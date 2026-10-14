"""Verify isolated examples without versioning, tagging, or publication."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
        and ".venv" not in path.relative_to(root).parts
    }


def command(args, cwd, code=0):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != code:
        raise AssertionError(f"{args}: expected {code}, got {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result


def cli(binary, cwd, *args, code=0):
    if args[0] not in {"status", "check", "add"}:
        raise AssertionError("Verifier permits only status, check, and add")
    before = snapshot(cwd)
    index = cwd / ".git/index"
    index_before = index.read_bytes() if index.exists() else None
    result = command([str(binary), *args], cwd, code)
    if args[0] != "add" or code != 0:
        assert snapshot(cwd) == before, "Read-only command or failed add changed files"
        assert (index.read_bytes() if index.exists() else None) == index_before, "Read-only command or failed add changed Git index"
    return result


def git(cwd, *args):
    return command(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args], cwd)


def commit(cwd):
    git(cwd, "add", "--", ".")
    git(cwd, "-c", "user.name=Example Test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture")


def verify_fixture(binary, folder):
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp) / "fixture"
        shutil.copytree(folder / "fixture", work)
        expected = json.loads((folder / "expected-status.json").read_text())
        actual = json.loads(cli(binary, work, "status").stdout)
        assert actual == expected, str(folder)
        detailed = json.loads(cli(binary, work, "status", "--include-note-bumps").stdout)
        for release in detailed:
            assert len(release["notes"]) == len(release["note_bumps"])
            expected_log = folder / f"expected-{release['package']}-CHANGELOG.md"
            if expected_log.exists():
                entry = f"## {release['version']}\n\n"
                for bump in ("major", "minor", "patch"):
                    notes = [note for note, kind in zip(release["notes"], release["note_bumps"]) if kind == bump]
                    if notes:
                        entry += f"### {bump.capitalize()} Changes\n\n"
                        entry += "\n\n".join("- " + note.replace("\n", "\n  ") for note in notes) + "\n\n"
                # Static excerpts are also covered by Rust changelog golden tests.
                assert expected_log.read_text() == entry
        if folder.name == "manifests":
            original = (work / "packages/pkg-node/package.json").read_bytes()
            expected_json = (folder / "expected-package.json").read_bytes()
            assert expected_json == original.replace(b'"1.2.3"', b'"1.2.4"', 1)


def verify_creation(binary):
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp) / "fixture"
        shutil.copytree(ROOT / "examples/notes/mixed/fixture", work)
        (work / ".changenote/shared.md").unlink()
        cli(binary, work, "add", "shared", "--minor", "pkg-python", "--patch", "pkg-node", "-m", "Update shared API")
        expected = json.loads((ROOT / "examples/notes/mixed/expected-status.json").read_text())
        assert json.loads(cli(binary, work, "status").stdout) == expected
        cli(binary, work, "add", "shared", "--patch", "pkg-node", "-m", "Overwrite", code=1)
        cli(binary, work, "add", "bad", "--minor", "pkg-node", "--patch", "pkg-node", "-m", "Conflict", code=1)
        assert not (work / ".changenote/bad.md").exists()


def verify_check(binary):
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp) / "fixture"
        shutil.copytree(ROOT / "examples/notes/patch/fixture", work)
        git(work, "init", "-qb", "main")
        commit(work)
        git(work, "branch", "base")
        assert json.loads(cli(binary, work, "check", "--since", "base").stdout)["passed"]
        (work / "packages/pkg-python/README.md").write_text("Documentation change\n")
        commit(work)
        report = json.loads(cli(binary, work, "check", "--since", "base", code=1).stdout)
        assert report["changed_packages"] == ["pkg-python"] and not report["note_paths"]
        report = json.loads(cli(binary, work, "check", "--since", "base", "--skip-release", "--reason", "Documentation only").stdout)
        assert report["passed"] and report["skip_reason"] == "Documentation only"
        cli(binary, work, "check", "--since", "base", "--reason", "Docs", code=2)
        cli(binary, work, "add", "new", "--patch", "pkg-python", "-m", "Update docs")
        commit(work)
        report = json.loads(cli(binary, work, "check", "--since", "base").stdout)
        assert report["passed"] and report["note_paths"] == [".changenote/new.md"]
        cli(binary, work, "check", "--since", "base", "--skip-release", "--reason", " ", code=1)
        (work / "untracked.txt").write_text("untracked")
        cli(binary, work, "check", "--since", "base", code=1)
        (work / "untracked.txt").unlink()
        (work / ".changenote/new.md").unlink()
        commit(work)
        cli(binary, work, "check", "--since", "base", code=1)
        (work / ".changenote/invalid.md").write_text("invalid note")
        commit(work)
        cli(binary, work, "check", "--since", "base", "--skip-release", "--reason", "Docs", code=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, help="Path or executable name of the compatible changenote CLI")
    args = parser.parse_args()
    executable = shutil.which(args.cli)
    if executable is None:
        parser.error("CLI executable was not found")
    binary = Path(executable).resolve()
    before = snapshot(ROOT)
    for name in ("patch", "highest", "mixed", "multiline"):
        verify_fixture(binary, ROOT / "examples/notes" / name)
    verify_fixture(binary, ROOT / "examples/manifests")
    verify_creation(binary)
    verify_check(binary)
    assert snapshot(ROOT) == before, "Verifier changed the example repository"
    print("Verified 5 fixtures, mixed-bump creation, PR checks, and failure paths; no release actions ran.")


if __name__ == "__main__":
    main()
