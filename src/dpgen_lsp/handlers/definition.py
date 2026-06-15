"""LSP go-to-definition handler."""

from typing import Any

from lsprotocol.types import Location, Position, Range

from .json_utils import get_document_text, key_at_position


def definition(ls: Any, params: Any) -> list | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    occ = key_at_position(text, params.position.line, params.position.character)
    if occ is None:
        return None

    # For JSON configuration keys, the key occurrence itself is the local
    # definition.  This still enables LSP clients to reveal and select it.
    return [Location(
        uri=uri,
        range=Range(
            start=Position(line=occ.line, character=occ.character),
            end=Position(line=occ.line, character=occ.end_character),
        ),
    )]