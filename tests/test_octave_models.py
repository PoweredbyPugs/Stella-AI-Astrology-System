import json

import octave_models as M


def test_write_parses_an_openai_reply():
    post = lambda url, body, headers: (200, {"choices": [{"message": {"content": "  One thought.  "}}]})
    r = M.write("sys", "user", key="k", model="m", url="http://x", post=post)
    assert r == {"ok": True, "text": "One thought."}


def test_write_reports_reasoning_without_text():
    post = lambda url, body, headers: (200, {"choices": [{"message": {"content": "", "reasoning": "..."}}]})
    assert M.write("s", "u", key="k", model="m", url="http://x", post=post)["message"] == "the model spent its budget reasoning and sent no text"


def test_write_sends_reasoning_off_and_temperature(monkeypatch):
    seen = {}

    def post(url, body, headers):
        seen.update(json.loads(body))
        seen["_headers"] = headers
        return (200, {"choices": [{"message": {"content": "t"}}]})

    M.write("s", "u", key="k", model="m", url="http://x", post=post)
    assert seen["reasoning"] == {"enabled": False} and seen["temperature"] == 0.7 and seen["max_tokens"] == 1600
    assert seen["_headers"]["Authorization"] == "Bearer k"
    assert seen["_headers"]["HTTP-Referer"] == "http://octave.lan" and seen["_headers"]["X-Title"] == "Stella Octave"
    assert [m["role"] for m in seen["messages"]] == ["system", "user"]


def test_write_non_2xx_and_empty_and_no_key():
    post = lambda url, body, headers: (429, {"error": {"message": "slow down"}})
    r = M.write("s", "u", key="k", model="m", url="http://x", post=post)
    assert r == {"ok": False, "status": 502, "error": "upstream", "message": "429: slow down"}
    post = lambda url, body, headers: (500, {})
    assert M.write("s", "u", key="k", model="m", url="http://x", post=post)["message"] == "500: the model refused the call"
    post = lambda url, body, headers: (200, {"choices": [{"message": {"content": ""}}]})
    assert M.write("s", "u", key="k", model="m", url="http://x", post=post)["message"] == "the model sent no text"
    r = M.write("s", "u", key="", model="m", url="http://x", post=post)
    assert r == {"ok": False, "status": 503, "error": "no_key", "message": "no OPENROUTER_API_KEY on the server"}


def test_writer_config_reads_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "ek")
    monkeypatch.delenv("FORECAST_MODEL", raising=False)
    monkeypatch.delenv("FORECAST_URL", raising=False)
    assert M.writer_config() == {"key": "ek", "model": "deepseek/deepseek-v4.1-flash", "url": "https://openrouter.ai/api/v1/chat/completions"}
    assert M.writer_config(key="a", model="b", url="c") == {"key": "a", "model": "b", "url": "c"}


def test_builders_and_level_word():
    assert M.choice("i", {"a": "b"}) == {"type": "choice", "instructions": "i", "criteria": {"a": "b"}}
    assert M.score("i", ["x", "y"]) == {"type": "score", "instructions": "i", "criteria": ["x", "y"]}
    assert M.noul("i") == {"type": "noul", "instructions": "i"}
    a = {"type": "score", "score": 1.78, "legend": {0: "Still", 1: "Stirring", 2: "Moving"}}
    assert M.level_word(a) == "Moving"
    assert M.level_word({"type": "score", "score": 9, "legend": {"0": "Still", "1": "Stirring"}}) == "Stirring"
    assert M.level_word({"type": "score", "score": -3, "legend": {"0": "Still", "1": "Stirring"}}) == "Still"
    assert M.level_word({"type": "noul", "noul": 0.1}) is None and M.level_word(None) is None


def test_jev_ask_without_key_is_no_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("JEVKIT_PATH", "/nonexistent")
    r = M.jev_ask("state", {"q": M.noul("x")})
    assert r["ok"] is False and r["error"] in ("no_key", "no_jevkit")


def test_cache_round_trip(tmp_path):
    c = M.load_cache(tmp_path)
    c["k"] = {"text": "t"}
    M.save_cache(tmp_path, c)
    assert json.load(open(tmp_path / "forecasts.json")) == {"k": {"text": "t"}}
    assert M.load_cache(str(tmp_path)) is c


def test_level_word_rounds_half_up_like_math_round():
    legend = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e"}
    assert M.level_word({"type": "score", "score": 2.5, "legend": legend}) == "d"
    assert M.level_word({"type": "score", "score": 0.5, "legend": legend}) == "b"


def test_save_cache_is_safe_from_two_threads(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(M.save_cache, tmp_path, {f"k{i}": "x" * 2000, **{f"p{j}": j for j in range(300)}}) for i in range(8)]
        for f in fs:
            f.result()
    assert isinstance(json.loads((tmp_path / "forecasts.json").read_text(encoding="utf-8")), dict)
    assert not (tmp_path / "forecasts.json.tmp").exists()
