# Versioned DP-GEN LSP Pipeline

Tracking issue: https://github.com/newtontech/dpgen-lsp/issues/1

This repository keeps DP-GEN input validation reproducible by treating the
official documentation pipeline as a checked-in build artifact:

1. Fetch official DP-GEN documentation and version indexes.
2. Sync structured schema/rule release tags.
3. Write source provenance snapshots.
4. Run tests and static checks.
5. Verify the LSP runtime and OpenQC integration.

## Source of Truth

- `src/dpgen_lsp/schema/dpgen_rules.json` is the runtime rule index.
- `raw/assets/dpgen-official-docs.json` is the fetched official-docs snapshot.
- `raw/assets/dpgen-version-index.json` records ReadTheDocs versions and GitHub release tags.
- `raw/assets/source-provenance.json` maps fetched pages back to rule/provenance inputs.
- `lsp-capabilities.json` exposes the agent/OpenQC manifest surface.

The refresh script updates both `dpgen_rules.json` and `lsp-capabilities.json`
from the fetched GitHub release tags so the runtime and manifest stay aligned
with current DP-GEN releases.

## Refresh

```bash
python3 scripts/update_official_pipeline.py
python3 scripts/update_official_pipeline.py --offline
```

The online refresh fetches:

- ReadTheDocs project versions from `https://readthedocs.org/api/v3/projects/dpgen/versions/`
- GitHub release tags from `https://api.github.com/repos/deepmodeling/dpgen/tags?per_page=100`
- Versioned run/simplify parameter pages for `latest`, `stable`, `devel`, `v0.13.3`, and `v0.12.1`

## Verification

```bash
python3 -m pytest -q
python3 -m black --check scripts/update_official_pipeline.py src/dpgen_lsp/schema/versioning.py tests/test_official_pipeline.py
python3 -m ruff check scripts/update_official_pipeline.py src/dpgen_lsp/schema/versioning.py tests/test_official_pipeline.py
python3 -m compileall -q src tests scripts
PYTHONPATH=src python3 -m dpgen_lsp.tool capabilities
```

OpenQC freshness is verified from the OpenQC checkout:

```bash
npm run lsp:check-latest
```

The DP-GEN row should report `status` as `latest`, `dirty` as `no`, and
`agentHelp` as `pass`.

## Runtime Contract

The runtime capabilities payload exposes:

- `pipeline`: `official-docs-fetch -> structured-schema-rules -> source-provenance -> tests -> lsp-runtime`
- `dpgenVersionSupport.knownReleaseTags`: release tags synchronized from GitHub
- `dpgenVersionSupport.releaseTagsUpdatedAt`: timestamp matching `raw/assets/dpgen-version-index.json`
- `standardLsp.textDocument`: standard LSP handlers for generic Python/C++/VS Code clients

Unknown explicit `dpgen_version` declarations are reported as non-blocking
`version.unverified` diagnostics. Known release tags are accepted without that
warning.
