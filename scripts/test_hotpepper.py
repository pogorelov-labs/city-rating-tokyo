import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("hotpepper", Path(__file__).parent / "scrapers/scrape-hotpepper.py")
hp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hp)


class Response:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


@pytest.mark.parametrize("body", [{"results": {"error": [{"code": 2000}]}},
                                   {"results": {}}, {}, {"results": {"results_available": -1}}])
def test_errors_never_become_zero(body, monkeypatch):
    monkeypatch.setattr(hp.time, "sleep", lambda _: None)
    assert hp.query_hotpepper(1, 2, get=lambda *a, **kw: Response(body)) is None


def test_real_zero_and_midnight_parameter():
    def get(url, **kwargs):
        assert kwargs["params"]["midnight"] == 1
        assert kwargs["params"]["range"] == 3  # Preserve production 1km semantics.
        return Response({"results": {"results_available": "0"}})
    assert hp.query_hotpepper(1, 2, midnight=True, get=get) == 0


def test_request_exception_never_prints_key(monkeypatch, capsys):
    monkeypatch.setattr(hp.time, "sleep", lambda _: None)
    def get(*args, **kwargs):
        raise ValueError("https://example.test/?key=synthetic-sensitive-token")
    assert hp.query_hotpepper(1, 2, get=get) is None
    assert "synthetic-sensitive-token" not in capsys.readouterr().out


def test_all_five_categories_required(monkeypatch):
    calls = []
    def query(*args, **kwargs):
        calls.append(kwargs)
        return None if kwargs.get("midnight") else 3
    monkeypatch.setattr(hp, "query_hotpepper", query)
    limiter = type("Limiter", (), {"wait": lambda self: None})()
    assert hp.query_all_categories(1, 2, limiter) is None
    assert len(calls) == 5
    monkeypatch.setattr(hp, "query_hotpepper", lambda *args, **kwargs: 0)
    assert hp.query_all_categories(1, 2, limiter)["midnight_count"] == 0
