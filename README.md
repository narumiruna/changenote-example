# changenote-example

Tested examples for the language-independent [changenote](https://github.com/narumiruna/changenote) CLI. Each fixture has a separate config and known starting versions. Example notes are outside the active `.changenote/` directory and cannot trigger the repository's release workflow.

## Install

Requires stable Rust with edition 2024 support. Git is required for PR checks. Python 3.11 or later and uv are required only for the example verifier.

Install the exact CLI revision used by the workflows:

```sh
cargo install --git https://github.com/narumiruna/changenote --rev c97ca89a7fcc7c37bad87d5fb9316ef5c1bcf7ce --locked
```

This is a pinned source revision, not a promise that the latest published binary has the same features. Install the compatible CLI before running these examples.

## Examples

| Feature | Example | Status |
| --- | --- | --- |
| Single-package patch | [patch fixture](examples/notes/patch/) | Supported |
| Highest requested bump applied once | [highest fixture](examples/notes/highest/) | Supported |
| Different bumps in one note | [mixed fixture](examples/notes/mixed/) | Supported |
| Bump groups and multiline Markdown | [multiline fixture](examples/notes/multiline/) | Supported |
| Manifest sources and exact JSON formatting | [manifest guide](examples/manifests/README.md) | Supported |
| Read-only PR note check and explicit exemption | [PR check guide](examples/check/README.md) | Supported |
| Release PRs, tags, and GitHub Releases | [release workflow](.github/workflows/release.yml) | Supported; not run by verification |
| Fixed or linked groups | — | Not supported |
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

Never copy all sample notes into this repository's active `.changenote/`. That directory is used by real release automation.

## Verify all examples

```sh
uv run --no-project python scripts/verify_examples.py --cli changenote
```

For local CLI development, pass the absolute path to the built executable instead. The verifier copies fixtures into temporary directories and checks status JSON, mixed-bump creation, PR note checks, expected exit codes, and failure paths. It verifies that read-only commands and the source repository do not change. It does not run release commands or contact GitHub. Generated changelog and JSON output are covered by the core CLI's Rust tests; static expected excerpts are checked against status details here.

[Example CI](.github/workflows/examples.yml) installs the same pinned source revision and runs this verifier. The release workflow is separate and runs only on `main` pushes or explicit manual dispatch. Do not dispatch it to test examples.

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

## Release safety

The release workflow pins CLI and both Actions to the same reviewed full commit SHA. Update those pins together. The compatible publication Action verifies either the complete current output tree or the complete legacy output tree; it rejects manual edits and mixed profiles. It can verify an older saved batch after upgrading, without moving tags or replacing releases.

The source revision for these examples is under review. Merge the core implementation before merging a workflow-pin update that depends on it. Local fixture verification does not prove production permissions, branch rules, or publication on GitHub. Test those separately in a disposable consumer repository when release testing is authorized.
