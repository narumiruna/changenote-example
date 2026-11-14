"""Validate inactive composition templates without deploying new Action paths."""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "examples/actions"


def load(name):
    return yaml.load((TEMPLATES / name).read_text(), Loader=yaml.BaseLoader)


def action_pin():
    workflow = yaml.load((ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader)
    action = workflow["jobs"]["release"]["steps"][-1]["uses"]
    return re.fullmatch(r"changenote/action@([0-9a-f]{40})", action).group(1)


class ActionTemplates(unittest.TestCase):
    def test_root_explicitly_opts_into_built_in_publication(self):
        workflow = load("root.yml")
        self.assertEqual(workflow["on"]["workflow_dispatch"]["inputs"]["operation"]["default"], "manage-pr")
        action = workflow["jobs"]["release"]["steps"][-1]
        self.assertEqual(action["uses"], "changenote/action@" + action_pin())
        self.assertEqual(action["with"]["version"], "v0.9.2")
        self.assertEqual(action["with"]["operation"], "${{ inputs.operation || 'auto' }}")

    def test_composed_jobs_reuse_one_cli_installation_each(self):
        workflow = load("composed.yml")
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        for name, job in workflow["jobs"].items():
            with self.subTest(job=name):
                setups = [step for step in job["steps"]
                          if step.get("uses", "").startswith("changenote/action/setup@")]
                self.assertEqual(len(setups), 1)
                self.assertEqual(setups[0]["with"]["version"], "${{ env.CHANGENOTE_CLI_VERSION }}")
                for step in job["steps"]:
                    self.assertNotIn("run", step)
                    if re.match(r"changenote/action/(prepare|manage-pr|select|publish)@", step["uses"]):
                        self.assertEqual(step["with"]["cli-path"], "${{ steps.cli.outputs.cli-path }}")

    def test_publication_uses_selected_identity_and_separate_state(self):
        jobs = load("composed.yml")["jobs"]
        self.assertEqual(jobs["publish"]["needs"], "select")
        self.assertNotIn("needs.manage-pr", str(jobs["publish"]))
        self.assertEqual(jobs["publish"]["permissions"], {"contents": "write"})
        self.assertIn("needs.select.outputs.publication-needed == 'true'", jobs["publish"]["if"])
        self.assertIn("inputs.operation == 'retry-publication'", jobs["publish"]["if"])
        expected = "${{ needs.select.outputs.release-commit }}"
        self.assertEqual(jobs["publish"]["steps"][0]["with"]["ref"], expected)
        self.assertEqual(jobs["publish"]["steps"][-1]["with"]["expected-release-commit"], expected)
        self.assertEqual(jobs["manage-pr"]["permissions"], {
            "contents": "write", "pull-requests": "write",
        })

    def test_templates_are_inactive_and_share_the_published_action_pin(self):
        for name in ("root.yml", "composed.yml"):
            self.assertFalse((ROOT / ".github/workflows" / name).exists())
            workflow = load(name)
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    if step["uses"].startswith("changenote/"):
                        self.assertTrue(step["uses"].endswith("@" + action_pin()))
        active = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertNotIn("<full-action-commit-sha>", active)
        self.assertNotIn("changenote/action/setup@", active)

    @unittest.skipUnless(shutil.which("actionlint"), "actionlint is not installed")
    def test_workflow_templates_lint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet", directory], check=True, capture_output=True)
            templates = [TEMPLATES / "root.yml", TEMPLATES / "composed.yml",
                         ROOT / "examples/preview/workflow.yml"]
            for source in templates:
                path = workflows / source.name
                shutil.copyfile(source, path)
                result = subprocess.run(["actionlint", str(path)], cwd=root,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
