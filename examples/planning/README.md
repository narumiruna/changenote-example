# Release planning examples

Use the CLI revision pinned in the root README. Run commands from the example repository root and copy fixtures before use.

## Note provenance

```sh
work=$(mktemp -d)
cp -R examples/planning/provenance/fixture/. "$work/"
changenote --root "$work" status --include-note-paths --include-note-bumps
```

Output must match [expected-details.json](provenance/expected-details.json). The two Node.js notes have identical summaries but retain their separate paths. Direct paths align with summaries and bumps in filename order. Either status option can be used independently; default status and saved batch fields are unchanged. No files are written.

## Automatic names

Copy the same fixture, then remove only its copied notes:

```sh
work=$(mktemp -d)
cp -R examples/planning/provenance/fixture/. "$work/"
rm -- "$work/.changenote/a.md" "$work/.changenote/z.md"
changenote --root "$work" add --patch pkg-node -m "Fix output"
changenote --root "$work" status --include-note-paths
```

Add prints the actual created path. Its filename is `note-` plus 32 lowercase hexadecimal characters from OS randomness. Do not expect a particular ID or creation-time order. An explicit name still works. Creation never overwrites files or symlinks; only generated-name collisions retry, at most eight times. Invalid packages, conflicting bumps, and empty messages fail before allocation.

## Fixed version groups

```sh
group=$(mktemp -d)
cp -R examples/planning/fixed-unequal/fixture/. "$group/"
changenote --root "$group" status
changenote --root "$group" status --include-note-paths --include-note-bumps
```

Output must match the fixture's [default plan](fixed-unequal/expected-status.json) and [detailed plan](fixed-unequal/expected-details.json). Node.js starts at `1.0.0`; Python starts at `2.4.9`. Only Node.js has a patch note, but both release at `2.4.10`: the highest current group version plus the highest requested bump, applied once. Each result retains its actual old version. The change for a lower-version member can exceed the requested bump.

Python has no direct summaries or paths. Its `fixed_group.source_note_paths` explains the cause without copying Node.js notes into Python. Its illustrative [changelog](fixed-unequal/expected-pkg-python-CHANGELOG.md) states that it was released with the group. The [equal-version fixture](fixed-equal/) starts both packages at `1.0.0` and plans `1.0.1`.

Groups need at least two distinct known package names, cannot overlap, and do not accept globs. No group notes means no synchronization, even when versions differ. Absent `fixed` or `fixed: []` preserves independent behavior. Dependency ranges and lockfiles are not updated.

The verifier runs only status, check, and add on copied fixtures. It does not apply versions or create tags. Actual version writes and exact changelog output are tested in temporary core Rust fixtures. Active package versions and configs in this repository are unchanged.
