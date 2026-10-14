"""Transport guard tests (audit C2): SSE must refuse to run with auth on.

These import the server module, which pulls fastmcp — so they skip when the
runtime deps are not installed (local quick runs) and run in CI's mcp job.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

fastmcp = pytest.importorskip("fastmcp")  # noqa: F841

from city_rating_mcp import server  # noqa: E402


def test_sse_refused_with_auth_required(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    monkeypatch.setenv("MCP_AUTH_REQUIRED", "true")
    with pytest.raises(SystemExit, match="sse is not allowed"):
        server.main()


def test_sse_refused_with_auth_required_explicit(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    monkeypatch.setenv("MCP_AUTH_REQUIRED", "1")
    with pytest.raises(SystemExit):
        server.main()


def test_unknown_transport_still_rejected(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "carrier-pigeon")
    with pytest.raises(SystemExit, match="Unknown MCP_TRANSPORT"):
        server.main()
