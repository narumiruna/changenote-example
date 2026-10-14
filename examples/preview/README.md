# Publication preview

[workflow.yml](workflow.yml) is a template outside `.github/workflows/`. It is not active and local verification does not dispatch it. Its CLI and Action must use the same reviewed compatible full SHA as the root README.

The Action needs Linux, Bash, Git, gh, jq, standard coreutils, an installed compatible CLI, and only `contents: read`. No source checkout is required. The selected remote base branch, not local uncommitted files, determines the release.

Preview discovers the latest first-parent batch and verifies the complete release tree from its parent's notes/config, including supported current and legacy output. It reconstructs files only in a temporary repository and removes it afterward. Source files, index, refs, tags, and identity stay unchanged. It never creates tags, commits, PRs, or Releases.

## Outputs and mock reports

- `release-commit`: the validated commit, or an empty string for no batch.
- `ready`: true only after complete inspection finds no conflicts.
- `publication-plan`: JSON array with `name`, `version`, `tag`, `action`, and `conflicts`.

[expected-success.json](expected-success.json) is a mock partial-publication report: Node.js already has a matching tag and published Release; Python needs both. [expected-conflict.json](expected-conflict.json) is a mock report with a wrong Node.js tag identity. They are examples of the output contract, not observations of this repository or its active package versions.

Actions are `create-tag-and-release`, `create-release` (matching tag only), `none`, or `conflict`. Wrong tag identities, draft Releases, and Releases without remote tags are conflicts. All entries are inspected before conflict failure. No batch returns ready=true and an empty plan. Invalid batches/trees, API errors, and fetch failures fail without claiming readiness; API errors are not missing releases.

The verifier checks these mock reports and the matching pins. Template metadata/lint checks and real inspection with GitHub mocks run separately; the core Linux Action suite proves no source/remote writes. No real GitHub API request is needed for local verification.

Preview is advisory, not a reservation. State can change afterward. Actual publication must repeat its preflight and race checks. This example does not authorize publication, modify the active release workflow, or demonstrate production permissions.
