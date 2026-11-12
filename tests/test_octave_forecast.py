import json
from datetime import datetime

import ki_solar
import octave_forecast as F

IDX = ki_solar.period_index(ki_solar.dt_to_jd(datetime(2026, 11, 9, 12)), "month")
NATAL = "1986-05-01"

MOTION_LEGEND = {0: "Still", 1: "Stirring", 2: "Moving", 3: "Turning", 4: "Breaking"}
WEIGHT_LEGEND = {0: "Background", 1: "Supporting", 2: "Central"}

READ_ANSWERS = {
    "lead": {"type": "choice", "choice": "ji", "confidence": 0.9},
    "stance": {"type": "choice", "choice": "keep", "confidence": 0.9},
    "motion": {"type": "score", "score": 2.0, "legend": MOTION_LEGEND},
    "warning": {"type": "noul", "noul": 0.1},
    **{f"w_{k}": {"type": "score", "score": 1.0, "legend": WEIGHT_LEGEND} for k in F.SOURCE_KEYS},
}
_LEVEL3 = {0: "Whisper", 1: "Present", 2: "Turn"}
ST_ANSWERS_TELL = {
    "stance": {"type": "choice", "choice": "keep", "confidence": 0.9},
    "condition": {"type": "score", "score": 1.0, "legend": _LEVEL3},
    "flow": {"type": "score", "score": 1.0, "legend": _LEVEL3},
    "form": {"type": "choice", "choice": "tell", "confidence": 0.9},
    "tending": {"type": "choice", "choice": "none", "confidence": 0.9},
}
ST_ANSWERS_ASK = {**ST_ANSWERS_TELL, "form": {"type": "choice", "choice": "ask", "confidence": 0.9}}
GOOD_ST = {"adds": 1.8, "method": 0.1, "whole": 0.9}
GOOD_EX = {"explains": 1.8, "method": 0.1}
EXPLAIN_JSON = json.dumps({
    "parts": [{"quote": "A thought.", "meaning": "It is one."}, {"quote": "It tells.", "meaning": "It says."}],
    "whole": "The whole.", "questions": ["What do I hold?", "What do I tell?", "What stays?"], "close": "Hold it lightly.",
})


def fake_writer(*texts):
    """An injectable `post`: the next canned text each call (the last one repeats); records system and prompt."""
    calls = []

    def post(url, body, headers):
        msgs = json.loads(body)["messages"]
        calls.append({"system": msgs[0]["content"], "prompt": msgs[1]["content"]})
        text = texts[min(len(calls), len(texts)) - 1]
        return 200, {"choices": [{"message": {"content": text}}]}

    post.calls = calls
    return post


def _answer(q, v):
    """A real Jev answer of the question's type, from a plain value (dicts pass through)."""
    if isinstance(v, dict):
        return v
    if q["type"] == "score":
        return {"type": "score", "score": v, "legend": dict(enumerate(q["criteria"])), "confidence": 0.9}
    if q["type"] == "noul":
        return {"type": "noul", "noul": v}
    return {"type": "choice", "choice": v, "confidence": 0.9}


def fake_jev(read, grades):
    """The read answers on the first call, then each grade in turn."""
    seq = [read, *grades]
    calls = []

    def jev(state, questions):
        a = seq[min(len(calls), len(seq) - 1)]
        calls.append({"state": state, "questions": questions})
        return {"ok": True, "answers": {k: _answer(questions[k], a[k]) for k in questions if k in a}}

    jev.calls = calls
    return jev


def test_forecast_without_writer_key_is_503(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    r = F.forecast("month", IDX, NATAL, data_dir=tmp_path)
    assert (r["ok"], r["status"], r["error"]) == (False, 503, "no_key")


def test_forecast_unbriefed_without_jev_and_cached(tmp_path):
    post = fake_writer("A paragraph of seventy words ...")
    jev = lambda state, qs: {"ok": False, "error": "no_key"}
    r = F.forecast("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert r["ok"] and r["jev"] is None and r["jevNote"] == "no_key" and r["grade"] is None and r["cached"] is False
    assert "Jev is not available" in post.calls[0]["system"]
    r2 = F.forecast("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert r2["cached"] is True and len(post.calls) == 1


def test_forecast_failing_grade_is_rewritten_once_and_better_kept(tmp_path):
    post = fake_writer("first draft", "second draft")
    jev = fake_jev(read=READ_ANSWERS, grades=[{"synthesis": 0.5, "usable": 0.9, "method": 0.1}, {"synthesis": 1.6, "usable": 0.9, "method": 0.1}])
    r = F.forecast("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert r["text"] == "second draft" and r["rewritten"] is True and r["grade"]["pass"] is True
    assert "recites the parts" in post.calls[1]["prompt"]


def test_forecast_read_shapes_the_system_prompt(tmp_path):
    post = fake_writer("a paragraph")
    jev = fake_jev(read=READ_ANSWERS, grades=[{"synthesis": 1.8, "usable": 0.9, "method": 0.1}])
    r = F.forecast("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert r["jev"]["lead"] == "ji" and r["jev"]["motion"] == "Moving" and r["jev"]["weights"]["ba"]["word"] == "supporting"
    system = post.calls[0]["system"]
    assert "- Lead with what the person meets in this period." in system and "- Motion: moving." in system
    assert "Jev is not available" not in system and len(post.calls) == 1 and r["rewritten"] is False
    assert set(jev.calls[0]["questions"]) == {"lead", "stance", "motion", "warning", *[f"w_{k}" for k in F.SOURCE_KEYS]}


def test_statement_shape_is_counted_not_asked(tmp_path):
    post = fake_writer("One. Two. Three. Four.")
    jev = fake_jev(read=ST_ANSWERS_TELL, grades=[{"adds": 1.8, "method": 0.1, "whole": 0.9}, {"adds": 1.8, "method": 0.1, "whole": 0.9}])
    r = F.statement("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert r["grade"]["sentences"] == 4 and r["grade"]["pass"] is False and r["text"] is None and r["draft"]
    assert r["composed"].endswith("?") or r["composed"].endswith(".")


def test_statement_wrong_ending_is_rewritten_but_does_not_fail(tmp_path):
    post = fake_writer("A thought. It tells.", "A thought. Does it ask?")
    jev = fake_jev(read=ST_ANSWERS_ASK, grades=[GOOD_ST, GOOD_ST])
    r = F.statement("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert r["text"] == "A thought. Does it ask?" and r["rewritten"] is True
    assert "it should end in a question the person carries, not a statement" in post.calls[1]["prompt"]


def test_shape_of_counts_sentences_words_and_ending():
    assert F.shape_of("One. Two? Three!", "tell") == {"sentences": 3, "words": 3, "form": True}
    assert F.shape_of("no stop at all", "ask") == {"sentences": 1, "words": 4, "form": False}
    assert F.shape_of("Does it ask?", "ask")["form"] is True


def test_tidy_turns_dashes_into_commas():
    assert F.tidy('"Earth — on earth.\nStill."') == "Earth, on earth. Still."


def test_parse_explain_strips_fences_and_requires_shape():
    raw = '```json\n{"parts":[{"quote":"a","meaning":"b"},{"quote":"c","meaning":"d — e"}],"whole":"w","questions":["q1","q2","q3"],"close":"c"}\n```'
    x = F.parse_explain(raw)
    assert x["parts"][1]["meaning"] == "d, e" and len(x["questions"]) == 3
    assert F.parse_explain('{"parts":[{"quote":"a","meaning":"b"}],"whole":"w","questions":["q"],"close":"c"}') is None


def test_explain_without_statement_is_404(tmp_path):
    post = fake_writer("One. Two. Three. Four.")          # a statement that fails its shape
    jev = fake_jev(read=ST_ANSWERS_TELL, grades=[GOOD_ST, GOOD_ST])
    r = F.explain("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert (r["ok"], r["status"], r["error"]) == (False, 404, "no_statement")


def test_explain_wrong_shape_twice_is_502(tmp_path):
    post = fake_writer("A thought. It tells.", "not json", "still not json")
    jev = fake_jev(read=ST_ANSWERS_TELL, grades=[GOOD_ST])
    r = F.explain("month", IDX, NATAL, data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    assert (r["ok"], r["status"], r["error"], r["raw"]) == (False, 502, "shape", "still not json")
    assert "it was not the JSON shape asked for; answer with that JSON only" in post.calls[2]["prompt"]


def test_explain_keyed_to_the_thought(tmp_path):
    post = fake_writer("A thought. It tells.", EXPLAIN_JSON)
    jev = fake_jev(read=ST_ANSWERS_TELL, grades=[GOOD_ST, GOOD_EX])
    kw = dict(data_dir=tmp_path, post=post, jev=jev, key="k", model="m", url="u")
    r = F.explain("month", IDX, NATAL, **kw)
    assert r["ok"] and r["cached"] is False and r["of"] == "A thought. It tells."
    assert len(r["parts"]) == 2 and len(r["questions"]) == 3 and r["grade"]["pass"] is True and r["rewritten"] is False
    assert post.calls[1]["system"] == F.EX_SYSTEM and "The passage:\nA thought. It tells." in post.calls[1]["prompt"]
    r2 = F.explain("month", IDX, NATAL, **kw)
    assert r2["cached"] is True and r2["of"] == "A thought. It tells." and r2["whole"] == r["whole"]
    assert len(post.calls) == 2
    saved = json.loads((tmp_path / "forecasts.json").read_text())
    assert saved[f"x{F.EXPLAIN_VERSION}|m|month|{IDX}|{NATAL}"]["of"] == "A thought. It tells."
