# Manifest Version Sources

This fixture uses four explicit version sources, all starting at `1.2.3`:

| Package | Source | Selected field | Expected version |
| --- | --- | --- | --- |
| `pkg-python` | `pyproject.toml` | `project.version` | `1.3.0` |
| `pkg-rust` | `Cargo.toml` | `package.version` | `1.2.4` |
| `pkg-node` | `package.json` | top-level `version` | `1.2.4` |
| `pkg-go` | `VERSION` | plain-text SemVer | `1.2.4` |

Run from the repository root:

```sh
work=$(mktemp -d)
cp -R examples/manifests/fixture/. "$work/"
changenote --root "$work" status
```

Compare output with [`expected-status.json`](expected-status.json). This does not write manifests or consume notes. The fixture config has no effect on this repository's active config.

[`expected-package.json`](expected-package.json) is illustrative release output. Compare it at the byte level with `fixture/packages/pkg-node/package.json`: only the top-level version token differs. Tabs, CRLF, an exact large exponent, the nested `version` field, and the absence of a final newline remain unchanged. TOML comments and unrelated fields are also preserved.

Use the example verifier for read-only checks. Actual release writes are tested by the core Rust suite in temporary directories. Do not run release commands against the active packages merely to compare output.

Dynamic Python versions, Poetry-only versions, inherited Cargo workspace versions, duplicate top-level JSON version keys, prereleases, and JSONC are not supported. Changenote does not update dependency ranges or lockfiles. These are version-source fixtures, not complete language build projects.
