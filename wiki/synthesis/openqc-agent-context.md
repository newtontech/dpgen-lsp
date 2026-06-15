# OpenQC Agent Context

OpenQC should route DP-GEN JSON inputs to `dpgen-lsp` using the `dpgen-lsp-tool`
agent CLI for preflight diagnostics. The expected DiagnosticEnvelope/v1 output
includes `manual_ref`, `fix_hints`, `blocking`, and source-provenance-backed
diagnostic codes so agents can repair inputs before launching DP-GEN.

## Traceability Contract

`scripts/check_docstring_traceability.py --write-report` emits
`reports/docstring-wiki-raw-traceability.json` using the
`openqc.lsp.traceability.v1` schema. The report enumerates every code
docstring, every wiki page, the structured rule identifiers, the upstream
source URLs, and the raw asset manifest so the OpenQC family gate can verify
end-to-end provenance without faked links.

Rule identifiers follow `DPGEN-<FILE_ROLE>-<CATEGORY>-NNN`, where
`<FILE_ROLE>` is `PARAM` for `param.json` workflow rules, `MACHINE` for
`machine.json` rules, and `CROSS` for cross-artifact stage alignment rules.
`<CATEGORY>` is `LINT`, `PATH`, `SCHEMA`, `SCASS`, or `STAGE`, derived
deterministically from the legacy rule code in
`src/dpgen_lsp/schema/dpgen_rules.json`.

## Traceability Sources

- Raw evidence: `raw/assets/source-provenance.json`
- Rule index: `src/dpgen_lsp/schema/dpgen_rules.json`
- Capability manifest: `lsp-capabilities.json`
