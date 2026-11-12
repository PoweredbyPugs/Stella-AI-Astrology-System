"""Octave's three model pipelines: the forecast, the statement and the explain.

Each has the same shape: the packet (octave_packet, deterministic); Jev, the decision model, reads it and
decides what matters (typed questions); the writer phrases under a prompt composed from that reading; Jev
grades the draft and a failing one is written once more, the better of the two kept; the result is cached in
DATA_DIR/forecasts.json keyed by version, writer model and period.

- forecast: one paragraph of synthesis for a period (PROMPT_VERSION 4, key ``v4|model|level|idx|natal``).
- statement: the thought under the headline, two or three sentences (STATEMENT_VERSION 2, key ``s2|…``);
  ``text`` is None when no thought passed and the composed sentence stays.
- explain: the reading of the written thought, as structured data (EXPLAIN_VERSION 1, key ``x1|…``), keyed
  to the thought's text.

A port of the page's lib/forecast.js (committed snapshot of 10-11 Nov 2026); every prompt is the page's word for word.
"""
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import octave_ledger
import octave_models as M
from octave_packet import packet

PROMPT_VERSION = 4      # bump when the prompts change, so cached paragraphs are written again
STATEMENT_VERSION = 2
EXPLAIN_VERSION = 1


# ---------------------------------------------------------------- small helpers (the page's)

def first(s):
    """The first sentence: up to the first full stop followed by whitespace."""
    return re.split(r"(?<=\.)\s", str(s or ""))[0]


def clip(s, n):
    return (s[:n] + " …" if len(s) > n else s) if s else None


def AN(w):
    return ("an " if re.match(r"[aeiou]", w, re.I) else "a ") + w


def _round(x):
    """JavaScript's Math.round (halves go up)."""
    return math.floor(x + 0.5)


def _or(v, d):
    """JavaScript's ``??``."""
    return d if v is None else v


def _lt(v, x):
    return v is not None and v < x


def _gt(v, x):
    return v is not None and v > x


def _day(s):
    return s[:10] if s else "open"


def _get(a, k, field):
    """``a.k && a.k.field`` on Jev's answers."""
    v = a.get(k)
    return v.get(field) if isinstance(v, dict) else None


def _stances():
    T = octave_ledger.load()
    return {verb: f"{T['PAIRS'][key]['title']} · {first(T['PAIRS'][key]['lines'])} {first(T['PAIRS'][key]['practice'])}"
            for key, verb in T["VERB"].items()}


def _verb_key(stance):
    VERB = octave_ledger.load()["VERB"]
    return next((k for k in VERB if VERB[k] == stance), None)


# ---------------------------------------------------------------- Jev's reading of the packet, before the writer

SOURCE_KEYS = ["ba", "ji", "shi", "native", "point", "ground"]
WEIGHT = ["Background: leave it out or give it one clause", "Supporting: one sentence, under the lead",
          "Central: the paragraph turns on it"]
FRAME = {"hour": "the next few hours", "day": "today", "month": "this month", "year": "this year",
         "great_year": "these twelve years", "ki_age": "this age of a hundred and forty-four years",
         "great_age": "this great age"}


def read_questions(pk):
    q = {
        "lead": M.choice(f"What should the forecast for {FRAME[pk['level']]} lead with, for this person?", {
            "ji": "what the person meets in this period: the line where their native figure differs from the period's",
            "shi": "what is moving: the line that changes into the next period",
        }),
        "stance": M.choice("Which of the six lines names what this period asks of the person? Its practice closes the forecast.", _stances()),
        "motion": M.score("How much is moving in this period?", ["Still", "Stirring", "Moving", "Turning", "Breaking"]),
        "warning": M.noul("This period carries a warning the person should hear before anything else"),
    }
    for k in SOURCE_KEYS:
        if pk["sources"][k]:
            q[f"w_{k}"] = M.score(f"How much does {pk['sources'][k]['label']} matter to the forecast for {FRAME[pk['level']]}?", WEIGHT)
    return q


def read_state(pk):
    ba, nat, shi = pk["ba"], pk["native"], pk["shi"]
    lines = [
        f"Period: {pk['level']} {_day(pk['span']['start'])} to {_day(pk['span']['end'])}, point {pk['number']} {pk['point']['name']}: \"{pk['point']['question']}\"",
        (f"The period's figure (ba): {ba['n']} {ba['name']}{' (' + ba['gnostic'] + ')' if ba.get('gnostic') else ''}."
         if ba else "The period has no figure of its own."),
        (f"The person's native figure: {nat['n']} {nat['name']}. The ji (where native and period differ): "
         f"{'line ' + ', '.join(map(str, pk['ji'])) if pk['ji'] else 'none'}." if nat else ""),
        f"The shi (what changes into the next period, {str(shi['ba']['n']) + ' ' + shi['ba']['name'] if shi['ba'] else 'no figure'}): "
        f"{'line ' + ', '.join(map(str, shi['lines'])) if shi['lines'] else 'none'}.",
        *[f"\n[{k}] {pk['sources'][k]['label']}:\n{clip(pk['sources'][k]['short'], 1100) or ''}"
          for k in SOURCE_KEYS if pk["sources"][k]],
    ]
    return "\n".join(x for x in lines if x)


WEIGHT_WORD = ["background", "supporting", "central"]


def read_of(a):
    if not a:
        return None
    weights = {}
    for k in SOURCE_KEYS:
        w = a.get(f"w_{k}")
        if w:
            weights[k] = {"score": w["score"], "word": WEIGHT_WORD[min(2, max(0, _round(w["score"])))]}
    return {"lead": _get(a, "lead", "choice"), "leadConfidence": _get(a, "lead", "confidence"),
            "stance": _get(a, "stance", "choice"), "motion": M.level_word(a.get("motion")),
            "motionScore": _get(a, "motion", "score"), "warning": _get(a, "warning", "noul"), "weights": weights}


# ---------------------------------------------------------------- Jev's grade of the draft, after the writer

GRADE_Q = {
    "synthesis": M.score("Does the paragraph add the parts up into one new thing, or recite them?",
                         ["Recites the parts one by one", "Mixed", "Says one new thing the parts add up to"]),
    "usable": M.noul("The person could act on this paragraph today"),
    "method": M.noul("The paragraph talks about the method instead of the person: ba, ji, shi, trigrams, hexagram or line numbers, the Lo Shu, the calendar's mechanics"),
}


def grade_of(a):
    if not a:
        return None
    g = {"synthesis": _get(a, "synthesis", "score"), "synthesisWord": M.level_word(a.get("synthesis")),
         "usable": _get(a, "usable", "noul"), "method": _get(a, "method", "noul")}
    g["pass"] = _or(g["synthesis"], 2) >= 1.2 and _or(g["usable"], 1) >= 0.45 and _or(g["method"], 0) <= 0.8
    return g


# ---------------------------------------------------------------- the writer: a system prompt composed from Jev's reading

RULES = """Form: one paragraph, 70 to 110 words, second person, present tense, concrete, plain. Your job is synthesis, not summary: say the one thing the sources add up to for this person, in this period, that none of them says alone. Draw the image from the book's own words at the lines, and make it this period's, not the book's in general.
Never explain the method and never use its words: not ba, ji, shi, packet, trigram, hexagram, figure, line, native, Lo Shu, and no numbers at all. You may name the period's figure by its title once, as a thing in the world, never as a label. No list, no heading, no quotation marks, no hedging, no restating the question, no preamble."""


def compose_system(pk, read):
    T = octave_ledger.load()
    frame = (f"You write the forecast for {FRAME[pk['level']]} for one person, from the Octave Calendar: a period read as an I Ching figure, "
             f"against the person's own figure, with the lines that differ and the lines that move.")
    if not read:
        return f"{frame}\n{RULES}\nJev is not available: choose the lead yourself from the strongest source, keep to one motion, and end on one thing to do."
    vk = _verb_key(read["stance"])
    stance = f"{read['stance']} ({T['PAIRS'][vk]['title']}): {T['PAIRS'][vk]['practice']}" if vk else read["stance"]
    order = sorted((k for k in SOURCE_KEYS if k in read["weights"]), key=lambda k: -read["weights"][k]["score"])
    motion = str(read["motion"] if read["motion"] is not None else "null").lower()
    warning = "- There is a warning. It comes first, in one sentence.\n" if _or(read["warning"], -1) >= 0.6 else ""
    tending = (f"- An earth period: it {pk['tending']['text']} The thing to do at the close is a tending at that scale, not a push.\n"
               if pk["tending"] else "")
    weights = ", ".join(f"{k} ({read['weights'][k]['word']})" for k in order)
    return (f"{frame}\n"
            f"Jev, the decision model, has read this period and set its shape:\n"
            f"- Lead with {'what is moving into the next period' if read['lead'] == 'shi' else 'what the person meets in this period'}.\n"
            f"- Motion: {motion}. Keep the whole paragraph at that temperature.\n"
            f"- Stance, which closes the paragraph as one concrete thing to do or not do: {stance}\n"
            f"{warning}{tending}- Weight of the sources, most to least: {weights}. A central source is what the paragraph turns on; "
            f"a supporting one gets a sentence under it; a background one at most a clause, or nothing.\n"
            f"{RULES}")


def compose_user(pk, read, feedback):
    def w(k):
        return read["weights"][k]["word"] if read and k in read["weights"] else "supporting"

    parts = []
    for k in SOURCE_KEYS:
        s = pk["sources"][k]
        if not s:
            continue
        wt = w(k)
        body = s["full"] if wt == "central" else clip(s["short"], 900) if wt == "supporting" else clip(first(s["short"]), 240)
        parts.append(f"## {s['label']} ({wt})\n{body}")
    fb = (f"\n\nYour first draft was judged: {feedback}. Write it again: one new thing, none of the method's words, "
          f"something the person can do in this period.") if feedback else ""
    return f"Period: {pk['level']}, {_day(pk['span']['start'])} to {_day(pk['span']['end'])}.\n\n" + "\n\n".join(parts) + fb


# ---------------------------------------------------------------- shared: config, Jev, the writer call, the cache

def _config(key, model, url, data_dir):
    cfg = M.writer_config(key, model, url)
    cfg["data_dir"] = data_dir if data_dir is not None else (os.environ.get("DATA_DIR") or Path(__file__).parent / "data")
    return cfg


def _jev(jev):
    return jev if jev is not None else (lambda state, questions: M.jev_ask(state, questions))


def _writer(cfg, post, timeout):
    def wr(system, prompt, max_tokens=1600):
        return M.write(system, prompt, max_tokens=max_tokens, timeout=timeout if timeout is not None else 60.0,
                       key=cfg["key"], model=cfg["model"], url=cfg["url"], post=post)
    return wr


_NO_KEY = {"ok": False, "status": 503, "error": "no_key", "message": "no OPENROUTER_API_KEY on the server"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _cached(model, entry):
    return {"ok": True, "status": 200, "cached": True, "model": model, **entry}


# ---------------------------------------------------------------- the forecast

def forecast(level, idx, natal, *, fresh=False, data_dir=None, post=None, jev=None, key=None, model=None, url=None,
             timeout=None, keep_prompt=False):
    """The paragraph for one period, cached; ``fresh`` writes it again."""
    cfg = _config(key, model, url, data_dir)
    if not cfg["key"]:
        return dict(_NO_KEY)
    model, ask, write = cfg["model"], _jev(jev), _writer(cfg, post, timeout)
    ck = f"v{PROMPT_VERSION}|{model}|{level}|{idx}|{natal}"
    cache = M.load_cache(cfg["data_dir"])
    if ck in cache and not fresh:
        return _cached(model, cache[ck])
    pk = packet(level, idx, natal)
    # 1. Jev reads the packet and sets the shape
    r1 = ask(read_state(pk), read_questions(pk))
    read = read_of(r1["answers"]) if r1.get("ok") else None
    jev_note = None if r1.get("ok") else r1.get("error")
    # 2. the writer, under a prompt composed from that reading
    system = compose_system(pk, read)
    w = write(system, compose_user(pk, read, None))
    if not w["ok"]:
        return w
    # 3. Jev grades the draft; a failing draft is written once more with the verdict, and the better of the two is kept
    grade, rewritten = None, False
    if r1.get("ok"):
        def grade_state(text):
            return f"The paragraph:\n{text}\n\nThe sources it was written from:\n{read_state(pk)}"
        g1 = ask(grade_state(w["text"]), GRADE_Q)
        grade = grade_of(g1["answers"]) if g1.get("ok") else None
        if grade and not grade["pass"]:
            why = "; ".join(x for x in [
                "it recites the parts instead of adding them up" if _lt(grade["synthesis"], 1.2) else None,
                "nothing in it can be acted on" if _lt(grade["usable"], 0.45) else None,
                "it talks about the method instead of the person" if _gt(grade["method"], 0.8) else None] if x)
            w2 = write(system, compose_user(pk, read, why))
            if w2["ok"]:
                g2 = ask(grade_state(w2["text"]), GRADE_Q)
                grade2 = grade_of(g2["answers"]) if g2.get("ok") else None
                if grade2 and _or(grade2["synthesis"], 0) >= _or(grade["synthesis"], 0):
                    w, grade, rewritten = w2, grade2, True
    entry = {"text": w["text"], "jev": read, "jevNote": jev_note, "grade": grade, "rewritten": rewritten}
    if keep_prompt:
        entry["system"] = system
    entry["at"] = _now()
    cache[ck] = entry
    M.save_cache(cfg["data_dir"], cache)
    return {"ok": True, "status": 200, "cached": False, "model": model, **entry}


# ---------------------------------------------------------------- the statement: the thought under the headline

TEND_WORD = {"all": "tends everything: all of it generated in the dark, in private, not for show",
             "self": "tends the self: unblocking so that what is coming through can land, not pushing outward",
             "one": "tends one thing, with great care"}


def statement_questions(pk):
    q = {
        "stance": M.choice("Which of the six lines names what this period asks of the person?", _stances()),
        "condition": M.score("How much should the thought turn on the condition, the person's element in the period's?",
                             ["Whisper: the condition stays in the background", "Present: one clause", "Turn: the thought turns on it"]),
        "form": M.choice("Should the thought end by asking or by telling?", {
            "ask": "a question the person carries through the period: the period is receiving and the answer is not yet theirs",
            "tell": "a statement: the period is acting, and the thought says what it is for"}),
    }
    if pk["flow"]:
        q["flow"] = M.score("How much should the thought draw on the flow, this period inside the one that holds it?",
                            ["Whisper: the flow stays in the background", "Present: a few words", "Turn: the thought opens on it"])
    if not pk["tending"]:
        q["tending"] = M.choice("Is this period a tending, and at what scale?", {
            "none": "not a tending: the period acts, moves, cuts or sees",
            "all": TEND_WORD["all"], "self": TEND_WORD["self"], "one": TEND_WORD["one"]})
    return q


def st_read_of(a, pk):
    if not a:
        return None
    return {"tending": pk["tending"]["scale"] if pk["tending"] else (_get(a, "tending", "choice") or "none"),
            "stance": _get(a, "stance", "choice"), "condition": M.level_word(a.get("condition")),
            "conditionScore": _get(a, "condition", "score"),
            "flow": M.level_word(a.get("flow")) if pk["flow"] else None, "form": _get(a, "form", "choice")}


ST_RULES = "Form: one thought in two or three sentences, at most fifty words in all, addressed to the person (you, your), present tense, concrete, plain. It is one voice telling one thing: the period inside the one that holds it, what this period is for this person, and how the person stands in it; not three facts in a row. It must say something the point's question alone does not. It ends the way Jev decided: on a question the person carries, or on a statement. One image from the book's line may carry it. Never explain the method and never use its words: not ba, ji, shi, trigram, hexagram, figure, line, native, the Lo Shu, no element names as labels (an element may appear only as a thing: earth, water, fire, as what they are), and no numbers. No quotation marks, no dashes, no preamble, no hedging, no list, nothing but the sentences."


def compose_statement_system(pk, read):
    T = octave_ledger.load()
    frame = (f"You write the thought that heads the reading of {FRAME[pk['level']]} for one person, from the Octave Calendar. "
             f"The point's question is \"{pk['point']['question']}\"; your thought takes its place and keeps its direction.")
    if not read:
        return f"{frame}\n{ST_RULES}\nJev is not available: keep the question's form and add what this period adds."
    vk = _verb_key(read["stance"])
    stance = f"{read['stance']} ({T['PAIRS'][vk]['title']}): {first(T['PAIRS'][vk]['practice'])}" if vk else read["stance"]
    c = pk["condition"]
    cond = f"the person's {c['native'].lower()} in the period's {c['field'].lower()}, {c['word']}" if c else "none"
    f = pk["flow"]
    flow = (f"{f['field'].lower()} {pk['level']} in {AN(f['container'].lower())} {f['containerLevel']}, it "
            f"{'is ' + f['word'] + ' by it' if f['word'] in ('fed', 'controlled') else f['word'] + ' it'}") if f else None
    tending = ("none; the period acts." if read["tending"] == "none"
               else f"{read['tending']}. This period {TEND_WORD.get(read['tending'], '')}.")
    cond_how = ("the thought turns on it." if read["condition"] == "Turn"
                else "background, at most a word." if read["condition"] == "Whisper" else "one clause.")
    if flow:
        flow_how = ("the thought opens on it." if read["flow"] == "Turn"
                    else "background, at most a word." if read["flow"] == "Whisper" else "a few words, where it belongs.")
        flow_line = f"- The flow ({flow}): {flow_how}"
    else:
        flow_line = "- No flow: this is the top level, nothing holds it."
    return (f"{frame}\n"
            f"Jev, the decision model, has read this period and set the thought's shape:\n"
            f"- {'Tell: it ends in a statement.' if read['form'] == 'tell' else 'Ask: it ends in a question the person carries.'}\n"
            f"- Tending: {tending}\n"
            f"- Stance: {stance}\n"
            f"- The condition ({cond}): {cond_how}\n"
            f"{flow_line}\n"
            f"{ST_RULES}")


def compose_statement_user(pk, feedback):
    c, f, src = pk["condition"], pk["flow"], pk["sources"]
    parts = [f"Period: {pk['level']}, {_day(pk['span']['start'])} to {_day(pk['span']['end'])}. Point: {pk['point']['name']}. Question: {pk['point']['question']}",
             f"Condition, {c['word']}: {c['text']}" if c else None,
             f"Flow, this {pk['level']} in its {f['containerLevel']}, {f['word']}: {f['text']}" if f else None,
             f"What the person meets, the book's line:\n{clip(src['ji']['short'], 700)}" if src["ji"] else None,
             f"The point:\n{clip(src['point']['short'], 600)}",
             f"Ground:\n{clip(src['ground']['short'], 500)}" if src["ground"] else None]
    return "\n\n".join(x for x in parts if x) + (f"\n\nYour first thought was judged: {feedback}. Write it again." if feedback else "")


ST_GRADE_Q = {
    "adds": M.score("Does the statement say something the point's question alone does not, for this person in this period?",
                    ["Restates the question", "Adds a little", "Says something new"]),
    "method": M.noul("The statement talks about the method instead of the person: ba, ji, shi, trigrams, hexagram or line numbers, the Lo Shu, the calendar's mechanics, elements as labels"),
    "whole": M.noul("It reads as one thought in one voice addressed to the person, not three facts in a row"),
}


def shape_of(text, form):
    """The shape is counted, not asked: the sentences, the words, and whether it ends the way Jev decided (ask / tell)."""
    t = str(text)
    n = len(re.findall(r"[^.?!]+[.?!]+", t)) or 1
    words = len(t.strip().split()) or 1
    asks = re.search(r"\?\s*$", t) is not None
    return {"sentences": n, "words": words, "form": asks if form == "ask" else not asks}


def st_grade_of(a, shape):
    if not a:
        return None
    g = {"adds": _get(a, "adds", "score"), "method": _get(a, "method", "noul"), "whole": _get(a, "whole", "noul"), **shape}
    g["pass"] = (_or(g["adds"], 2) >= 1.2 and _or(g["method"], 0) <= 0.8 and _or(g["whole"], 1) >= 0.5
                 and g["sentences"] <= 3 and g["words"] <= 60)
    return g


def tidy(text):
    """One block, no dashes, no wrapping quotes."""
    s = str(text or "").strip()
    s = re.sub(r"\s*\n+\s*", " ", s)
    s = re.sub(r"\s*[—–]\s*", ", ", s)
    s = re.sub(r'^["“]+|["”]+$', "", s)
    return s.strip()


def statement(level, idx, natal, *, fresh=False, data_dir=None, post=None, jev=None, key=None, model=None, url=None,
              timeout=None, keep_prompt=False):
    """The written statement for one period, cached; ``text`` is None when no thought passed and the composed one stays."""
    cfg = _config(key, model, url, data_dir)
    if not cfg["key"]:
        return dict(_NO_KEY)
    model, ask, write = cfg["model"], _jev(jev), _writer(cfg, post, timeout)
    ck = f"s{STATEMENT_VERSION}|{model}|{level}|{idx}|{natal}"
    cache = M.load_cache(cfg["data_dir"])
    if ck in cache and not fresh:
        return _cached(model, cache[ck])
    pk = packet(level, idx, natal)
    composed = pk["condition"]["statement"] if pk["condition"] else pk["point"]["question"]
    state = f"{read_state(pk)}\nThe point's question: \"{pk['point']['question']}\"\nThe composed statement: \"{composed}\""
    r1 = ask(state, statement_questions(pk))
    read = st_read_of(r1["answers"], pk) if r1.get("ok") else None
    system = compose_statement_system(pk, read)

    def wr(feedback):
        return write(system, compose_statement_user(pk, feedback), max_tokens=200)

    w = wr(None)
    if not w["ok"]:
        return w
    w = {**w, "text": tidy(w["text"])}
    grade, rewritten = None, False
    if r1.get("ok"):
        def gs(t):
            return f"The statement:\n{t}\n\nThe point's question: \"{pk['point']['question']}\"\n\nThe sources:\n{read_state(pk)}"
        g1 = ask(gs(w["text"]), ST_GRADE_Q)
        grade = st_grade_of(g1["answers"], shape_of(w["text"], read["form"])) if g1.get("ok") else None
        if grade and (not grade["pass"] or not grade["form"]):   # a wrong ending is written again but does not fail the thought
            why = "; ".join(x for x in [
                "it restates the question instead of adding to it" if _lt(grade["adds"], 1.2) else None,
                "it talks about the method instead of the person" if _gt(grade["method"], 0.8) else None,
                "it is not one thought in one voice" if _lt(grade["whole"], 0.5) else None,
                "it runs past three sentences or fifty words" if grade["sentences"] > 3 or grade["words"] > 60 else None,
                None if grade["form"] else ("it should end in a question the person carries, not a statement" if read["form"] == "ask"
                                            else "it should end in a statement, not a question")] if x)
            w2 = wr(why)
            if w2["ok"]:
                w2 = {**w2, "text": tidy(w2["text"])}
                g2 = ask(gs(w2["text"]), ST_GRADE_Q)
                grade2 = st_grade_of(g2["answers"], shape_of(w2["text"], read["form"])) if g2.get("ok") else None

                def rank(g):   # a passing thought first, then one that ends as Jev decided, then the one that adds more
                    return (2 if g["pass"] else 0) + (1 if g["form"] else 0)
                if grade2 and (rank(grade2) > rank(grade) or (rank(grade2) == rank(grade) and _or(grade2["adds"], 0) >= _or(grade["adds"], 0))):
                    w, grade, rewritten = w2, grade2, True
    passed = not grade or grade["pass"]
    entry = {"text": w["text"] if passed else None}
    if not passed:
        entry["draft"] = w["text"]
    entry.update({"composed": composed, "jev": read, "jevNote": None if r1.get("ok") else r1.get("error"),
                  "grade": grade, "rewritten": rewritten})
    if keep_prompt:
        entry["system"] = system
    entry["at"] = _now()
    cache[ck] = entry
    M.save_cache(cfg["data_dir"], cache)
    return {"ok": True, "status": 200, "cached": False, "model": model, **entry}


# ---------------------------------------------------------------- the explain: the reading of the thought

EX_SYSTEM = """You read one short passage back to the person it was written for, the way a close friend would read a poem with them: plainly, warmly, without jargon. The passage is the thought that heads their reading for a period of time in the Octave Calendar; its images come from an old book of changes, but you never say so and never name any source, method, number, figure, line, trigram, hexagram, element or calendar. You read it as words addressed to a person.
Answer with JSON only, no fences, no preamble, in this exact shape:
{"parts":[{"quote":"<a phrase of the passage, copied exactly>","meaning":"<what it is saying to them, two to four sentences>"}],"whole":"<the whole passage in one plain paragraph, three or four sentences>","questions":["<a question to sit with>"],"close":"<one or two sentences: what kind of thing this passage is and how to hold it>"}
Rules: the quotes are the passage itself, copied exactly, in order, two to five of them, covering it; speak to the person as you; where an image is open (a field, a mountain, ore, ash, light), say what it could mean for them in a few concrete alternatives, not one fixed reading; three to five questions, each in the first person, as they would ask it of themselves; no "yes", no "this reads like", no praise of the passage, no hedging about what you are, nothing before or after the JSON."""

_SPAN_WORD = {"hour": "a few hours", "day": "a day", "month": "a month", "year": "a year"}


def ex_user(pk, text, feedback):
    c, ji = pk["condition"], pk["sources"]["ji"]
    return (f"The passage:\n{text}\n\nFor your own understanding only, never to be named: the period is "
            f"{_SPAN_WORD.get(pk['level'], 'a long span')}; the passage grew from the question \"{pk['point']['question']}\""
            f"{', from this: ' + clip(c['text'], 400) if c else ''}"
            f"{', and from this line: ' + clip(ji['short'], 500) if ji else ''}."
            + (f"\n\nYour first reading was judged: {feedback}. Write it again." if feedback else ""))


def parse_explain(raw):
    t = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", str(raw or ""))
    a, z = t.find("{"), t.rfind("}")
    if a < 0 or z <= a:
        return None
    try:
        o = json.loads(t[a:z + 1])
    except Exception:
        return None
    if not isinstance(o, dict):
        return None

    def s(v):   # no dashes, as everywhere on the page
        return re.sub(r"\s*[—–]\s*", ", ", v.strip()) if isinstance(v, str) and v.strip() else None

    parts = [{"quote": s(x.get("quote")), "meaning": s(x.get("meaning"))}
             for x in (o["parts"] if isinstance(o.get("parts"), list) else []) if isinstance(x, dict)]
    parts = [x for x in parts if x["quote"] and x["meaning"]]
    questions = [q for q in map(s, o["questions"] if isinstance(o.get("questions"), list) else []) if q]
    if len(parts) < 2 or not s(o.get("whole")) or len(questions) < 3 or not s(o.get("close")):
        return None
    return {"parts": parts, "whole": s(o["whole"]), "questions": questions, "close": s(o["close"])}


EX_GRADE_Q = {
    "explains": M.score("Does the reading open the passage up for the person, or only restate it in other words?",
                        ["Restates it", "Opens it a little", "Opens it up"]),
    "method": M.noul("The reading names the method behind the passage: a book, a figure, a hexagram or line, a trigram, an element as a label, a number, the calendar's mechanics"),
}


def ex_grade_of(a):
    if not a:
        return None
    g = {"explains": _get(a, "explains", "score"), "method": _get(a, "method", "noul")}
    g["pass"] = _or(g["explains"], 2) >= 1.2 and _or(g["method"], 0) <= 0.8
    return g


def ex_flat(x):
    return "\n\n".join([*(f"\"{p['quote']}\"\n{p['meaning']}" for p in x["parts"]), x["whole"], *x["questions"], x["close"]])


def explain(level, idx, natal, *, fresh=False, data_dir=None, post=None, jev=None, key=None, model=None, url=None,
            timeout=None, keep_prompt=False):
    """The reading of the written thought for one period, cached by the thought's text; 404 ``no_statement`` where none was written."""
    cfg = _config(key, model, url, data_dir)
    if not cfg["key"]:
        return dict(_NO_KEY)
    st = statement(level, idx, natal, fresh=False, data_dir=data_dir, post=post, jev=jev, key=key, model=model, url=url,
                   timeout=timeout, keep_prompt=keep_prompt)
    if not st["ok"]:
        return st
    if not st.get("text"):
        return {"ok": False, "status": 404, "error": "no_statement", "message": "no thought was written for this period"}
    model, ask, write = cfg["model"], _jev(jev), _writer(cfg, post, timeout)
    ck = f"x{EXPLAIN_VERSION}|{model}|{level}|{idx}|{natal}"
    cache = M.load_cache(cfg["data_dir"])
    if ck in cache and cache[ck].get("of") == st["text"] and not fresh:
        return _cached(model, cache[ck])
    pk = packet(level, idx, natal)

    def wr(feedback):
        w = write(EX_SYSTEM, ex_user(pk, st["text"], feedback), max_tokens=1400)
        if not w["ok"]:
            return w
        x = parse_explain(w["text"])
        return ({"ok": True, "text": x} if x else
                {"ok": False, "status": 502, "error": "shape", "message": "the model did not answer in the shape asked for", "raw": w["text"]})

    w = wr(None)
    if not w["ok"] and w.get("error") == "shape":
        w = wr("it was not the JSON shape asked for; answer with that JSON only")
    if not w["ok"]:
        return w

    def gs(x):
        return f"The passage:\n{st['text']}\n\nThe reading:\n{ex_flat(x)}"
    rewritten = False
    g1 = ask(gs(w["text"]), EX_GRADE_Q)
    grade = ex_grade_of(g1["answers"]) if g1.get("ok") else None
    if grade and not grade["pass"]:
        why = "; ".join(x for x in [
            "it restates the passage instead of opening it up" if _lt(grade["explains"], 1.2) else None,
            "it names the method behind the passage instead of reading the words" if _gt(grade["method"], 0.8) else None] if x)
        w2 = wr(why)
        if w2["ok"]:
            g2 = ask(gs(w2["text"]), EX_GRADE_Q)
            grade2 = ex_grade_of(g2["answers"]) if g2.get("ok") else None
            if grade2 and ((grade2["pass"] and not grade["pass"]) or
                           (grade2["pass"] == grade["pass"] and _or(grade2["explains"], 0) >= _or(grade["explains"], 0))):
                w, grade, rewritten = w2, grade2, True
    entry = {"of": st["text"], **w["text"], "grade": grade, "jevNote": None if g1.get("ok") else g1.get("error"),
             "rewritten": rewritten, "at": _now()}
    cache[ck] = entry
    M.save_cache(cfg["data_dir"], cache)
    return {"ok": True, "status": 200, "cached": False, "model": model, **entry}
