# Changelog

## Unreleased

- Upgraded `reports/docstring-wiki-raw-traceability.json` to the OpenQC `openqc.lsp.traceability.v1` contract with `serverId`, `languageId`, `docstrings`, `wikiSources`, `ruleIds`, `sourceUrls`, and `rawManifest` sections. Rule identifiers now follow `DPGEN-<FILE_ROLE>-<CATEGORY>-NNN`.

## 0.1.2 - 2026-07-16

- Added tag-only PyPI release automation using GitHub OIDC Trusted Publishing
  and the protected `pypi` environment.
- Added a fresh-wheel gate covering `dpgen-lsp --help`, the agent CLI, and
  canonical valid, invalid, and runtime-log fixtures.
- Added machine-readable `releaseVersion` and `releaseTag` capability metadata
  and aligned public project URLs with `newtontech/dpgen-lsp`.
- Added native `make format`, `make lint`, `make typecheck`, `make test`, and
  `make check` gates for local and CI release verification.
- Corrected the declared Python floor from 3.9 to 3.10 to match the existing
  runtime type syntax, and verified CI on Python 3.10 and 3.12.

## 0.1.0 - 2026-06-15

- Added the repeatable official-docs pipeline from DP-GEN documentation capture to structured schema/rules, provenance assets, tests, and LSP runtime capabilities.
- Added release-tag-aware DP-GEN version indexing through upstream `v0.13.3`.
- Added output-log diagnostics, smoke fixtures, and OpenQC capability metadata for family-level maturity checks.

## 0.0.1

- Restore OpenQC family-gate metadata for the force-updated DP-GEN LSP mainline.
- Add canonical valid and invalid fixture directories used by OpenQC release checks.
- Keep the manifest aligned with the currently implemented agent CLI operations.
