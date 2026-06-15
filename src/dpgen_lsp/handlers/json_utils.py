"""JSON document utilities used by LSP handlers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JsonKeyOccurrence:
    """Location of a JSON object key in source text."""

    key: str
    line: int
    character: int
    end_character: int
    indent: int
    path: str


_KEY_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s*:')


def get_document_text(ls: Any, uri: str) -> str:
    """Return cached document text for a URI from the language server."""
    docs = getattr(ls, "documents", {})
    return docs.get(uri, "")


def iter_json_key_occurrences(text: str) -> list[JsonKeyOccurrence]:
    """Find JSON object-key occurrences and infer simple dotted paths.

    The inference is indentation-based, which is sufficient for DP-GEN JSON
    config files and avoids mutating or reparsing partially invalid documents.
    """
    occurrences: list[JsonKeyOccurrence] = []
    stack: list[tuple[int, str]] = []

    for line_no, raw in enumerate(text.splitlines()):
        match = _KEY_RE.search(raw)
        if match is None:
            continue

        key = match.group(1)
        indent = len(raw) - len(raw.lstrip())

        while stack and stack[-1][0] >= indent:
            stack.pop()

        path = ".".join([part for _, part in stack] + [key])
        occurrences.append(
            JsonKeyOccurrence(
                key=key,
                line=line_no,
                character=match.start(1),
                end_character=match.end(1),
                indent=indent,
                path=path,
            )
        )

        stripped = raw[match.end():].lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            stack.append((indent, key))

    return occurrences


def key_at_position(text: str, line: int, character: int) -> JsonKeyOccurrence | None:
    """Return the JSON key occurrence under a cursor position, if any."""
    for occ in iter_json_key_occurrences(text):
        if occ.line != line:
            continue
        if occ.character <= character <= occ.end_character:
            return occ
    return None
