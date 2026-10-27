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


def test_auth_middleware_rejects_unconfigured_store():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def protected(_request):
        return PlainTextResponse('allowed')

    app = Starlette(routes=[Route('/protected', protected)])
    app.add_middleware(server._auth_middleware_factory(
        server.KeyStore(nocodb_url='', nocodb_token='', table_id='')
    ))
    with TestClient(app) as client:
        response = client.get('/protected', headers={'Authorization': 'Bearer arbitrary'})
        assert response.status_code == 503
        assert response.json()['error'] == 'unavailable'
        assert client.get('/healthz').status_code == 200
