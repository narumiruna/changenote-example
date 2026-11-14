"""Check release workflow metadata without running release operations."""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ReleaseWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load(
            (ROOT / ".github/workflows/release.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        cls.job = cls.workflow["jobs"]["release"]

    def test_all_workflow_actions_are_pinned(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
            for job in workflow["jobs"].values():
                for step in job.get("steps", []):
                    if "uses" in step:
                        with self.subTest(workflow=path.name, action=step["uses"]):
                            self.assertRegex(step["uses"], r"^[^@\s]+@[0-9a-f]{40}$")

    def test_single_action_owns_setup_and_release_routing(self):
        self.assertEqual(set(self.workflow["jobs"]), {"release"})
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(self.job["runs-on"], "ubuntu-latest")
        self.assertEqual(
            self.job["permissions"],
            {"contents": "write", "pull-requests": "write"},
        )
        checkout, action = self.job["steps"]
        self.assertRegex(checkout["uses"], r"^actions/checkout@[0-9a-f]{40}$")
        self.assertEqual(
            checkout["with"],
            {"ref": "main", "fetch-depth": "0", "persist-credentials": "false"},
        )
        self.assertRegex(
            action["uses"], r"^changenote/action@[0-9a-f]{40}$"
        )
        self.assertEqual(
            action["with"],
            {"base-branch": "main", "version": "v0.9.2",
             "operation": "${{ inputs.operation || 'auto' }}"},
        )
        self.assertNotIn("cargo install", str(self.job))
        self.assertNotIn("rust-toolchain", str(self.job))
        self.assertTrue(all("run" not in step for step in self.job["steps"]))

    def test_events_manual_choices_and_concurrency(self):
        self.assertEqual(self.workflow["on"]["push"]["branches"], ["main"])
        operation = self.workflow["on"]["workflow_dispatch"]["inputs"]["operation"]
        self.assertEqual(operation["type"], "choice")
        self.assertEqual(operation["default"], "manage-pr")
        self.assertEqual(operation["options"], ["manage-pr", "retry-publication"])
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertEqual(
            self.workflow["concurrency"],
            {"group": "changenote-release-main", "cancel-in-progress": "false"},
        )


if __name__ == "__main__":
    unittest.main()
