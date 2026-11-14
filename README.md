# changenote-example

Tested examples for the [changenote CLI](https://github.com/changenote/changenote) and [GitHub Actions](https://github.com/changenote/action).
Inspect change notes, SemVer release plans, version sources, and release workflows across Python, Node.js, Rust, and Go.

The fixtures in `examples/` have separate configurations and known starting versions.
The packages in `packages/` use the root configuration and have a real release workflow.

## Install and use

Choose one of these three methods.
The uv and uvx methods require [uv](https://docs.astral.sh/uv/).
Cargo installation requires stable Rust with edition 2024 support.

### uv

Install the CLI, then run it:

```sh
uv tool install changenote
changenote --help
```

### uvx

Run the CLI without a separate installation:

```sh
uvx changenote --help
```

### Cargo

Install the CLI, then run it:

```sh
cargo install changenote --locked
changenote --help
```

These commands use published releases.
For exact fixture output, use the source revision in [Verify all examples](#verify-all-examples).

The CLI includes agent instructions:

```sh
changenote skill
```

With uvx, use `uvx changenote skill` instead.
See [AGENTS.md](AGENTS.md) for this repository's agent requirements.

## Try an isolated fixture

Run these commands from the repository root:

```sh
work=$(mktemp -d)
cp -R examples/notes/mixed/fixture/. "$work/"
changenote --root "$work" status
```

`status` prints JSON without changing files.
Compare it with [expected-status.json](examples/notes/mixed/expected-status.json):

| Package | Starting version | Planned version | Bump |
| --- | --- | --- | --- |
| `pkg-node` | `1.2.3` | `1.2.4` | patch |
| `pkg-python` | `1.2.3` | `1.3.0` | minor |

Keep experiments in temporary fixture copies.
Never copy sample notes into the root `.changenote/` directory: it is an active release queue.

## Examples

| Guide | Coverage |
| --- | --- |
| [Change notes](examples/notes/README.md) | Patch, major, shared, empty, highest-bump, mixed-bump, and multiline notes |
| [Release planning](examples/planning/README.md) | Note paths, automatic note names, and fixed version groups |
| [Version sources](examples/manifests/README.md) | `VERSION`, `pyproject.toml`, `Cargo.toml`, and `package.json` |
| [PR note checks](examples/check/README.md) | Committed changes, release exemptions, and validation failures |
| [Release Actions](examples/actions/README.md) | Root, composed, command-hook, and external-CI workflow templates |
| [Publication inspection](examples/inspect/README.md) | Read-only workflow template and mock publication reports |

These examples cover specific CLI and Action revisions, not every feature of the latest release.
The workflow templates remain inactive outside `.github/workflows/`.
Expected changelog files are reference output; `status` does not generate them.

## Verify all examples

Verification requires Git, uv, Python 3.11 or later, and stable Rust with edition 2024 support.
Install the exact CLI revision used by [CI](.github/workflows/ci.yml):

```sh
cargo install --git https://github.com/changenote/changenote --rev c644511a48a4c09a72b1d7a7b58dc6d6d8f374f5 --locked
```

This fixture source pin is separate from published CLI versions and the release Action pin.
Run the checks from the repository root:

```sh
uv run --no-project python scripts/verify_examples.py --cli changenote
uv run --no-project --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v
```

For a local CLI build, pass its absolute executable path to `--cli`.

- The verifier checks 11 fixtures, note creation, default and detailed plans, PR note checks, inspection mock reports, and failure cases.
  - It uses temporary copies and checks that the source repository stays unchanged.
  - It compares expected changelog excerpts with planned notes; it does not generate release files.
- The workflow tests check Action pins, permissions, event routing, CLI reuse, and publication guards.
  - They also check template syntax when `actionlint` is installed.

These checks do not run `version`, `tag`, or publication, and do not contact GitHub.
Actual release writes are tested in the core CLI repository.

## Repository packages

The active [configuration](.changenote/config.json) uses a plain-text `VERSION` file in each package directory.
These package versions are independent of fixture versions.

| Package | Directory | Package guide |
| --- | --- | --- |
| `pkg-python` | `packages/pkg-python` | [Python](packages/pkg-python/README.md) |
| `pkg-node` | `packages/pkg-node` | [Node.js](packages/pkg-node/README.md) |
| `pkg-rust` | `packages/pkg-rust` | [Rust](packages/pkg-rust/README.md) |
| `pkg-go` | `packages/pkg-go` | [Go](packages/pkg-go/README.md) |

The manifest fixture has its own configuration; it does not change these active version sources.
The package guides describe their run or test commands.
The Python package has no automated tests; run its smoke check from the repository root with Python 3.14 or later:

```sh
uv run --locked pkg-python
```

Expected output: `Hello from pkg-python!`.

### Historical Python release

[PR #6](https://github.com/changenote/example/pull/6) added fictional Python notes that [PR #7](https://github.com/changenote/example/pull/7) published as `pkg-python@0.2.0`.
The package does not implement the custom greeting or formatting fixes described in those entries.
Do not use the historical changelog or release text as evidence of package features.
Use the isolated [highest-bump fixture](examples/notes/highest/) to test patch and minor notes instead.

## Release automation

The active [Release workflow](.github/workflows/release.yml) runs only on `main`.
It has two steps: checkout, then `changenote/action@339f86c81883cb39f3003a38534ca87c97d1d7c2` with `operation: auto`.

| Trigger | Behavior |
| --- | --- |
| Push to `main` | Manage the Release PR and publish incomplete validated batches as Git tags and GitHub Releases |
| Manual dispatch on `main` | Manage the Release PR only; no publication retry menu |

The root Action installs the CLI and prepares project tools.
It uses the default latest stable PyPI CLI, installed as a prebuilt wheel through uv outside the checkout.
It does not build the CLI from source.
The Action SHA pins Action code, not the CLI; different jobs or runs can resolve different CLI versions.
The Action does not merge PRs or upload packages to registries.

Use the inactive [composed template](examples/actions/composed.yml) for separate PR management, inspection, and exact-commit publication jobs.
Its manual menu supports explicit publication retries after review.
Use the [command-hook template](examples/actions/command-hooks.yml) for project-owned publication scripts.
Use the [external CI template](examples/actions/external-ci.yml) for external CI and Docker jobs at the verified release commit.
The [inspection template](examples/inspect/README.md) provides read-only reports with `contents: read` and no consumer checkout.
Inspection returns completed batches too; automatic publication must check `publication-needed`, not only `release-commit`.

## Release safety

- Do not dispatch the Release workflow to test examples or add fictional notes to force a release.
- Do not run `version`, `tag`, or publication against active packages to compare fixture output.
  - If you test `version`, use a disposable fixture checkout: it updates versions and changelogs, saves a release batch, and consumes notes.
- Preserve the historical [release batch](.changenote/releases.json), which contains legacy `notes` fields.
  - Do not change its format, move published tags, replace Releases, or rewrite release text.
- Keep workflow templates inactive until a maintainer reviews them for deployment.
  - Validate tools, token permissions, branch rules, caches, and publication in an authorized disposable repository.
  - PRs created with `GITHUB_TOKEN` do not start PR workflows automatically; review required checks and token setup separately.

Local verification does not prove hosted release readiness or authorize a real release.
For Action interface changes and publication recovery, use the [pinned migration guide](https://github.com/changenote/action/blob/339f86c81883cb39f3003a38534ca87c97d1d7c2/docs/migration.md).
To stop automation, disable the Release workflow.
For rollback, restore the previous workflow with its matching Action SHA and CLI version.
