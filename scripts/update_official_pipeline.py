#!/usr/bin/env python3
"""Fetch official DP-GEN docs and refresh provenance artifacts.

This script keeps the repo-local raw/provenance layer reproducible without
making the LSP runtime depend on network access. Runtime code reads the checked
in structured rule index under ``src/dpgen_lsp/schema/dpgen_rules.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RULE_INDEX = ROOT / "src" / "dpgen_lsp" / "schema" / "dpgen_rules.json"
CAPABILITIES = ROOT / "lsp-capabilities.json"
RAW_ASSETS = ROOT / "raw" / "assets"
VERSION_INDEX = RAW_ASSETS / "dpgen-version-index.json"
READTHEDOCS_VERSIONS_API = "https://readthedocs.org/api/v3/projects/dpgen/versions/"
GITHUB_TAGS_API = "https://api.github.com/repos/deepmodeling/dpgen/tags?per_page=100"


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def load_rule_index() -> dict[str, Any]:
    return json.loads(RULE_INDEX.read_text(encoding="utf-8"))


def load_sources() -> list[dict[str, str]]:
    rules = load_rule_index()
    direct_sources = [
        source
        for source in rules.get("sourceProvenance", [])
        if source.get("kind") == "official_docs" and source.get("url")
    ]
    version_support = rules.get("versionSupport", {})
    doc_versions = version_support.get("documentedVersions", [])
    doc_pages = version_support.get("docPages", [])
    versioned_sources = []
    for version in doc_versions:
        for page in doc_pages:
            page_id = page.replace("/", "-").replace(".html", "")
            versioned_sources.append(
                {
                    "id": f"dpgen-docs-{version}-{page_id}",
                    "kind": "official_docs",
                    "label": f"DP-GEN {version} {page}",
                    "url": f"https://docs.deepmodeling.com/projects/dpgen/en/{version}/{page}",
                    "version": version,
                    "path": page,
                }
            )
    seen: set[str] = set()
    sources = []
    for source in [*direct_sources, *versioned_sources]:
        if source["url"] in seen:
            continue
        seen.add(source["url"])
        sources.append(source)
    return sources


def fetch_json(url: str, timeout: int) -> Any:
    req = Request(url, headers={"User-Agent": "dpgen-lsp-provenance/0.1"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_readthedocs_versions(timeout: int) -> list[dict[str, str | bool]]:
    versions: list[dict[str, str | bool]] = []
    url: str | None = READTHEDOCS_VERSIONS_API
    while url:
        payload = fetch_json(url, timeout)
        for item in payload.get("results", []):
            versions.append(
                {
                    "slug": item.get("slug", ""),
                    "type": item.get("type", ""),
                    "active": bool(item.get("active", False)),
                    "built": bool(item.get("built", False)),
                    "documentation": item.get("urls", {}).get("documentation", ""),
                    "vcs": item.get("urls", {}).get("vcs", ""),
                }
            )
        url = payload.get("next")
    return versions


def collect_release_tags(timeout: int) -> list[str]:
    payload = fetch_json(GITHUB_TAGS_API, timeout)
    if not isinstance(payload, list):
        return []
    return [str(item.get("name", "")) for item in payload if item.get("name")]


def write_version_index(timeout: int, fetched_at: str) -> dict[str, Any]:
    rules = load_rule_index()
    versions = collect_readthedocs_versions(timeout)
    tags = collect_release_tags(timeout)
    payload = {
        "schema": "DpgenVersionIndex/v1",
        "fetched_at": fetched_at,
        "sources": {
            "readthedocs": READTHEDOCS_VERSIONS_API,
            "github_tags": GITHUB_TAGS_API,
        },
        "policy": rules.get("versionSupport", {}),
        "readthedocsVersions": versions,
        "releaseTags": tags,
        "summary": {
            "readthedocsVersionCount": len(versions),
            "releaseTagCount": len(tags),
            "latestReleaseTag": tags[0] if tags else None,
        },
    }
    VERSION_INDEX.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def write_structured_release_tags(tags: list[str], fetched_at: str) -> None:
    if not tags:
        return
    rules = load_rule_index()
    support = rules.setdefault("versionSupport", {})
    support["knownReleaseTags"] = tags
    support["releaseTagsUpdatedAt"] = fetched_at
    RULE_INDEX.write_text(json.dumps(rules, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    capabilities = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    capabilities_support = capabilities.setdefault("dpgenVersionSupport", {})
    for key in (
        "policy",
        "readthedocsApi",
        "githubTagsApi",
        "documentedVersions",
        "knownReleaseTags",
        "docPages",
        "dpgenVersionFields",
        "runtimeVersionFields",
        "relatedRuntimeVersionFields",
        "compatibilityModes",
        "releaseTagsUpdatedAt",
    ):
        if key in support:
            capabilities_support[key] = support[key]
    CAPABILITIES.write_text(
        json.dumps(capabilities, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def fetch_source(source: dict[str, str], timeout: int) -> dict[str, str | int]:
    url = source["url"]
    req = Request(url, headers={"User-Agent": "dpgen-lsp-provenance/0.1"})
    with urlopen(req, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get("content-type", "")
        final_url = response.geturl()
        status = response.status
    parser = TextExtractor()
    parser.feed(body.decode("utf-8", errors="replace"))
    text = parser.text()
    return {
        "id": source["id"],
        "label": source["label"],
        "url": url,
        "version": source.get("version", ""),
        "path": source.get("path", ""),
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "sha256": hashlib.sha256(body).hexdigest(),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text[:20000],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--offline", action="store_true", help="Only validate checked-in files.")
    args = parser.parse_args(argv)

    if args.offline:
        sources = load_sources()
        if not sources:
            raise SystemExit("no official sources in rule index")
        if not VERSION_INDEX.exists():
            raise SystemExit("missing version index")
        return 0

    RAW_ASSETS.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    version_index = write_version_index(args.timeout, fetched_at)
    write_structured_release_tags(version_index["releaseTags"], fetched_at)
    sources = load_sources()
    fetched = [fetch_source(source, args.timeout) for source in sources]
    payload = {
        "schema": "DpgenOfficialDocsSnapshot/v1",
        "fetched_at": fetched_at,
        "pipeline": [
            "official-docs-fetch",
            "structured-schema-rules",
            "source-provenance",
            "tests",
            "lsp-runtime",
        ],
        "versionSummary": version_index["summary"],
        "sources": fetched,
    }
    (RAW_ASSETS / "dpgen-official-docs.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    provenance = {
        "schema": "SourceProvenance/v1",
        "fetched_at": fetched_at,
        "rule_index": str(RULE_INDEX.relative_to(ROOT)),
        "version_index": str(VERSION_INDEX.relative_to(ROOT)),
        "sources": [
            {
                key: item[key]
                for key in (
                    "id",
                    "label",
                    "url",
                    "version",
                    "path",
                    "final_url",
                    "status",
                    "sha256",
                )
            }
            for item in fetched
        ],
    }
    (RAW_ASSETS / "source-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "sources": len(fetched), "raw_assets": str(RAW_ASSETS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
