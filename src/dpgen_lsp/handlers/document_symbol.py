"""LSP document symbol handler.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

from typing import Any

from lsprotocol.types import DocumentSymbol, SymbolKind

from .text_utils import find_json_key_ranges, get_document_text


def document_symbol(ls: Any, params: Any) -> list[DocumentSymbol] | None:
    text = get_document_text(ls, params.text_document.uri)
    if not text:
        return None

    symbols = [
        DocumentSymbol(
            name=name,
            kind=SymbolKind.Property,
            range=key_range,
            selection_range=key_range,
        )
        for name, key_range in find_json_key_ranges(text)
    ]
    return symbols or None
