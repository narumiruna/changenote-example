# Composable release Actions

These templates are inactive because they are outside `.github/workflows/`.
They use merged Action commit `339f86c81883cb39f3003a38534ca87c97d1d7c2` from [Action PR #9](https://github.com/changenote/action/pull/9).
The active Release workflow and read-only [inspection template](../inspect/README.md) use the same full SHA.

- [Root workflow](root.yml) matches the active two-step workflow: checkout, then root `auto`.
  - Push manages the PR and publishes incomplete validated batches.
  - Manual dispatch only manages the PR. There is no manual operation menu.
  - Root owns CLI installation and project preparation; no standalone setup steps are needed.
- [Composed workflow](composed.yml) separates PR management, read-only inspection, and guarded publication into independent jobs.
  - Each job installs the CLI once with `/setup` and reuses its trusted `cli-path`.
  - `/prepare` prepares project tools and offline caches without PR or publication writes.
  - `/inspect` returns the verified batch, including completed batches.
  - Automatic publication uses `publication-needed`; its manual menu supports explicit retries, including completed batches.
  - `/publish` receives the exact inspected commit and stops if the latest batch changes before writes.
  - PR management failure does not block the independent inspection and publication jobs.
- [Command-hook workflow](command-hooks.yml) runs project-owned publication and release scripts after a verified managed merge.
  - The caller supplies runtimes, dependencies, caches, and registry credentials; `prepare: 'false'` leaves project preparation to the caller.
  - The scripts must test and build the verified source before upload and handle retries safely.
  - Manual dispatch only manages the PR and does not run the scripts.
- [External CI workflow](external-ci.yml) adds exact-commit external CI and Docker artifact publication to the composed flow.
  - Reusable CI must succeed for the inspected commit before `/publish` can write tags or GitHub Releases.
  - The Docker job receives the verified publication commit and tag. Its first `releases` entry is valid only for a single-package configuration.
  - Node.js and npm versions remain explicit and shared across preparation jobs.

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

The root and composed templates do not run project CI.
Add exact-commit validation, required approvals, and artifact jobs before publication when policy requires them.
The external CI template requires caller-owned reusable `.github/workflows/ci.yml` and `.github/workflows/docker.yml` files with `workflow_call`.
CI accepts the string input `revision`; Docker accepts the string inputs `revision` and `version-tag`.
These reusable workflows and the command-hook scripts are project-specific prerequisites, not included runnable examples.
Local template checks validate workflow structure, not hosted CI results or publication readiness.
PRs created with `GITHUB_TOKEN` do not start PR workflows automatically.
A maintainer must configure branch rules, required checks, and any authorized App token.

## Validation and deployment

Run `uv run --no-project --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v`.
Tests check API paths, pins, CLI reuse, commit and state gates, permissions, routing, and workflow syntax without contacting GitHub.
Neither this template migration nor local tests authorize workflow dispatch, tag pushes, GitHub Releases, registry uploads, or changes to historical release data.

Keep these files inactive until a maintainer selects and reviews a workflow.
Validate hosted tools, tokens, branch rules, and publication in an authorized disposable repository.
See [Release safety](../../README.md#release-safety) for restrictions and rollback.
