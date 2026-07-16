from __future__ import annotations

import pytest

from dpgen_lsp import server


def test_server_help_exits_without_starting_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    started = False

    def start_io() -> None:
        nonlocal started
        started = True

    monkeypatch.setattr(server.server, "start_io", start_io)
    with pytest.raises(SystemExit) as exc_info:
        server.main(["--help"])

    assert exc_info.value.code == 0
    assert started is False
