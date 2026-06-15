"""DP-GEN version support helpers for diagnostics and agent capabilities."""

from __future__ import annotations

from typing import Any

from .official_rules import version_support


def dpgen_version_support_payload() -> dict[str, Any]:
    support = version_support()
    return {
        "policy": support.get("policy", ""),
        "readthedocsApi": support.get("readthedocsApi", ""),
        "githubTagsApi": support.get("githubTagsApi", ""),
        "documentedVersions": list(support.get("documentedVersions", [])),
        "knownReleaseTags": list(support.get("knownReleaseTags", [])),
        "docPages": list(support.get("docPages", [])),
        "runtimeVersionFields": list(support.get("runtimeVersionFields", [])),
        "compatibilityModes": list(support.get("compatibilityModes", [])),
    }


def declared_dpgen_version(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("dpgen_version", "dpgenVersion"):
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
