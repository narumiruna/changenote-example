# changenote-example

Tested examples for the language-independent [changenote](https://github.com/changenote/changenote) CLI. Each fixture has a separate config and known starting versions. Example notes are outside the active `.changenote/` directory and cannot trigger the repository's release workflow.

## Install

Requires stable Rust with edition 2024 support. Git is required for PR checks. Python 3.11 or later and uv are required only for the example verifier.

Install the exact CLI revision used by fixture CI:

```sh
cargo install --git https://github.com/changenote/changenote --rev c644511a48a4c09a72b1d7a7b58dc6d6d8f374f5 --locked
```

This is a pinned source revision, not a promise that the latest published binary has the same features. Install the compatible CLI before running these examples.

## Examples

| Feature | Example | Status |
| --- | --- | --- |
| Single-package patch | [patch fixture](examples/notes/patch/) | Supported |
| Major bump with migration steps | [major fixture](examples/notes/major/) | Supported |
| Shared patch across packages | [shared fixture](examples/notes/shared/) | Supported |
| No pending notes | [empty fixture](examples/notes/empty/) | Supported |
| Highest requested bump applied once | [highest fixture](examples/notes/highest/) | Supported |
| Different bumps in one note | [mixed fixture](examples/notes/mixed/) | Supported |
| Bump groups and multiline Markdown | [multiline fixture](examples/notes/multiline/) | Supported |
| Manifest sources and exact JSON formatting | [manifest guide](examples/manifests/README.md) | Supported |
| Read-only PR note check and explicit exemption | [PR check guide](examples/check/README.md) | Supported |
| Release PRs, tags, and GitHub Releases | [release workflow](.github/workflows/release.yml) | Pinned to the merged seven-entry Action API; not dispatched by verification |
| Complete root workflow and reusable operation Actions | [Action templates](examples/actions/README.md) | Inactive; use the same full Action SHA as the release workflow |
| Note provenance and automatic names | [planning guide](examples/planning/README.md) | Supported |
| Fixed version groups | [fixed fixtures](examples/planning/README.md#fixed-version-groups) | Supported |
| Read-only publication inspection | [inspection template and mock reports](examples/inspect/README.md) | Supported; not dispatched by verification |
| Linked groups | — | Not supported |
| Dependency propagation and lockfile updates | — | Not supported |
| Snapshots and prereleases | — | Not supported |
| Registry publication | — | Not provided by the reusable Actions |

See the [note guide](examples/notes/README.md) for commands and expected output.

## Safe setup

Run these commands from this repository root. Copy a fixture into a temporary directory, then inspect its plan:

```sh
work=$(mktemp -d)
cp -R examples/notes/mixed/fixture/. "$work/"
changenote --root "$work" status
```

The output must match [`examples/notes/mixed/expected-status.json`](examples/notes/mixed/expected-status.json). Starting versions are `1.2.3`: `pkg-node` gets `1.2.4`, and `pkg-python` gets `1.3.0`.

`status` does not change files. The `expected-*-CHANGELOG.md` files are illustrative generated output, not existing fixture changelogs. The verifier does not run `version`, `tag`, or publication. If you choose to run `version` manually, do so only in a disposable fixture checkout: it updates versions, writes changelogs and the release batch, and deletes consumed notes.

Never copy sample notes into this repository's active `.changenote/`. That directory is used by real release automation.

### Historical Python example release

[PR #6](https://github.com/changenote/example/pull/6) added fictional Python notes to the active release queue.
[PR #7](https://github.com/changenote/example/pull/7) consumed them and published `pkg-python@0.2.0`.
Its changelog and release text describe a customizable greeting and a formatting fix, but neither change was implemented.
The Python package still prints only `Hello from pkg-python!`.
Do not use those entries as evidence of package features.
The published release data is kept unchanged.

Use the isolated [highest-bump fixture](examples/notes/highest/) to test patch and minor notes without a real release.

## Verify all examples

```sh
uv run --no-project python scripts/verify_examples.py --cli changenote
uv run --no-project --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v
```

For local CLI development, pass the absolute path to the built executable instead. The verifier copies fixtures into temporary directories and checks eleven fixtures, default/detailed status JSON, named/generated note creation, fixed-group plans, PR note checks, inspection mock reports, matching Action pins, expected exit codes, and failure paths. It verifies that read-only commands and the source repository do not change. It does not run release commands or contact GitHub. Generated changelog and JSON output are covered by the core CLI's Rust tests; static expected excerpts are checked against status details here.

[CI](.github/workflows/ci.yml) installs the fixture CLI pin, runs the fixture verifier, and checks release workflow metadata. uv supplies PyYAML for the workflow tests. These checks do not run release commands or contact GitHub.

The [release workflow](.github/workflows/release.yml) uses the separate config-driven Action pin. It runs only on `main` pushes or explicit manual dispatch. Do not dispatch it to test examples.

## Active package configuration

The root `.changenote/config.json` still uses plain-text `VERSION` for all packages:

| Package | Directory | Active version source |
| --- | --- | --- |
| `pkg-python` | `packages/pkg-python` | `VERSION` |
| `pkg-node` | `packages/pkg-node` | `VERSION` |
| `pkg-rust` | `packages/pkg-rust` | `VERSION` |
| `pkg-go` | `packages/pkg-go` | `VERSION` |

These versions are independent of fixture starting versions. Changenote updates only configured version files. It does not synchronize other manifests, dependency ranges, or lockfiles and does not run language-specific publication tools. The isolated manifest example changes no active package settings.

See the Node.js, Rust, and Go package READMEs for their test commands. The Python package has no automated test suite; run `uv run --locked pkg-python` from this root for a smoke check (Python 3.14 or later). It must print `Hello from pkg-python!`. The root Python project uses a uv workspace; the other packages have their own test tools.

## Action interfaces

The [root and composed templates](examples/actions/README.md) use the seven-entry API from merged [Action PR #9](https://github.com/changenote/action/pull/9).
The public entry points are root, `setup`, `prepare`, `check`, `manage-pr`, `inspect`, and `publish`.
The templates and active Release workflow pin the same merge commit, `339f86c81883cb39f3003a38534ca87c97d1d7c2`.
The former release, select, and preview Action paths are removed without aliases.

Root accepts only `hooks` and `auto`. Individual operations use standalone Actions.
The composed template separates PR management, read-only inspection, and exact-commit publication.
Inspection includes completed batches; automatic GitHub work must check `publication-needed`, not only commit presence.
The template tests do not dispatch workflows or change release data.

## Release safety

The release workflow pins the root `changenote/action` to merged commit `339f86c81883cb39f3003a38534ca87c97d1d7c2`.
On ordinary pushes, root explicitly uses `operation: auto` for PR management and incomplete GitHub publication.
Root's default `hooks` mode does not enable built-in publication.

Action calls omit `version` and use the default `latest` stable PyPI CLI, installed as a prebuilt wheel through uv outside the consumer checkout.
Installation never builds the CLI from source or falls back to a source build.
Fixture CI independently retains source revision `c644511a48a4c09a72b1d7a7b58dc6d6d8f374f5`.

The active workflow has only checkout and root `auto`, with no manual operation menu.
Manual dispatch only manages the Release PR; it does not publish an older batch.
The root Action installs the CLI and prepares project tools, so no separate setup or preparation steps are needed.
For independent inspection or explicit exact-commit publication retries, use the inactive [composed template](examples/actions/composed.yml) after review. Its manual menu is not part of the active workflow.
The Action SHA pins the Action code, not the CLI. Separate jobs and runs can resolve different latest CLI versions.
The inactive read-only [inspection template](examples/inspect/README.md) uses only `setup` and `inspect`, with `contents: read` and no consumer checkout.
The Action never merges PRs or uploads to package registries.
CLI and Action revisions are separate; see the [migration guide](https://github.com/changenote/action/blob/339f86c81883cb39f3003a38534ca87c97d1d7c2/docs/migration.md).

The batch published by [PR #7](https://github.com/changenote/example/pull/7) contains legacy `notes` fields. Its four GitHub Releases already exist. The Action validates the parent release plan and complete generated tree, then checks every remote tag and GitHub Release. A fully published legacy batch is a successful no-op, including explicit publication retries. Missing tags, missing or draft Releases, tag conflicts, and invalid release data stop without remote writes for that batch. The workflow needs no repository-specific commit or blob exceptions.

Do not edit or delete the historical batch, move tags, replace Releases, or add sample notes to force migration. New Release PRs write metadata-only batches. After a real package change produces and merges a new batch, ordinary pushes publish it through the same Action.

Disable the workflow to stop automation. To undo this migration, restore the previous workflow and its matching Action SHA and CLI version together; do not change historical release data.

Local fixture and workflow metadata tests do not prove hosted cache restoration, token permissions, branch rules, or publication on GitHub. A maintainer must test those separately in an authorized disposable consumer repository. No real release is authorized by local verification.
