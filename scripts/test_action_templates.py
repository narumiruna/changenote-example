"""Check inactive templates and API boundaries without contacting GitHub."""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

from test_release_workflow import PUBLIC, ROOT, action_pin, action_steps, load_workflow

TEMPLATES = ROOT / "examples/actions"


def load(name):
    return load_workflow(TEMPLATES / name)


class ActionTemplates(unittest.TestCase):
    def test_root_template_matches_the_minimal_active_workflow(self):
        workflow = load("root.yml")
        self.assertEqual(workflow, load_workflow(ROOT / ".github/workflows/release.yml"))
        self.assertEqual(len(workflow["jobs"]["release"]["steps"]), 2)
        self.assertEqual(action_steps(workflow)[""]["with"], {"operation": "auto"})
        self.assertFalse(workflow["on"]["workflow_dispatch"])

    def test_composed_and_external_ci_jobs_reuse_one_cli_installation_each(self):
        for name in ("composed.yml", "external-ci.yml"):
            workflow = load(name)
            self.assertEqual(workflow["permissions"], {"contents": "read"})
            self.assertNotIn("CHANGENOTE_CLI_VERSION", workflow.get("env", {}))
            for job_name, job in workflow["jobs"].items():
                if "steps" not in job:
                    continue
                with self.subTest(template=name, job=job_name):
                    setups = [step for step in job["steps"]
                              if step.get("uses", "").startswith("changenote/action/setup@")]
                    self.assertEqual(len(setups), 1)
                    self.assertEqual(setups[0].get("with", {}), {})
                    for step in job["steps"]:
                        self.assertNotIn("run", step)
                        if re.match(r"changenote/action/(prepare|manage-pr|inspect|publish)@", step["uses"]):
                            self.assertEqual(step["with"]["cli-path"], "${{ steps.cli.outputs.cli-path }}")

    def test_publication_uses_inspected_identity_and_separate_state(self):
        jobs = load("composed.yml")["jobs"]
        self.assertEqual(set(jobs), {"manage-pr", "inspect", "publish"})
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
            for step in job["steps"]:
                self.assertNotEqual(step.get("continue-on-error"), "true")
                self.assertNotIn("always(", step.get("if", ""))
        self.assertEqual(load("composed.yml")["on"]["workflow_dispatch"]["inputs"]["operation"]["default"], "manage-pr")
        self.assertIn("inputs.operation == 'manage-pr'", jobs["manage-pr"]["if"])
        for name, scope in (("manage-pr", "manage-pr"), ("inspect", "inspect"), ("publish", "publish")):
            prepare = next(step for step in jobs[name]["steps"]
                           if step["uses"].startswith("changenote/action/prepare@"))
            self.assertEqual(prepare["with"]["operation"], scope)

    def test_external_ci_keeps_exact_commit_ci_and_artifacts_separate(self):
        workflow = load("external-ci.yml")
        jobs = workflow["jobs"]
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertNotIn("concurrency", workflow)
        self.assertNotIn("concurrency", jobs["inspect"])
        self.assertEqual(jobs["validate"]["needs"], "inspect")
        self.assertEqual(jobs["validate"]["uses"], "./.github/workflows/ci.yml")
        expected = "${{ needs.inspect.outputs.release-commit }}"
        self.assertEqual(jobs["validate"]["with"]["revision"], expected)
        self.assertEqual(jobs["publish"]["needs"], ["inspect", "validate"])
        self.assertIn("needs.validate.result == 'success'", jobs["publish"]["if"])
        self.assertEqual(jobs["publish"]["steps"][-1]["with"]["expected-release-commit"], expected)
        self.assertEqual(jobs["publish"]["steps"][0]["with"]["ref"], expected)
        self.assertEqual(jobs["publish"]["permissions"], {"contents": "write"})
        self.assertEqual(jobs["release"]["permissions"], {"contents": "write", "pull-requests": "write"})
        pr_inputs = jobs["release"]["steps"][-1]["with"]
        self.assertNotIn("commit-message", pr_inputs)
        self.assertNotIn("pr-title", pr_inputs)
        self.assertEqual(jobs["release"]["concurrency"]["cancel-in-progress"], "false")
        self.assertEqual(jobs["publish"]["concurrency"]["cancel-in-progress"], "false")
        self.assertNotEqual(jobs["release"]["concurrency"]["group"], jobs["publish"]["concurrency"]["group"])
        self.assertEqual(jobs["docker"]["uses"], "./.github/workflows/docker.yml")
        self.assertEqual(jobs["docker"]["with"]["revision"], "${{ needs.publish.outputs.release-commit }}")
        self.assertEqual(jobs["docker"]["with"]["version-tag"], "${{ fromJSON(needs.publish.outputs.releases)[0].tag }}")
        self.assertIn("needs.inspect.outputs.publication-needed == 'true'", jobs["validate"]["if"])
        self.assertIn("inputs.operation == 'retry-publication'", jobs["validate"]["if"])
        self.assertEqual(jobs["inspect"]["steps"][-1]["uses"], "changenote/action/inspect@" + action_pin())
        self.assertEqual(jobs["release"]["steps"][-1]["uses"], "changenote/action/manage-pr@" + action_pin())
        self.assertEqual(jobs["publish"]["steps"][-1]["uses"], "changenote/action/publish@" + action_pin())
        self.assertIn("inputs.operation == 'retry-publication'", jobs["docker"]["if"])
        self.assertNotIn("needs.release", jobs["publish"]["if"])

    def test_command_hooks_use_public_root_and_safe_defaults(self):
        example = load("command-hooks.yml")
        self.assertEqual(set(example["on"]), {"push", "workflow_dispatch"})
        job = example["jobs"]["release"]
        self.assertEqual(job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(example["concurrency"]["cancel-in-progress"], "false")
        steps = job["steps"]
        self.assertEqual(steps[0]["with"]["persist-credentials"], "false")
        self.assertEqual(steps[-1]["uses"], "changenote/action@" + action_pin())
        self.assertEqual(steps[-1]["with"]["publish-script"], "bash scripts/publish.sh")
        self.assertEqual(steps[-1]["with"]["release-script"], "bash scripts/release.sh")
        self.assertNotIn("scripts/action/", str(steps))

    def test_all_consumer_setup_is_inside_the_public_action(self):
        for source in TEMPLATES.glob("*.yml"):
            workflow = load(source.name)
            for job in workflow["jobs"].values():
                for step in job.get("steps", []):
                    self.assertNotIn("run", step)
                    self.assertIn("uses", step)
                    if "with" in step and "persist-credentials" in step["with"]:
                        self.assertEqual(step["with"]["persist-credentials"], "false")
            text = source.read_text()
            self.assertNotIn("scripts/action/", text)
            self.assertNotIn("setup-changenote", text)
            self.assertNotIn("VERSION", text.replace("CHANGENOTE_NODE_VERSION", "").replace("CHANGENOTE_NPM_VERSION", ""))

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
        paths = [*TEMPLATES.glob("*.yml"), ROOT / "examples/inspect/workflow.yml"]
        for path in paths:
            workflow = load_workflow(path)
            for name, step in action_steps(workflow).items():
                self.assertIn(name, PUBLIC)
                self.assertTrue(step["uses"].endswith("@" + action_pin()))
            for job in workflow["jobs"].values():
                for step in job.get("steps", []):
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
            for called, inputs in (("ci.yml", ["revision"]), ("docker.yml", ["revision", "version-tag"])):
                stub = {
                    "on": {"workflow_call": {"inputs": {
                        key: {"type": "string", "required": True} for key in inputs
                    }}},
                    "jobs": {"check": {"runs-on": "ubuntu-latest", "steps": [{"run": "true"}]}},
                }
                (workflows / called).write_text(yaml.safe_dump(stub))
            templates = [*TEMPLATES.glob("*.yml"), ROOT / "examples/inspect/workflow.yml"]
            for source in templates:
                path = workflows / source.name
                shutil.copyfile(source, path)
                result = subprocess.run(["actionlint", str(path)], cwd=root,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
