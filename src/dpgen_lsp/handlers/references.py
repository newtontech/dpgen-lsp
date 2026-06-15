"""LSP references handler."""

from __future__ import annotations

from typing import Any

from lsprotocol.types import Location

from .text_utils import find_token_ranges, get_document_text, word_at


def references(ls: Any, params: Any) -> list[Location] | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    selected = word_at(text, params.position.line, params.position.character)
    if selected is None:
        return None
    token, _ = selected
    locations = [
        Location(uri=uri, range=token_range) for token_range in find_token_ranges(text, token)
    ]
    return locations or None
