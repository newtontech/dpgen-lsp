"""LSP document symbol handler."""

from typing import Any

from lsprotocol.types import DocumentSymbol, Position, Range, SymbolKind

from .json_utils import get_document_text, iter_json_key_occurrences


def document_symbol(ls: Any, params: Any) -> list | None:
    text = get_document_text(ls, params.text_document.uri)
    if not text:
        return None

    symbols: list[DocumentSymbol] = []
    for occ in iter_json_key_occurrences(text):
        rng = Range(
            start=Position(line=occ.line, character=occ.character),
            end=Position(line=occ.line, character=occ.end_character),
        )
        symbols.append(DocumentSymbol(
            name=occ.key,
            detail=occ.path,
            kind=SymbolKind.Property,
            range=rng,
            selection_range=rng,
        ))

    return symbols or None