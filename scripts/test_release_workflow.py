"""Check release routing and safety without running release operations."""

from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = {"", "setup", "prepare", "check", "manage-pr", "inspect", "publish"}


def load_workflow(path):
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


def action_steps(workflow):
    return {
        step["uses"].split("@")[0].removeprefix("changenote/action").lstrip("/"): step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith("changenote/action@")
        or step.get("uses", "").startswith("changenote/action/")
    }


def action_pin():
    workflow = load_workflow(ROOT / ".github/workflows/release.yml")
    return action_steps(workflow)[""]["uses"].split("@")[1]


class ReleaseWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load_workflow(ROOT / ".github/workflows/release.yml")
        cls.job = cls.workflow["jobs"]["release"]
        cls.actions = action_steps(cls.workflow)

    def test_all_workflow_actions_are_pinned(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for job in load_workflow(path)["jobs"].values():
                for step in job.get("steps", []):
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"^[^@\s]+@[0-9a-f]{40}$")
                        if step["uses"].startswith("changenote/action"):
                            match = re.fullmatch(r"changenote/action(?:/([a-z-]+))?@([0-9a-f]{40})", step["uses"])
                            self.assertIsNotNone(match)
                            self.assertIn(match[1] or "", PUBLIC)
                            self.assertEqual(match[2], action_pin())
                            self.assertNotIn("version", step.get("with", {}))
        self.assertEqual(set(self.actions), {""})
        for name, step in self.actions.items():
            self.assertIn(name, PUBLIC)
            self.assertTrue(step["uses"].endswith("@" + action_pin()))

    def test_two_steps_use_root_auto_with_the_default_cli(self):
        self.assertEqual(set(self.workflow["jobs"]), {"release"})
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(self.job["runs-on"], "ubuntu-latest")
        self.assertEqual(len(self.job["steps"]), 2)
        checkout = self.job["steps"][0]
        self.assertRegex(checkout["uses"], r"^actions/checkout@[0-9a-f]{40}$")
        self.assertEqual(checkout["with"], {"persist-credentials": "false"})
        self.assertNotIn("if", self.actions[""])
        self.assertEqual(self.actions[""]["with"], {"operation": "auto"})
        self.assertNotIn("cargo install", str(self.job))
        self.assertNotIn("rust-toolchain", str(self.job))
        self.assertTrue(all("run" not in step for step in self.job["steps"]))

    def test_manual_dispatch_uses_root_policy_without_input_choices(self):
        self.assertFalse(self.workflow["on"]["workflow_dispatch"])
        self.assertNotIn("inputs.", str(self.actions[""]))
        self.assertNotIn("publish-script", self.actions[""]["with"])
        self.assertNotIn("release-script", self.actions[""]["with"])

    def test_checkout_failure_does_not_bypass_default_step_gates(self):
        for step in self.job["steps"]:
            self.assertNotEqual(step.get("continue-on-error"), "true")
            self.assertNotIn("always(", step.get("if", ""))
        self.assertEqual(set(self.actions), {""})

    def test_events_permissions_and_concurrency_are_preserved(self):
        self.assertEqual(set(self.workflow["on"]), {"push", "workflow_dispatch"})
        self.assertEqual(self.workflow["on"]["push"]["branches"], ["main"])
        self.assertEqual(self.workflow["permissions"], {"contents": "write", "pull-requests": "write"})
        self.assertNotIn("permissions", self.job)
        self.assertEqual(self.workflow["concurrency"], {
            "group": "changenote-release-main", "cancel-in-progress": "false",
        })

    def test_fixture_ci_keeps_its_independent_source_pin(self):
        pin = "c644511a48a4c09a72b1d7a7b58dc6d6d8f374f5"
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertEqual(re.findall(r"--rev ([0-9a-f]{40})", ci), [pin])
        self.assertIn("--rev " + pin, (ROOT / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
