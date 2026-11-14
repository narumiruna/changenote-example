"""Check inactive templates and API boundaries without contacting GitHub."""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_release_workflow import PUBLIC, ROOT, action_pin, action_steps, load_workflow

TEMPLATES = ROOT / "examples/actions"


def load(name):
    return load_workflow(TEMPLATES / name)


class ActionTemplates(unittest.TestCase):
    def test_root_template_has_explicit_push_and_manual_routes(self):
        workflow = load("root.yml")
        self.assertEqual(workflow["on"]["workflow_dispatch"]["inputs"]["operation"]["default"], "manage-pr")
        actions = action_steps(workflow)
        self.assertEqual(actions[""]["with"]["operation"], "auto")
        self.assertNotIn("version", actions[""]["with"])
        self.assertEqual(actions[""]["if"], "github.event_name == 'push'")
        self.assertIn("inputs.operation == 'manage-pr'", actions["manage-pr"]["if"])
        self.assertIn("inputs.operation == 'retry-publication'", actions["publish"]["if"])
        self.assertIn("steps.inspect.outputs.release-commit != ''", actions["publish"]["if"])
        self.assertEqual(actions["publish"]["with"]["expected-release-commit"],
                         "${{ steps.inspect.outputs.release-commit }}")

    def test_composed_jobs_reuse_one_cli_installation_each(self):
        workflow = load("composed.yml")
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["jobs"]), {"manage-pr", "inspect", "publish"})
        for name, job in workflow["jobs"].items():
            with self.subTest(job=name):
                setups = [step for step in job["steps"]
                          if step.get("uses", "").startswith("changenote/action/setup@")]
                self.assertEqual(len(setups), 1)
                self.assertEqual(setups[0].get("with", {}), {})
                for step in job["steps"]:
                    self.assertNotIn("run", step)
                    if re.match(r"changenote/action/(prepare|manage-pr|inspect|publish)@", step["uses"]):
                        self.assertEqual(step["with"]["cli-path"], "${{ steps.cli.outputs.cli-path }}")
        self.assertNotIn("CHANGENOTE_CLI_VERSION", workflow.get("env", {}))

    def test_publication_uses_inspected_identity_and_separate_state(self):
        jobs = load("composed.yml")["jobs"]
        self.assertEqual(jobs["publish"]["needs"], "inspect")
        self.assertNotIn("needs.manage-pr", str(jobs["publish"]))
        self.assertEqual(jobs["publish"]["permissions"], {"contents": "write"})
        self.assertIn("needs.inspect.outputs.release-commit != ''", jobs["publish"]["if"])
        self.assertIn("needs.inspect.outputs.publication-needed == 'true'", jobs["publish"]["if"])
        self.assertIn("inputs.operation == 'retry-publication'", jobs["publish"]["if"])
        expected = "${{ needs.inspect.outputs.release-commit }}"
        self.assertEqual(jobs["publish"]["steps"][0]["with"]["ref"], expected)
        for step in jobs["publish"]["steps"]:
            if re.match(r"changenote/action/(prepare|publish)@", step["uses"]):
                self.assertEqual(step["with"]["expected-release-commit"], expected)
        self.assertEqual(jobs["manage-pr"]["permissions"], {
            "contents": "write", "pull-requests": "write",
        })
        self.assertNotIn("permissions", jobs["inspect"])
        for job in jobs.values():
            if "concurrency" in job:
                self.assertEqual(job["concurrency"]["cancel-in-progress"], "false")
            self.assertNotEqual(job.get("continue-on-error"), "true")
            self.assertNotIn("always(", job.get("if", ""))
        for name, scope in (("manage-pr", "manage-pr"), ("inspect", "inspect"), ("publish", "publish")):
            prepare = next(step for step in jobs[name]["steps"]
                           if step["uses"].startswith("changenote/action/prepare@"))
            self.assertEqual(prepare["with"]["operation"], scope)

    def test_inspection_is_readonly_without_a_consumer_checkout(self):
        workflow = load_workflow(ROOT / "examples/inspect/workflow.yml")
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
        steps = workflow["jobs"]["inspect"]["steps"]
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["uses"], "changenote/action/setup@" + action_pin())
        self.assertEqual(steps[0].get("with", {}), {})
        self.assertEqual(steps[1]["uses"], "changenote/action/inspect@" + action_pin())
        self.assertEqual(steps[1]["with"]["cli-path"], "${{ steps.cli.outputs.cli-path }}")
        self.assertNotIn("checkout", str(steps))

    def test_templates_are_inactive_and_use_only_the_new_api_at_one_pin(self):
        paths = [TEMPLATES / "root.yml", TEMPLATES / "composed.yml",
                 ROOT / "examples/inspect/workflow.yml"]
        for path in paths:
            workflow = load_workflow(path)
            for name, step in action_steps(workflow).items():
                self.assertIn(name, PUBLIC)
                self.assertTrue(step["uses"].endswith("@" + action_pin()))
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    self.assertRegex(step["uses"], r"^[^@\s]+@[0-9a-f]{40}$")
                    if step["uses"].startswith("changenote/action"):
                        match = re.fullmatch(r"changenote/action(?:/([a-z-]+))?@([0-9a-f]{40})", step["uses"])
                        self.assertIsNotNone(match)
                        self.assertIn(match[1] or "", PUBLIC)
                        self.assertEqual(match[2], action_pin())
                        self.assertNotIn("version", step.get("with", {}))
        active = {p.name for p in (ROOT / ".github/workflows").glob("*.yml")}
        self.assertEqual(active, {"ci.yml", "release.yml"})
        self.assertFalse((ROOT / "examples/preview").exists())

    @unittest.skipUnless(shutil.which("actionlint"), "actionlint is not installed")
    def test_workflow_templates_lint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet", directory], check=True, capture_output=True)
            templates = [TEMPLATES / "root.yml", TEMPLATES / "composed.yml",
                         ROOT / "examples/inspect/workflow.yml"]
            for source in templates:
                path = workflows / source.name
                shutil.copyfile(source, path)
                result = subprocess.run(["actionlint", str(path)], cwd=root,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
