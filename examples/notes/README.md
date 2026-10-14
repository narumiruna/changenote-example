# Note Examples

All fixtures start at `1.2.3`. Each directory contains `fixture/`, `expected-status.json`, and illustrative `expected-*-CHANGELOG.md` files. Only files inside the copied `fixture/` participate in its plan.

| Fixture | Notes | Expected result |
| --- | --- | --- |
| `patch` | One Python patch | `1.2.4` |
| `highest` | Two patches and one minor | One bump to `1.3.0`, not three bumps |
| `mixed` | Python minor and Node.js patch in one note | Python `1.3.0`, Node.js `1.2.4` |
| `multiline` | Minor with nested list and fenced code | `1.3.0`; Markdown stays inside its list item |

## Inspect existing notes

From the repository root:

```sh
work=$(mktemp -d)
cp -R examples/notes/highest/fixture/. "$work/"
changenote --root "$work" status
changenote --root "$work" status --include-note-bumps
```

Default output must match `highest/expected-status.json`. The opt-in output adds `note_bumps` aligned with `notes`. The highest bump controls the package version, but each note retains its own heading in the changelog. Empty bump groups are omitted.

## Create a mixed-bump note

This changes only the temporary fixture:

```sh
work=$(mktemp -d)
cp -R examples/notes/mixed/fixture/. "$work/"
rm "$work/.changenote/shared.md"
changenote --root "$work" add shared --minor pkg-python --patch pkg-node -m "Update shared API"
changenote --root "$work" status
```

The output must match `mixed/expected-status.json`. The generated note contains:

```markdown
---
pkg-node: patch
pkg-python: minor
---

Update shared API
```

Repeat each bump option for more packages. Do not combine mixed-bump options with `--package` or `--bump`. Conflicting assignments, unknown packages, and an existing note filename fail without overwriting files. The original shared-bump syntax remains supported:

```sh
changenote --root "$work" add another -p pkg-python -p pkg-node --bump patch -m "Fix shared output"
```

That last command adds another note, so the plan no longer equals the original mixed fixture's expected JSON.

## Generated changelog excerpts

The expected changelog files show output from a release, not files written by `status`. For example, `mixed/expected-pkg-python-CHANGELOG.md` has `Minor Changes`; Node.js has `Patch Changes` for the same summary. New entries preserve the existing title and introduction above version headings. The verifier never consumes fixture notes or creates tags.
