# Publication inspection

[workflow.yml](workflow.yml) is an inactive template outside `.github/workflows/`.
It uses `/setup` and `/inspect` at merged Action commit `339f86c81883cb39f3003a38534ca87c97d1d7c2`, the same full SHA as the active Release workflow.
Both use CLI `v0.9.2`; fixture CI retains its separate source pin.

The Actions need Linux, Bash, Git, gh, jq, standard coreutils, and only `contents: read`.
`/setup` installs a prebuilt PyPI wheel with uv; `/inspect` reuses its trusted same-job `cli-path`.
No consumer checkout is required. The selected remote base branch, not uncommitted files, determines the release.

Inspection discovers the latest first-parent batch and verifies the complete release tree from its parent's notes and configuration, including supported historical output.
It reconstructs files only in a temporary repository and removes it afterward.
Source files, index, refs, tags, and Git identity stay unchanged. It never creates tags, commits, PRs, or Releases.

## Outputs and mock reports

- `release-commit`: the validated commit, or empty when no batch exists.
- `ready`: true only after complete inspection finds no conflicts.
- `publication-plan`: JSON array with `name`, `version`, `tag`, `action`, and `conflicts`.
- `publication-needed`: whether incomplete GitHub work remains, independently of batch identity.
- `releases`: package, version, and tag for every package in the batch, including completed publication.

[expected-success.json](expected-success.json) is a mock partial-publication report: Node.js has a matching tag and published Release; Python needs both.
[expected-conflict.json](expected-conflict.json) is a mock report with a wrong Node.js tag identity.
These files describe the output contract, not observations of this repository or its active package versions.

Plan actions are `create-tag-and-release`, `create-release`, `none`, or `conflict`.
Wrong tag identities, draft Releases, and Releases without remote tags are conflicts.
All entries are inspected before conflict failure. No batch returns `ready=true` and an empty plan.
Invalid batches or trees, API errors, and fetch failures do not claim readiness. API errors are not missing releases.

The verifier checks mock reports and matching pins without GitHub API access.
Workflow tests check the template; the Action repository's Git/mock suite checks source and remote isolation.

Inspection is advisory, not a reservation. Publication must repeat preflight and race checks.
This example does not authorize publication or prove production permissions.
Local tests do not dispatch workflows. See [Release safety](../../README.md#release-safety) before hosted validation or deployment.
