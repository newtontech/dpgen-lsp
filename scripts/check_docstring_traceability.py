#!/usr/bin/env python3
"""Check code docstrings, LLM Wiki pages, and raw evidence traceability.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "docs",
    "node_modules",
    "out",
    "raw",
    "target",
    "tests",
    "venv",
    "wiki",
}

WIKI_RE = re.compile(r"(?<![A-Za-z0-9_./-])(wiki/[A-Za-z0-9_./%+@:#=-]+?\.md)(?:#[A-Za-z0-9_.-]+)?")
RAW_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(raw/[A-Za-z0-9_./%+@:#=-]+\.[A-Za-z0-9][A-Za-z0-9_-]*)"
)


@dataclass
class DocstringRecord:
    file: str
    line: int
    kind: str
    linked: bool
    wiki_refs: list[str]
    broken_wiki_refs: list[str]


@dataclass
class WikiRecord:
    file: str
    raw_refs: list[str]
    missing_raw_refs: list[str]
    refs_missing_from_manifest: list[str]


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def extract_wiki_refs(text: str) -> list[str]:
    return sorted(set(match.group(1).rstrip(".,);]") for match in WIKI_RE.finditer(text)))


def extract_raw_refs(text: str) -> list[str]:
    refs = []
    for match in RAW_RE.finditer(text):
        ref = match.group(1).rstrip(".,);]")
        if ref.endswith("`"):
            ref = ref[:-1]
        refs.append(ref)
    return sorted(set(refs))


def resolve_existing_wiki_refs(root: Path, refs: Iterable[str]) -> list[str]:
    broken = []
    for ref in refs:
        if not (root / ref).is_file():
            broken.append(ref)
    return broken


def iter_python_docstrings(path: Path) -> Iterable[tuple[int, int, int, int, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return

    nodes: list[ast.AST] = [tree]
    nodes.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef))
    )
    for node in nodes:
        if not getattr(node, "body", None):
            continue
        first = node.body[0]  # type: ignore[index]
        value = getattr(first, "value", None)
        if not (
            isinstance(first, ast.Expr)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and hasattr(first, "end_lineno")
            and hasattr(first, "end_col_offset")
        ):
            continue
        yield first.lineno, first.col_offset, first.end_lineno, first.end_col_offset, value.value


def scan_docstrings(root: Path) -> list[DocstringRecord]:
    records: list[DocstringRecord] = []

    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        for line, _col, _end_line, _end_col, docstring in iter_python_docstrings(path):
            refs = extract_wiki_refs(docstring)
            records.append(
                DocstringRecord(
                    file=relpath(path, root),
                    line=line,
                    kind="python-docstring",
                    linked=bool(refs),
                    wiki_refs=refs,
                    broken_wiki_refs=resolve_existing_wiki_refs(root, refs),
                )
            )

    for path in sorted(
        [*root.rglob("*.js"), *root.rglob("*.jsx"), *root.rglob("*.ts"), *root.rglob("*.tsx")]
    ):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"/\*\*([\s\S]*?)\*/", text):
            line = text.count("\n", 0, match.start()) + 1
            block = match.group(0)
            refs = extract_wiki_refs(block)
            records.append(
                DocstringRecord(
                    file=relpath(path, root),
                    line=line,
                    kind="jsdoc",
                    linked=bool(refs),
                    wiki_refs=refs,
                    broken_wiki_refs=resolve_existing_wiki_refs(root, refs),
                )
            )

    for path in sorted(root.rglob("*.rs")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        block: list[tuple[int, str]] = []
        for number, line in [*enumerate(lines, start=1), (len(lines) + 1, "")]:
            if line.lstrip().startswith(("///", "//!")):
                block.append((number, line))
                continue
            if not block:
                continue
            text = "\n".join(item for _line_number, item in block)
            refs = extract_wiki_refs(text)
            records.append(
                DocstringRecord(
                    file=relpath(path, root),
                    line=block[0][0],
                    kind="rustdoc",
                    linked=bool(refs),
                    wiki_refs=refs,
                    broken_wiki_refs=resolve_existing_wiki_refs(root, refs),
                )
            )
            block = []

    return records


def collect_manifest_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and key in {
                "asset",
                "file",
                "filename",
                "path",
                "raw_path",
            }:
                paths.add(child)
                if not child.startswith("raw/"):
                    paths.add(f"raw/assets/{child}")
            else:
                paths.update(collect_manifest_paths(child))
    elif isinstance(value, list):
        for child in value:
            paths.update(collect_manifest_paths(child))
    elif isinstance(value, str) and value.startswith("raw/"):
        paths.add(value)
    return paths


def load_manifest(root: Path) -> tuple[set[str], list[str]]:
    manifest = root / "raw" / "assets" / "manifest.json"
    if not manifest.is_file():
        return set(), ["raw/assets/manifest.json is missing"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return set(), [f"raw/assets/manifest.json is invalid JSON: {exc}"]
    paths = collect_manifest_paths(data)
    if not paths:
        return set(), ["raw/assets/manifest.json contains no raw asset paths"]
    return paths, []


def scan_wiki(root: Path, manifest_paths: set[str]) -> list[WikiRecord]:
    records: list[WikiRecord] = []
    wiki_root = root / "wiki"
    if not wiki_root.is_dir():
        return records

    for path in sorted(wiki_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        refs = extract_raw_refs(text)
        missing_refs = [ref for ref in refs if not (root / ref).is_file()]
        not_manifested = [
            ref for ref in refs if manifest_paths and ref not in manifest_paths and ref[11:] not in manifest_paths
        ]
        records.append(
            WikiRecord(
                file=relpath(path, root),
                raw_refs=refs,
                missing_raw_refs=missing_refs,
                refs_missing_from_manifest=not_manifested,
            )
        )
    return records


def choose_default_wiki(root: Path) -> str:
    candidates = [
        "wiki/synthesis/openqc-agent-context.md",
        "wiki/concepts/diagnostic-engine-v1.md",
        "wiki/concepts/diagnostic-engine.md",
    ]
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    wiki_pages = sorted((root / "wiki").rglob("*.md")) if (root / "wiki").is_dir() else []
    if not wiki_pages:
        raise SystemExit("No wiki page found; cannot choose a default docstring source")
    return relpath(wiki_pages[0], root)


def choose_default_raw(root: Path) -> str:
    candidates = [
        "raw/assets/source-provenance.json",
        "raw/assets/upstream-sources.md",
        "raw/assets/README.md",
        "raw/assets/DIAGNOSTIC_ENGINE_V1.md",
    ]
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    raw_assets = sorted(
        path
        for path in (root / "raw" / "assets").rglob("*")
        if path.is_file() and path.name != "manifest.json"
    )
    if not raw_assets:
        raise SystemExit("No raw asset found; cannot choose a default wiki source")
    return relpath(raw_assets[0], root)


def line_offsets(text: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\n", text):
        offsets.append(match.end())
    return offsets


def add_link_to_python_literal(segment: str, wiki_ref: str) -> str:
    leading = segment[: len(segment) - len(segment.lstrip())]
    body = segment[len(leading) :]
    delimiter = '"""' if '"""' in body[:8] else "'''" if "'''" in body[:8] else ""
    if delimiter:
        close = body.rfind(delimiter)
        if close <= 0:
            return segment
        insertion = f"\n\n{leading}LLM Wiki: {wiki_ref}\n{leading}"
        return leading + body[:close].rstrip() + insertion + body[close:]

    try:
        value = ast.literal_eval(body)
    except (SyntaxError, ValueError):
        return segment
    return f'{leading}"""{value.rstrip()}\n\n{leading}LLM Wiki: {wiki_ref}\n{leading}"""'


def fix_python_docstrings(root: Path, wiki_ref: str) -> int:
    changed = 0
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        offsets = line_offsets(text)
        replacements: list[tuple[int, int, str]] = []
        for line, col, end_line, end_col, docstring in iter_python_docstrings(path):
            if extract_wiki_refs(docstring):
                continue
            start = offsets[line - 1] + col
            end = offsets[end_line - 1] + end_col
            replacements.append((start, end, add_link_to_python_literal(text[start:end], wiki_ref)))
        if not replacements:
            continue
        for start, end, replacement in sorted(replacements, reverse=True):
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8")
        changed += len(replacements)
    return changed


def fix_jsdoc_blocks(root: Path, wiki_ref: str) -> int:
    changed = 0
    for path in sorted(
        [*root.rglob("*.js"), *root.rglob("*.jsx"), *root.rglob("*.ts"), *root.rglob("*.tsx")]
    ):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            block = match.group(0)
            if extract_wiki_refs(block):
                return block
            indent = re.match(r"[ \t]*", text[text.rfind("\n", 0, match.start()) + 1 : match.start()])
            prefix = indent.group(0) if indent else ""
            changed += 1
            return block[:-2].rstrip() + f"\n{prefix} *\n{prefix} * LLM Wiki: {wiki_ref}\n{prefix} */"

        updated = re.sub(r"/\*\*([\s\S]*?)\*/", replace, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    return changed


def fix_rust_doc_comments(root: Path, wiki_ref: str) -> int:
    changed = 0
    for path in sorted(root.rglob("*.rs")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        output: list[str] = []
        block: list[str] = []
        file_changed = 0
        for line in [*lines, ""]:
            stripped = line.lstrip()
            if stripped.startswith(("///", "//!")):
                block.append(line)
                continue
            if block:
                if not any(extract_wiki_refs(item) for item in block):
                    marker = "//!" if block[-1].lstrip().startswith("//!") else "///"
                    indent = re.match(r"[ \t]*", block[-1]).group(0)  # type: ignore[union-attr]
                    newline = "\n" if block[-1].endswith("\n") else ""
                    block.append(f"{indent}{marker} LLM Wiki: {wiki_ref}{newline}")
                    file_changed += 1
                output.extend(block)
                block = []
            if line:
                output.append(line)
        if file_changed:
            path.write_text("".join(output), encoding="utf-8")
            changed += file_changed
    return changed


def fix_wiki_raw_links(root: Path, raw_ref: str) -> int:
    changed = 0
    wiki_root = root / "wiki"
    if not wiki_root.is_dir():
        return changed
    for path in sorted(wiki_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if extract_raw_refs(text):
            continue
        suffix = "\n" if text.endswith("\n") else "\n\n"
        text = (
            text
            + suffix
            + "## Traceability Sources\n\n"
            + f"- Raw evidence: `{raw_ref}`\n"
        )
        path.write_text(text, encoding="utf-8")
        changed += 1
    return changed


def write_manifest(root: Path) -> None:
    assets_root = root / "raw" / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in sorted(assets_root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(assets_root).as_posix(),
                "raw_path": relpath(path, root),
                "bytes": len(data),
                "checksum_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "manifest_version": "1.0.0",
        "schema_version": "provenance-manifest-v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": root.name,
        "pipeline": "official-docs -> raw/assets -> wiki -> docstrings -> LSP runtime",
        "entries": entries,
    }
    (assets_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_report(root: Path) -> dict[str, Any]:
    manifest_paths, manifest_errors = load_manifest(root)
    docstrings = scan_docstrings(root)
    wiki_pages = scan_wiki(root, manifest_paths)
    broken_wiki = sum(len(item.broken_wiki_refs) for item in docstrings)
    wiki_source_failures = sum(
        1
        for item in wiki_pages
        if not item.raw_refs or item.missing_raw_refs or item.refs_missing_from_manifest
    )
    summary = {
        "docstringsTotal": len(docstrings),
        "docstringsLinked": sum(1 for item in docstrings if item.linked),
        "brokenWikiLinks": broken_wiki,
        "wikiPagesTotal": len(wiki_pages),
        "wikiPagesWithRaw": sum(1 for item in wiki_pages if item.raw_refs),
        "wikiSourcesWithoutRaw": wiki_source_failures,
        "rawManifestFailures": len(manifest_errors),
    }
    return {
        "schemaVersion": "docstring-wiki-raw-traceability-v1",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": root.name,
        "summary": summary,
        "manifestErrors": manifest_errors,
        "docstringViolations": [asdict(item) for item in docstrings if not item.linked or item.broken_wiki_refs],
        "wikiViolations": [
            asdict(item)
            for item in wiki_pages
            if not item.raw_refs or item.missing_raw_refs or item.refs_missing_from_manifest
        ],
    }


def report_has_failures(report: dict[str, Any]) -> bool:
    summary = report["summary"]
    return any(
        [
            summary["docstringsTotal"] != summary["docstringsLinked"],
            summary["brokenWikiLinks"],
            summary["wikiSourcesWithoutRaw"],
            summary["rawManifestFailures"],
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--report", type=Path, default=Path("reports/docstring-wiki-raw-traceability.json"))
    parser.add_argument("--write-report", action="store_true", help="Write the JSON report")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when traceability is incomplete")
    parser.add_argument("--fix", action="store_true", help="Add missing docstring and wiki source links")
    parser.add_argument("--refresh-manifest", action="store_true", help="Regenerate raw/assets/manifest.json")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.fix:
        wiki_ref = choose_default_wiki(root)
        raw_ref = choose_default_raw(root)
        changed = {
            "python_docstrings": fix_python_docstrings(root, wiki_ref),
            "jsdoc_blocks": fix_jsdoc_blocks(root, wiki_ref),
            "rustdoc_blocks": fix_rust_doc_comments(root, wiki_ref),
            "wiki_pages": fix_wiki_raw_links(root, raw_ref),
        }
        print(json.dumps({"fixed": changed, "wiki_ref": wiki_ref, "raw_ref": raw_ref}, indent=2))

    if args.refresh_manifest or args.fix:
        write_manifest(root)

    report = build_report(root)
    if args.write_report:
        report_path = args.report if args.report.is_absolute() else root / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if args.strict and report_has_failures(report):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
