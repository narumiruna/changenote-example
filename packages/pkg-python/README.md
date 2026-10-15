# pkg-python

This example package prints `Hello from pkg-python!`.
It does not accept a custom name or greeting.

From the repository root, run:

```sh
uv run --locked pkg-python
```

## Release correction

The `0.2.0` entries in [CHANGELOG.md](CHANGELOG.md) and the [GitHub Release](https://github.com/narumiruna/changenote-example/releases/tag/changenote/pkg-python%40v0.2.0) came from fictional example notes in [PR #6](https://github.com/narumiruna/changenote-example/pull/6).
No customizable greeting or output formatting fix was implemented in that release.
The published release data is kept unchanged.

Use the isolated [highest-bump fixture](../../examples/notes/highest/) to test patch and minor notes.
Do not add fictional notes to the active `.changenote/` directory.
