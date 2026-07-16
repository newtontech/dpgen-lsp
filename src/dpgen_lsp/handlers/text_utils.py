"""Small text helpers shared by LSP handlers.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import re
from typing import Any, cast

from lsprotocol.types import Position, Range

WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.$%+-]*")
JSON_KEY_RE = re.compile(r'"(?P<name>[A-Za-z_][A-Za-z0-9_.$%+-]*)"\s*:')


def get_document_text(ls: Any, uri: str) -> str:
    docs = getattr(ls, "documents", {})
    return cast(str, docs.get(uri, ""))


def make_range(line: int, start: int, end: int) -> Range:
    return Range(
        start=Position(line=max(line, 0), character=max(start, 0)),
        end=Position(line=max(line, 0), character=max(end, start, 0)),
    )


def empty_range() -> Range:
    return make_range(0, 0, 0)


def word_at(text: str, line: int, character: int) -> tuple[str, Range] | None:
    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    current = lines[line]
    character = min(max(character, 0), len(current))
    for match in WORD_RE.finditer(current):
        if match.start() <= character <= match.end():
            return match.group(0), make_range(line, match.start(), match.end())
    return None


def find_token_ranges(text: str, token: str) -> list[Range]:
    if not token:
        return []
    ranges: list[Range] = []
    pattern = re.compile(rf"\b{re.escape(token)}\b")
    for line_no, line in enumerate(text.splitlines()):
        for match in pattern.finditer(line):
            ranges.append(make_range(line_no, match.start(), match.end()))
    return ranges


def find_json_key_ranges(text: str) -> list[tuple[str, Range]]:
    keys: list[tuple[str, Range]] = []
    for line_no, line in enumerate(text.splitlines()):
        for match in JSON_KEY_RE.finditer(line):
            keys.append(
                (match.group("name"), make_range(line_no, match.start("name"), match.end("name")))
            )
    return keys
