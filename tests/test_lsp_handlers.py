"""Tests for standard LSP handler coverage."""

from __future__ import annotations

from types import SimpleNamespace

URI = "file:///workspace/param.json"
TEXT = """{
  "type_map": ["H", "C"],
  "mass_map": [1],
  "dpgen_version": "v0.13.3"
}
"""


def _server(text: str = TEXT):
    return SimpleNamespace(documents={URI: text})


def _params(line: int = 1, character: int = 5):
    return SimpleNamespace(
        text_document=SimpleNamespace(uri=URI),
        position=SimpleNamespace(line=line, character=character),
    )


def test_document_symbol_handler_returns_json_keys():
    from dpgen_lsp.handlers.document_symbol import document_symbol

    symbols = document_symbol(_server(), _params())

    assert symbols
    assert {symbol.name for symbol in symbols} >= {"type_map", "mass_map", "dpgen_version"}


def test_definition_handler_links_known_field_to_manual():
    from dpgen_lsp.handlers.definition import definition

    locations = definition(_server(), _params(line=1, character=5))

    assert locations
    assert locations[0].uri.startswith("https://docs.deepmodeling.com/projects/dpgen/")


def test_references_and_rename_handlers_cover_token_occurrences():
    from dpgen_lsp.handlers.references import references
    from dpgen_lsp.handlers.rename import prepare_rename, rename

    params = _params(line=1, character=5)

    refs = references(_server(), params)
    prepared = prepare_rename(_server(), params)
    edit = rename(
        _server(),
        SimpleNamespace(
            text_document=SimpleNamespace(uri=URI),
            position=SimpleNamespace(line=1, character=5),
            new_name="type_map_renamed",
        ),
    )

    assert refs
    assert prepared is not None
    assert edit is not None
    assert edit.changes[URI][0].new_text == "type_map_renamed"


def test_code_action_handler_returns_diagnostic_fix_hints():
    from dpgen_lsp.handlers.code_action import code_action

    actions = code_action(_server(), _params(line=2, character=5))

    assert actions
    assert actions[0].kind == "quickfix"
    assert actions[0].data["source"] == "dpgen-lsp"


def test_agent_lsp_position_operations_cover_standard_surface():
    from dpgen_lsp.agent_lsp import AgentLSP

    agent = AgentLSP.from_text(TEXT, URI)
    completion_agent = AgentLSP.from_text('{\n  ""\n}', URI)

    symbols = agent.symbols()
    hover = agent.hover(1, 5)
    completions = completion_agent.complete(1, 3)

    assert symbols["items"]
    assert any(item["name"] == "type_map" for item in symbols["items"])
    assert hover["contents"]
    assert "type_map" in hover["contents"]
    assert completions["items"]
