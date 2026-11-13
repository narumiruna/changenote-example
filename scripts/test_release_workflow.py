"""Test release workflow metadata and operation selection without publication."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEGACY_COMMIT = "6d0d38646eaf078b535909036bfecaad664e52a9"
LEGACY_BLOB = "3978e1a049dc7633ba3c36059bfdfcd85ac0f362"


class ReleaseWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load(
            (ROOT / ".github/workflows/release.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        cls.job = cls.workflow["jobs"]["release"]
        cls.selector = next(
            step for step in cls.job["steps"] if step.get("id") == "operation"
        )

    def select(self, operation, commit=LEGACY_COMMIT, blob=LEGACY_BLOB, git_error=False):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            stub = work / "git"
            stub.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\n"
                '[[ $GIT_ERROR == false ]] || exit 2\n'
                'case "$*" in\n'
                '  "log -1 --first-parent --format=%H -- .changenote/releases.json")\n'
                '    printf "%s\\n" "$BATCH_COMMIT" ;;\n'
                '  "rev-parse HEAD:.changenote/releases.json")\n'
                '    printf "%s\\n" "$BATCH_BLOB" ;;\n'
                '  *) exit 99 ;;\n'
                "esac\n"
            )
            stub.chmod(0o755)
            output = work / "output"
            output.write_text("")
            env = dict(
                os.environ,
                PATH=str(work) + os.pathsep + os.environ["PATH"],
                REQUESTED_OPERATION=operation,
                BATCH_COMMIT=commit,
                BATCH_BLOB=blob,
                GIT_ERROR=str(git_error).lower(),
                GITHUB_OUTPUT=str(output),
            )
            result = subprocess.run(
                ["bash", "-c", self.selector["run"]],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result, output.read_text()

    def test_single_action_prepares_its_own_cli(self):
        self.assertEqual(set(self.workflow["jobs"]), {"release"})
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(self.job["runs-on"], "ubuntu-latest")
        self.assertEqual(
            self.job["permissions"],
            {"contents": "write", "pull-requests": "write"},
        )
        checkout, selector, action = self.job["steps"]
        self.assertEqual(checkout["uses"], "actions/checkout@v7")
        self.assertEqual(
            checkout["with"],
            {"ref": "main", "fetch-depth": "0", "persist-credentials": "false"},
        )
        self.assertIs(selector, self.selector)
        self.assertRegex(
            action["uses"], r"^narumiruna/changenote/release@[0-9a-f]{40}$"
        )
        self.assertEqual(action["with"]["base-branch"], "main")
        self.assertEqual(
            action["with"]["operation"], "${{ steps.operation.outputs.operation }}"
        )
        self.assertNotIn("cargo install", str(self.job))
        self.assertNotIn("rust-toolchain", str(self.job))

    def test_events_and_manual_operation_choices(self):
        self.assertEqual(self.workflow["on"]["push"]["branches"], ["main"])
        operation = self.workflow["on"]["workflow_dispatch"]["inputs"]["operation"]
        self.assertEqual(operation["type"], "choice")
        self.assertEqual(operation["default"], "manage-pr")
        self.assertEqual(operation["options"], ["manage-pr", "retry-publication"])
        self.assertEqual(
            self.selector["env"]["REQUESTED_OPERATION"],
            "${{ inputs.operation || 'auto' }}",
        )
        self.assertEqual(self.workflow["concurrency"]["cancel-in-progress"], "false")
        self.assertIsNone(re.search(r"\$\{\{", self.selector["run"]))

    def test_known_published_batch_only_manages_pr(self):
        for operation in ("auto", "manage-pr"):
            with self.subTest(operation=operation):
                result, output = self.select(operation)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, "operation=manage-pr\n")
                self.assertIn("::notice::", result.stdout)

    def test_legacy_publication_retry_fails(self):
        result, output = self.select("retry-publication")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output, "")
        self.assertIn("::error::", result.stdout)
        self.assertIn("original tooling", result.stdout)

    def test_new_batches_preserve_requested_operations(self):
        for operation in ("auto", "manage-pr", "retry-publication"):
            with self.subTest(operation=operation):
                result, output = self.select(operation, "a" * 40, "b" * 40)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, f"operation={operation}\n")
                self.assertNotIn("::notice::", result.stdout)

    def test_same_blob_at_another_commit_has_no_exemption(self):
        result, output = self.select("retry-publication", commit="a" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "operation=retry-publication\n")

    def test_other_blob_at_legacy_commit_has_no_exemption(self):
        result, output = self.select("retry-publication", blob="b" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "operation=retry-publication\n")

    def test_git_errors_do_not_select_an_operation(self):
        result, output = self.select("auto", git_error=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()
