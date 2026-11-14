# Composable release Actions

These templates are inactive because they are outside `.github/workflows/`.
They use merged Action commit `339f86c81883cb39f3003a38534ca87c97d1d7c2` from [Action PR #9](https://github.com/changenote/action/pull/9).
The active Release workflow and read-only [inspection template](../inspect/README.md) use the same full SHA.

- [Root workflow](root.yml) uses root `auto` on push for PR management and built-in GitHub publication.
  - Manual PR work calls standalone `manage-pr` after preparation.
  - A manual publication retry inspects the latest batch and calls `publish` with its exact commit.
  - Root never receives a manual menu choice as its operation.
- [Composed workflow](composed.yml) separates PR management, read-only inspection, and guarded publication into independent jobs.
  - Each job installs the CLI once with `/setup` and reuses its trusted `cli-path`.
  - `/prepare` prepares project tools and offline caches without PR or publication writes.
  - `/inspect` returns the verified batch, including completed batches.
  - Automatic publication uses `publication-needed`; manual retries can include completed batches.
  - `/publish` receives the exact inspected commit and stops if the latest batch changes before writes.
  - PR management failure does not block the independent inspection and publication jobs.

The seven public entry points are root, `setup`, `prepare`, `check`, `manage-pr`, `inspect`, and `publish`.
The former release, select, and preview paths have no compatibility aliases.
Root accepts only `hooks` and `auto`; its default remains `hooks`.
In `hooks`, optional `publish-script` runs before `release-script`, and no scripts means no publication.
Only `hooks` accepts scripts. Root `auto` prepares project tools by default; `prepare: 'false'` uses caller-owned preparation.

The `operation` input on `/prepare` is an environment scope, not a command:
`manage-pr` for pending notes, `inspect` or guarded `publish` for a saved batch, and `auto` for both.
Only the `publish` scope requires `expected-release-commit`.
Standalone operation jobs retain responsibility for their tool environment. Use the same tools as preparation; set `RUSTUP_TOOLCHAIN` explicitly if it must override a checked-in toolchain file.

These examples omit `version` and use the default `latest` stable PyPI CLI.
Each job resolves the CLI during setup, then reuses that installation. Different jobs and runs can resolve different CLI versions; the Action SHA does not pin the CLI.
A CLI path is valid only within its job; never take it from contributor input or pass it between jobs.
Built-in publication creates Git tags and GitHub Releases, not registry uploads.

These templates do not run or prove project CI.
Add exact-commit validation, required approvals, and artifact jobs before publication when policy requires them.
See the [external CI example](https://github.com/changenote/action/blob/339f86c81883cb39f3003a38534ca87c97d1d7c2/examples/github-actions/logice-release.yml).
PRs created with `GITHUB_TOKEN` do not start PR workflows automatically.
A maintainer must configure branch rules, required checks, and any authorized App token.

## Validation and deployment

Run `uv run --no-project --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v`.
Tests check API paths, pins, CLI reuse, commit and state gates, permissions, routing, and workflow syntax without contacting GitHub.
Neither this template migration nor local tests authorize workflow dispatch, tag pushes, GitHub Releases, registry uploads, or changes to historical release data.

Keep these files inactive until a maintainer selects and reviews a workflow.
Validate hosted tools, tokens, branch rules, and publication in an authorized disposable repository.
See [Release safety](../../README.md#release-safety) for restrictions and rollback.
