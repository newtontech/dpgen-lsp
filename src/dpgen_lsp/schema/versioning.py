"""DP-GEN version support helpers for diagnostics and agent capabilities.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

from typing import Any

from .official_rules import version_support


def dpgen_release_version_fields() -> list[str]:
    support = version_support()
    configured = support.get("dpgenVersionFields")
    if isinstance(configured, list) and configured:
        return [str(field) for field in configured]
    return ["dpgen_version", "dpgenVersion"]


def related_runtime_version_fields() -> list[str]:
    support = version_support()
    configured = support.get("relatedRuntimeVersionFields")
    if isinstance(configured, list):
        return [str(field) for field in configured]
    runtime_fields = [str(field) for field in support.get("runtimeVersionFields", [])]
    release_fields = set(dpgen_release_version_fields())
    return [field for field in runtime_fields if field not in release_fields]


def dpgen_version_support_payload() -> dict[str, Any]:
    support = version_support()
    documented_versions = list(support.get("documentedVersions", []))
    release_tags = list(support.get("knownReleaseTags", []))
    doc_pages = list(support.get("docPages", []))
    return {
        "policy": support.get("policy", ""),
        "readthedocsApi": support.get("readthedocsApi", ""),
        "githubTagsApi": support.get("githubTagsApi", ""),
        "documentedVersions": documented_versions,
        "knownReleaseTags": release_tags,
        "docPages": doc_pages,
        "dpgenVersionFields": dpgen_release_version_fields(),
        "runtimeVersionFields": list(support.get("runtimeVersionFields", [])),
        "relatedRuntimeVersionFields": related_runtime_version_fields(),
        "compatibilityModes": list(support.get("compatibilityModes", [])),
        "releaseTagsUpdatedAt": support.get("releaseTagsUpdatedAt", ""),
        "coverage": {
            "latestReleaseTag": release_tags[0] if release_tags else "",
            "releaseTagCount": len(release_tags),
            "documentedVersionCount": len(documented_versions),
            "docPageCount": len(doc_pages),
            "completeReleaseTagIndex": bool(release_tags),
        },
    }


def declared_dpgen_version(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in dpgen_release_version_fields():
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def is_documented_version(version: str) -> bool:
    normalized = version.strip()
    documented = set(version_support().get("documentedVersions", []))
    release_tags = set(version_support().get("knownReleaseTags", []))
    return (
        normalized in documented
        or f"v{normalized}" in documented
        or normalized in release_tags
        or f"v{normalized}" in release_tags
    )
