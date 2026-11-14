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
        self.assertEqual(set(self.actions), {"", "setup", "prepare", "manage-pr", "inspect", "publish"})
        for name, step in self.actions.items():
            self.assertIn(name, PUBLIC)
            self.assertTrue(step["uses"].endswith("@" + action_pin()))

    def test_push_uses_root_auto_with_the_default_cli(self):
        self.assertEqual(set(self.workflow["jobs"]), {"release"})
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(self.job["runs-on"], "ubuntu-latest")
        self.assertEqual(len(self.job["steps"]), 7)
        checkout = self.job["steps"][0]
        self.assertRegex(checkout["uses"], r"^actions/checkout@[0-9a-f]{40}$")
        self.assertEqual(checkout["with"], {
            "ref": "main", "fetch-depth": "0", "persist-credentials": "false",
        })
        self.assertEqual(self.actions[""]["if"], "github.event_name == 'push'")
        self.assertEqual(self.actions[""]["with"], {
            "base-branch": "main", "operation": "auto",
        })
        self.assertNotIn("cargo install", str(self.job))
        self.assertNotIn("rust-toolchain", str(self.job))
        self.assertTrue(all("run" not in step for step in self.job["steps"]))

    def test_manual_pr_and_retry_paths_reuse_one_cli_installation(self):
        self.assertEqual(self.actions["setup"].get("with", {}), {})
        for name in ("setup", "prepare", "manage-pr", "inspect", "publish"):
            self.assertIn("github.event_name == 'workflow_dispatch'", self.actions[name]["if"])
        self.assertEqual(self.actions["prepare"]["with"]["operation"],
                         "${{ inputs.operation == 'manage-pr' && 'manage-pr' || 'inspect' }}")
        self.assertEqual(self.actions["manage-pr"]["if"],
                         "github.event_name == 'workflow_dispatch' && inputs.operation == 'manage-pr'")
        self.assertEqual(self.actions["inspect"]["if"],
                         "github.event_name == 'workflow_dispatch' && inputs.operation == 'retry-publication'")
        for name in ("prepare", "manage-pr", "inspect", "publish"):
            self.assertEqual(self.actions[name]["with"]["cli-path"], "${{ steps.cli.outputs.cli-path }}")
            self.assertEqual(self.actions[name]["with"]["base-branch"], "main")
        self.assertEqual(self.actions["setup"]["id"], "cli")
        self.assertEqual(self.actions["inspect"]["id"], "inspect")

    def test_retry_requires_a_successful_nonempty_inspected_commit(self):
        publish = self.actions["publish"]
        self.assertEqual(publish["if"],
                         "github.event_name == 'workflow_dispatch' && inputs.operation == 'retry-publication' && steps.inspect.outputs.release-commit != ''")
        self.assertEqual(publish["with"]["expected-release-commit"],
                         "${{ steps.inspect.outputs.release-commit }}")
        steps = self.job["steps"]
        self.assertLess(steps.index(self.actions["prepare"]), steps.index(self.actions["inspect"]))
        self.assertLess(steps.index(self.actions["inspect"]), steps.index(publish))
        for step in steps:
            self.assertNotEqual(step.get("continue-on-error"), "true")
            self.assertNotIn("always(", step.get("if", ""))

    def test_events_permissions_and_concurrency_are_preserved(self):
        self.assertEqual(set(self.workflow["on"]), {"push", "workflow_dispatch"})
        self.assertEqual(self.workflow["on"]["push"]["branches"], ["main"])
        operation = self.workflow["on"]["workflow_dispatch"]["inputs"]["operation"]
        self.assertEqual(operation["type"], "choice")
        self.assertEqual(operation["default"], "manage-pr")
        self.assertEqual(operation["options"], ["manage-pr", "retry-publication"])
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertEqual(self.job["permissions"], {"contents": "write", "pull-requests": "write"})
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
