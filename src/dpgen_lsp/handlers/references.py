"""LSP references handler."""

from typing import Any

from lsprotocol.types import Location, Position, Range

from .json_utils import get_document_text, iter_json_key_occurrences, key_at_position


def references(ls: Any, params: Any) -> list | None:
    uri = params.text_document.uri
    text = get_document_text(ls, uri)
    if not text:
        return None

    current = key_at_position(text, params.position.line, params.position.character)
    if current is None:
        return None

    locations: list[Location] = []
    for occ in iter_json_key_occurrences(text):
        if occ.key != current.key:
            continue
        locations.append(Location(
            uri=uri,
            range=Range(
                start=Position(line=occ.line, character=occ.character),
                end=Position(line=occ.line, character=occ.end_character),
            ),
        ))

    return locations or None