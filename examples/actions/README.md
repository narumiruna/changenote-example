# Composable release Actions

These workflow templates are inactive because they are outside `.github/workflows/`.
They use published Action commit `b0fcdb183debdd058cd2298dec830c2caa5354e6` from [Action PR #7](https://github.com/changenote/action/pull/7).
Review and merge that Action PR before deploying this workflow migration.
The same full SHA is used by the proposed active workflow and the read-only preview template.

- [Root workflow](root.yml) explicitly chooses `auto` for complete PR management and built-in GitHub publication.
- [Composed workflow](composed.yml) separates PR management, read-only selection, and guarded publication into independent jobs.
  - Each job installs the CLI once with `/setup` and reuses its trusted `cli-path`.
  - `/prepare` prepares tools and offline caches without PR or publication writes.
  - `/select` returns the verified batch even after GitHub publication is complete.
  - Automatic publication uses `publication-needed`; explicit manual retries can include completed batches.
  - `/publish` receives the exact selected commit and stops if the latest batch changes before writes.

Root defaults to `operation: hooks`, not `auto`, to preserve existing script workflows.
In `hooks`, optional `publish-script` runs before `release-script`, and no scripts means no publication.
Nonempty scripts are rejected for other operations.
The root's built-in operations prepare project tools by default; `prepare: 'false'` uses caller-owned preparation.
The `/release` and `/preview` paths remain compatibility entry points.

The composed example uses the currently published PyPI CLI `v0.9.2` for this repository's plain-text version sources.
Select the same compatible exact version in every job.
A trusted executable path is valid only within its job; never take it from contributor input or pass it between jobs.
Built-in publication creates Git tags and GitHub Releases, not package registry uploads.

These workflows do not run or prove project CI.
Add validation of the selected commit, required approvals, or artifact jobs before publication when repository policy requires them.
Use the [external CI example](https://github.com/changenote/action/blob/main/examples/github-actions/logice-release.yml) for that boundary.
PRs created with `GITHUB_TOKEN` do not start PR workflows automatically.
A maintainer must configure branch rules, required checks, and any authorized App token before deployment.

## Validation and deployment

Run `uv run --no-project --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v`.
The template tests check interfaces, CLI reuse, exact commit guards, state gates, permissions, and workflow syntax without contacting GitHub.

The proposed active workflow selects root's built-in `auto` operation on pushes and defaults to PR management on manual runs.
Its publication policy is unchanged; new interfaces and installation come from the pinned Action revision.
A repository maintainer must review and merge Action PR #7 before merging this migration.
Do not dispatch a production workflow to test these examples.
Verify hosted tools, tokens, branch rules, and publication in an authorized disposable repository first.
Local tests do not authorize workflow dispatch, tag pushes, GitHub Releases, registry uploads, or changes to historical release data.
