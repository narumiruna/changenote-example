# PR Note Checks

`changenote check --since <ref>` compares committed paths from the merge base to `HEAD`. Run at the Git repository root with a clean tree and enough history. No file patterns are excluded automatically.

## Local examples

Use a disposable Git repository. Run from this repository root. The commit commands use your existing Git identity; they do not change it.

```sh
work=$(mktemp -d)
cp -R examples/notes/patch/fixture/. "$work/"
cd "$work"
git init -b main
git add -- .changenote packages
git commit -m "test: initial fixture"
git branch base
changenote check --since base
```

Expected exit: `0`. No package changed. The initial patch note is an old pending note, not a PR note.

```sh
printf 'Documentation change\n' > packages/pkg-python/README.md
git add -- packages/pkg-python/README.md
git commit -m "docs: describe package"
changenote check --since base
```

Expected exit: `1`. The JSON report has `changed_packages: ["pkg-python"]`, `note_paths: []`, and `passed: false`. An unchanged old note does not satisfy the rule.

```sh
changenote check --since base --skip-release --reason "Documentation only"
```

Expected exit: `0`. The report records the reason. This exemption does not bypass invalid configuration, invalid notes, invalid versions, or Git checks. Use it only when repository review policy permits a release exemption.

```sh
changenote add new --patch pkg-python -m "Update package documentation"
git add -- .changenote/new.md
git commit -m "test: add PR note"
changenote check --since base
```

Expected exit: `0`. `note_paths` contains `.changenote/new.md`. No files are written by `check`.

## Limits and failure cases

- Added, modified, or renamed valid notes count only if they remain in `HEAD`. Deleted notes do not count.
- At least one PR note is sufficient: this is a PR-level check, not proof that every changed package has a note.
- Nested package directories use the deepest matching directory. Paths outside all packages are reported, not treated as package changes.
- Untracked or uncommitted changes cause failure rather than changing the comparison.
- Missing refs and unavailable merge bases fail. Fetch full history and the base ref in CI.
- Validation or missing-note failures exit `1`; invalid CLI argument combinations exit `2`. `--reason` without `--skip-release` exits `2`; a blank exemption reason exits `1`.
- Status JSON is unchanged by this feature. Check JSON includes `merge_base`, `changed_packages`, `note_paths`, `outside_paths`, `skip_reason`, and `passed`. Validation errors report to stderr without a JSON report.

The [verifier](../../scripts/verify_examples.py) runs these success cases and tests deleted notes, invalid notes, invalid exemptions, dirty trees, conflicting bumps, and overwrite attempts in temporary directories.

For a consumer PR workflow, use the [core CI example](https://github.com/narumiruna/changenote#check-pr-notes): full checkout history, a compatible pinned CLI, and an available remote base ref. Define how documentation-only PRs and generated Release PRs are exempted before making that job required. The example-verification workflow does not impose a note policy on this repository.
