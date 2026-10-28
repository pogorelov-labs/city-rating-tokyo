import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import requests

spec = importlib.util.spec_from_file_location("check_livecams", Path(__file__).with_name("check-livecams.py"))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def snapshot(tmp_path, value):
    path = tmp_path / "cameras.json"
    path.write_text(json.dumps(value))
    return path


def test_deduplicates_and_sorts(tmp_path):
    path = snapshot(tmp_path, {"a": [{"video_id": "abcdefghijk"}], "b": [{"video_id": "abcdefghijk"}, {"video_id": "12345678901"}]})
    assert checker.load_ids(path) == ["12345678901", "abcdefghijk"]


def test_status_errors_and_delay():
    calls, delays = [], []
    def head(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) == 3:
            raise requests.Timeout()
        return SimpleNamespace(status_code=[200, 404][len(calls) - 1])
    missing, unknown = checker.check(["a", "b", "c"], get=head, sleep=delays.append)
    assert missing == ["b"] and unknown == [("c", "Timeout")]
    assert delays == [0.2, 0.2]
    assert all(c[1] == {"timeout": 10, "allow_redirects": False} for c in calls)


def test_other_http_is_unknown():
    assert checker.check(["a"], get=lambda *a, **k: SimpleNamespace(status_code=429))[1] == [("a", "HTTP 429")]


def test_repeated_failures_stop_without_marking_remaining_healthy():
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise requests.Timeout()
    _, unknown = checker.check(["a", "b", "c", "d"], get=fail, sleep=lambda _: None)
    assert len(calls) == 3
    assert unknown[-1] == ("d", "not checked after consecutive errors")


def test_offline_and_invalid_input(tmp_path, capsys):
    path = snapshot(tmp_path, {"a": [{"video_id": "abcdefghijk"}]})
    assert checker.main(["--data", str(path), "--offline"]) == 0
    assert "SKIP" in capsys.readouterr().out
    path = snapshot(tmp_path, {"a": [{"video_id": "bad"}]})
    assert checker.main(["--data", str(path), "--offline"]) == 2


def test_threshold_and_unknown_take_precedence(tmp_path, monkeypatch):
    path = snapshot(tmp_path, {"a": [{"video_id": "abcdefghijk"}]})
    monkeypatch.setattr(checker, "check", lambda ids: ([ids[0]], []))
    assert checker.main(["--data", str(path)]) == 1
    assert checker.main(["--data", str(path), "--threshold", "1"]) == 0
    monkeypatch.setattr(checker, "check", lambda ids: ([], [(ids[0], "Timeout")]))
    assert checker.main(["--data", str(path), "--threshold", "1"]) == 2
