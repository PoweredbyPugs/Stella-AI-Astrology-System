# Octave System on Stella — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the Octave Calendar's engine, ledger vocabulary, composed reading and the three Jev-plus-writer pipelines into Stella as ten MCP tools and one skill, so Stella answers the same questions as the page (http://192.168.1.181:3333) from the same numbers.

**Architecture:** Stella already has the clock (`ki_solar.py`, `ki_levels.py`), hub inheritance (`hub_inheritance.py`) and the book (`octave.py`). Four new modules sit on top of them, each one responsibility: `octave_engine.py` (a period and its figures, elements, palace), `octave_ledger.py` (the ledger tables as data, dumped once from the page's `ledger.js` + `briefs.js`, plus the three composed-text functions), `octave_packet.py` (the deterministic packet for one period, the page's `packet()` one to one), and `octave_forecast.py` (forecast, statement, explain: Jev decides, writer phrases, Jev grades, one rewrite, cache). Tools register through a new `octave_tools.py` called from `stella_server.py` beside `register_octave`. Nothing in the page changes; its tests stay the cross-check.

**Tech Stack:** Python 3.11+, pyswisseph (already), stdlib `urllib` for the writer, `jevkit` (the checkout at `~/hermes-jev-skills`, on `JEVKIT_PATH`) for Jev, pytest, FastMCP.

**Spec:** Claude Doc "The Octave System — a breakdown for Stella" (https://claude.ai/artifact/QJZHtLnVMwKxfB3M6owWjb), read 2026-11-12; a text export sits at `docs/superpowers/specs/2026-11-12-octave-system.md` (Task 0 saves it). Page source: `/Volumes/Shirahoshi/HermesNode/octave` (branch `feat/palace-field-ji`), `src/engine.js`, `src/ledger.js`, `src/briefs.js`, `lib/forecast.js`, `lib/jev.js`, `CLAUDE.md`.

## Global Constraints

- The numbers come from Stella's own clock: `ki_solar.solar_stack`, `period_index`, `period_start_jd`, `period_stack`, `octave_start_index`; `ki_levels.ki`, `personal`, `global_stack`, `personal_stack`; `hub_inheritance.resolve`, `king_wen`, `moving_lines`, `TRIGRAM_LINES`, `TRIGRAM_ELEMENT`. Never re-derive an anchor; never add a second Sun model.
- Verified stack, 2026-11-11 12:22 America/New_York, natal 1986-05-01: global `8.5.1.1.8.4.8`, personal `2.5.9.9.2.6.2` (great age → hour). Every engine test starts from this. The natal year number for 1986 is **5** (`ki(2027 − 1986)`), natal month 9, natal triple 5·9·1; the spec's "1986 → 6" is a slip (with 6 the personal year would be 1, not 9).
- The 5 rule (ledger, 30 Oct 2026, second revision): 5 inherits the trigram of the nearest level above that is not 5; a stack that is 5 all the way up has **no figure** (return `None`, do not raise). A 5 period's element is its inherited trigram's element; a 5 native is Earth.
- Elements by number: 1 Water; 3, 4 Wood; 9 Fire; 2, 5, 8 Earth; 6, 7 Metal. Generating cycle Wood → Fire → Earth → Metal → Water → Wood; controlling cycle Wood → Earth → Water → Fire → Metal → Wood.
- Ledger text is verbatim and comes from the JSON dump, never retyped. Reading-view rewords are the page's `briefs.js` overrides and ride in the same dump.
- Jev decides and grades; Jev never writes. Never ask Jev what code can count (sentences, words, an ending). Without a Jev key the writer runs unbriefed and ungraded; without a writer key the pipeline returns `{"ok": false, "error": "no_key"}`.
- Prompts (`RULES`, `composeSystem`, `composeUser`, `ST_RULES`, `composeStatementSystem`, `composeStatementUser`, `EX_SYSTEM`, `exUser`), the Jev questions, the grade thresholds (synthesis ≥ 1.2, usable ≥ 0.45, method ≤ 0.8; adds ≥ 1.2, whole ≥ 0.5; explains ≥ 1.2) and the shape counts (sentences ≤ 3, words ≤ 60) are copied from `lib/forecast.js` word for word. Version constants start where the page's are: `PROMPT_VERSION = 4`, `STATEMENT_VERSION = 2`, `EXPLAIN_VERSION = 1`.
- Everything a person reads: American spelling, no em-dashes (pipelines turn them into commas), no emoji. Always name whose element it is ("Your earth in an earth hour"), never the bare pair.
- UI names in tool output: ba, shi, ji; octave, plot, palace; path of time and circuit; "Tri-force" with the hyphen.
- Env: `TYPESAFE_API_KEY` (Jev), `OPENROUTER_API_KEY`, `FORECAST_MODEL` (default `deepseek/deepseek-v4.1-flash`), `FORECAST_URL` (default `https://openrouter.ai/api/v1/chat/completions`), `DATA_DIR` (default `data/`), `JEVKIT_PATH` (default `~/hermes-jev-skills`). Keys are never printed, logged or returned.
- Tool count in `tests/test_tool_registry.py` rises from 93 to 103 (seven deterministic tools in Task 5, three pipeline tools in Task 8).
- All tool times are America/New_York unless an offset is given; `ki_solar.parse_target` is the parser.

## Review Focus

- A period whose stack is 5 at the level and at every level above (a 5 Ki Age inside a 5 great age is not possible before 2154, but a 5 great year under a 5 Ki Age is: 2154–2165). `figure` and `native_figure` must return `None`, the packet must carry `ba: null` and the tools must say "no figure, by decision", not crash (Task 1, Task 3).
- The top level (great age) has no container: `flow` is `None`, `shi` still exists (the next great age), the statement pipeline must skip the flow question (Task 3, Task 7).
- A period whose index falls outside the ephemeris window (`period_start_jd` returns `None`): tools return an error naming the level and index, never a traceback (Task 4, Task 5).
- The writer answers with reasoning and no text, or with fenced JSON: the forecast reports `"the model spent its budget reasoning and sent no text"`; `parse_explain` strips fences and takes the first `{` to the last `}` (Task 6, Task 7).
- A thought that passes Jev's grade but ends the wrong way (Jev said ask, it told): it is rewritten once but does not fail; the one that ends right ranks above the one that adds more (Task 7).

---

### Task 0: Spec export and the ledger dump

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-octave-system.md` (the doc's text, from the read already saved at `/private/tmp/claude-501/-Volumes-Shirahoshi-HermesNode-clawd-stella/aab0ba31-9f4c-4e78-81f2-08413ea5ed40/scratchpad/octave_doc.txt`, re-read from the doc link if that file is gone)
- Create: `scripts/export_octave_ledger.sh`
- Create: `data/octave_ledger.json`
- Test: `tests/test_octave_ledger.py`

**Interfaces:**
- Produces: `data/octave_ledger.json` with top-level keys `BRIEF`, `CONDITION`, `COND_CLAUSE`, `HOUSES`, `RELATION_WORD`, `FLOW_WORD`, `PAIRS`, `VERB`, `TENDING`, `STAR`, `LPOINTS`, `LLINKS`, `LRULES`, `LREADINGS`, `LLOG`, `LARCHIVE`, `exported` (ISO datetime), `source` (git short hash of the octave repo).

- [ ] **Step 1: Write the failing test**

```python
def test_ledger_json_has_every_table():
    d = json.load(open(ROOT / "data" / "octave_ledger.json"))
    for k in ("BRIEF", "CONDITION", "COND_CLAUSE", "HOUSES", "RELATION_WORD", "FLOW_WORD", "PAIRS", "VERB", "TENDING", "STAR", "LPOINTS", "LLINKS"):
        assert k in d, k
    assert d["BRIEF"]["2"]["q"] == "What is being received?"
    assert d["BRIEF"]["6"]["q"] == "What was the ego magnetic to?"          # the briefs override, not the ledger's pin
    assert d["CONDITION"]["Earth"]["Earth"].startswith("Earth on earth. Weight and stillness.")
    assert d["COND_CLAUSE"]["Earth"]["Wood"] == "with roots drawing on you"
    assert d["VERB"] == {"1>4": "nourish", "4>2": "break", "2>8": "inherit", "8>5": "keep", "5>7": "reflect", "7>1": "shape"}
    assert d["TENDING"]["5"]["scale"] == "self"
    assert d["HOUSES"]["8"]["dir"] == "North-east"
    assert d["STAR"]["5"] == "Yellow Earth"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_octave_ledger.py -v`
Expected: FAIL, file not found.

- [ ] **Step 3: Write `scripts/export_octave_ledger.sh`**

A shell script that `cd`s to `${OCTAVE_REPO:-/Volumes/Shirahoshi/HermesNode/octave}` and runs `node -e` which: reads `src/ledger.js` and `src/briefs.js` into one `vm.runInNewContext` (as `lib/forecast.js` `texts()` does), appends `;({BRIEF, CONDITION, COND_CLAUSE, HOUSES, RELATION_WORD, FLOW_WORD, PAIRS, VERB, TENDING, STAR, LPOINTS, LLINKS, LRULES, LREADINGS, LLOG, LARCHIVE})`, adds `exported` and `source` (`git rev-parse --short HEAD`), and writes JSON (indent 1) to `$1` (default `data/octave_ledger.json` in Stella). If `STAR` is not a constant in `briefs.js`, define it in the script from the spec: 1 White Water, 2 Black Earth, 3 Jade Wood, 4 Green Wood, 5 Yellow Earth, 6 White Metal, 7 Red Metal, 8 White Earth, 9 Purple Fire. `LRULES`/`LREADINGS`/`LLOG`/`LARCHIVE` that do not exist as globals are written as `null`, never guessed.

- [ ] **Step 4: Run the script, then the test**

Run: `sh scripts/export_octave_ledger.sh && .venv/bin/python -m pytest tests/test_octave_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/export_octave_ledger.sh data/octave_ledger.json docs/superpowers/specs/2026-11-12-octave-system.md tests/test_octave_ledger.py
git commit -m "feat(octave): ledger tables dumped from the page, spec export"
```

---

### Task 1: The engine: period, resolve, figure, moving, elements

**Files:**
- Create: `octave_engine.py`
- Test: `tests/test_octave_engine.py`

**Interfaces:**
- Consumes: `ki_solar.period_index(jd, level)`, `period_start_jd(level, idx)`, `period_stack(level, idx)`, `dt_to_jd`, `jd_to_dt`, `parse_target`, `solar_stack_at`; `ki_levels.ki`, `personal`, `personal_stack`; `hub_inheritance.resolve`, `HubUnresolvable`, `king_wen`, `moving_lines`, `TRIGRAM_LINES`, `TRIGRAM_PINYIN`, `TRIGRAM_ELEMENT`.
- Produces:
  - `LEVELS = ("great_age", "ki_age", "great_year", "year", "month", "day", "hour")`, `LABEL` (level → "great age", "Ki Age", …), `ELEMENT: dict[int, str]`, `HEX_NAME: list[str]` (Wilhelm titles, index = King Wen), `GNOSTIC_TITLE: dict[int, str]` (the page's `GNOSTIC` map).
  - `upper(level) -> str | None`, `lower(level) -> str | None`.
  - `@dataclass Resolved(ki: int, source: int | None, lines: tuple | None, element: str | None, inherited: str | None)`; `resolve(stack: dict[str, int], level: str) -> Resolved` (wraps `hub_inheritance.resolve`; on `HubUnresolvable` returns `Resolved(5, None, None, None, None)`).
  - `@dataclass Figure(n: int, name: str, gnostic: str | None, lines: tuple[int, ...], up: Resolved, lo: Resolved)`; `hex_of(up_ki: int, lo_ki: int) -> Figure` (neither 5); `figure(stack, level) -> Figure | None` (level's trigram over its container's; `None` at the top level or when either side is unresolved).
  - `moving(a: tuple, b: tuple) -> list[int]` (1 = bottom; the lines where they differ).
  - `relation(actor: str | None, field: str | None) -> str | None` returning `"resonates" | "fed_by" | "feeds" | "controls" | "controlled_by"`.
  - `line_figure(from_res: Resolved, to_res: Resolved) -> dict | None` with keys `fig` (Figure), `base` (Figure, origin doubled), `moving` (list[int]), `inherited_from`, `inherited_origin`.
  - `triforce(n: int) -> Figure | None` (3 → 51, 6 → 1, 9 → 30; `None` otherwise).
  - `natal_of(birth_date: str) -> dict(year: int, month: int, pm: int, ki_year: int)` from `solar_stack_at(datetime(y, m, d, 12))`.
  - `@dataclass Period(level, idx, start: datetime, end: datetime, gstack: dict, pstack: dict | None, stack: dict, number: int, global_number: int, personal_number: int | None, self: Resolved, fig: Figure | None, role: str)`; `period(level: str, idx: int, natal: int | None) -> Period` (raises `ValueError("outside the ephemeris")` when `period_start_jd` is `None`); `period_at(level, dt: datetime, natal) -> Period`; `role` is `"shock-given"` for 3, `"shock-made"` for 6, `"clarity"` for 9, else `"hexad"`.
  - `octave(level, idx, natal) -> list[Period]` (nine periods from `ki_solar.octave_start_index`).

- [ ] **Step 1: Write the failing tests**

```python
NATAL = "1986-05-01"
AT = datetime(2026, 11, 11, 12, 22)      # America/New_York

def test_stack_matches_the_page():
    p = E.period_at("hour", AT, E.natal_of(NATAL)["year"])
    assert [p.gstack[L] for L in E.LEVELS] == [8, 5, 1, 1, 8, 4, 8]
    assert [p.pstack[L] for L in E.LEVELS] == [2, 5, 9, 9, 2, 6, 2]

def test_natal_triple():
    n = E.natal_of(NATAL)
    assert (n["year"], n["month"], n["pm"]) == (5, 9, 1)   # 1986 → 5 (ki(2027 − 1986)); the spec's "1986 → 6" is a slip, the stack 2.5.9.9.2.6.2 only holds with 5

def test_resolve_five_inherits_and_all_five_is_no_figure():
    r = E.resolve({"great_age": 8, "ki_age": 5, "great_year": 5}, "great_year")
    assert (r.source, r.inherited, r.element) == (8, "great_age", "Earth")
    r5 = E.resolve({"great_age": 5, "ki_age": 5}, "ki_age")
    assert r5.lines is None and E.figure({"great_age": 5, "ki_age": 5}, "ki_age") is None

def test_month_figure_9_nov_2026():
    p = E.period_at("month", datetime(2026, 11, 9, 12), 6)
    assert p.fig.n == 36 and p.fig.name == "Darkening of the Light"

def test_line_figures_fixed_where_no_five():
    R = lambda k: E.resolve({"year": k}, "year")
    assert E.line_figure(R(1), R(4))["fig"].n == 59
    assert E.line_figure(R(4), R(2))["fig"].n == 46
    assert E.line_figure(R(2), R(8))["fig"].n == 23
    assert E.line_figure(R(7), R(1))["fig"].n == 60
    assert E.line_figure(R(8), R(1))["moving"] == [5, 6]       # Gen → Kan: 39 against 52

def test_triforce():
    assert (E.triforce(3).n, E.triforce(6).n, E.triforce(9).n, E.triforce(4)) == (51, 1, 30, None)

def test_relation_cycles():
    assert E.relation("Water", "Water") == "resonates"
    assert E.relation("Water", "Wood") == "feeds"
    assert E.relation("Water", "Metal") == "fed_by"
    assert E.relation("Water", "Fire") == "controls"
    assert E.relation("Water", "Earth") == "controlled_by"
    assert E.relation("Earth", "Fire") == "fed_by" and E.relation("Wood", "Earth") == "controls"
    assert E.relation(None, "Earth") is None

def test_period_outside_ephemeris_raises():
    with pytest.raises(ValueError):
        E.period("year", -3000, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_engine.py -v`
Expected: FAIL, `octave_engine` not found.

- [ ] **Step 3: Implement `octave_engine.py`**

Port `src/engine.js` lines 137–307 onto Stella's clock: `period()` probes the stack at mid-period through `ki_solar.period_stack` (month, day, hour) or at the opening Ki year (year and above), exactly as `period_stack` already does; `pstack = personal_stack(natal, gstack)`; `stack = pstack if natal else gstack`. `figure(stack, level)` = `hex_of(resolve(stack, level).source, resolve(stack, upper(level)).source)`. Copy `HEX_NAME` and `GNOSTIC_TITLE` from `engine.js` lines 174–184.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_engine.py tests/test_octave_engine.py
git commit -m "feat(octave): engine — periods on Stella's clock, figures, line figures, element relation"
```

---

### Task 2: Native figure, ji, and the Lo Shu palace

**Files:**
- Modify: `octave_engine.py`
- Test: `tests/test_octave_engine.py`

**Interfaces:**
- Produces:
  - `native_figure(p: Period, natal_month: int) -> Figure | None`: the personal number's trigram at `p.level` over the house of the natal month number at the same level (`personal_stack(natal_month, p.gstack)`), both resolved; `None` for a Global period (`p.pstack is None`) or when either side is unresolved.
  - `ji_lines(p: Period, natal_month: int) -> list[int]` = `moving(p.fig.lines, native.lines)` or `[]`.
  - `shi(p: Period) -> dict(to: int, fig: Figure | None, lines: list[int], start, end)` from `period(p.level, p.idx + 1, natal)`.
  - `HOMES = (4, 9, 2, 3, 5, 7, 8, 1, 6)`, `DIRECTION: dict[int, str]` (1 north … 9 south, lower case, hyphenated), `STAR` from the ledger JSON's `STAR`.
  - `palace(global_number: int, personal_number: int | None) -> dict(global, personal, cells: list[dict(home, dir, n, element, star)], five_yellow: int, broken: int | None, own: int | None, opposite: int | None, coincides: bool)`; cell `n = ki(home - 5 + global)`; `broken = 10 - five_yellow`, `None` when Five Yellow is the center.

- [ ] **Step 1: Write the failing tests**

```python
def test_native_figure_and_ji_9_nov_2026():
    n = E.natal_of("1986-05-01")
    m = E.period_at("month", datetime(2026, 11, 9, 12), n["year"])
    nat = E.native_figure(m, n["month"])
    assert (m.fig.n, nat.n, E.ji_lines(m, n["month"])) == (36, 11, [2])
    d = E.period_at("day", datetime(2026, 11, 9, 12), n["year"])
    assert (d.fig.n, E.native_figure(d, n["month"]).n, E.ji_lines(d, n["month"])) == (20, 53, [3])

def test_native_figure_global_profile_has_no_ji():
    m = E.period_at("month", datetime(2026, 11, 9, 12), None)
    assert E.native_figure(m, 9) is None

def test_palace_2026_global_1():
    pal = E.palace(1, 9)
    assert pal["five_yellow"] == 9 and pal["broken"] == 1
    assert pal["own"] == 9 and pal["opposite"] == 1 and pal["coincides"] is True
    assert [c["n"] for c in pal["cells"]] == [9, 5, 7, 8, 1, 3, 4, 6, 2]
    assert pal["cells"][4]["star"] == "White Water" and pal["cells"][4]["dir"] == "center"

def test_palace_month_global_8_and_center_five():
    pal = E.palace(8, 2)
    assert pal["five_yellow"] == 2 and pal["broken"] == 8 and pal["coincides"] is True
    assert all(c["n"] == E.ki(c["home"] + 3) for c in pal["cells"])
    assert E.palace(1, None)["own"] is None
    c = E.palace(5, None); assert c["five_yellow"] == 5 and c["broken"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_engine.py -v -k "native or palace"`
Expected: FAIL, attribute errors.

- [ ] **Step 3: Implement the four functions in `octave_engine.py`**

Port `engine.js` lines 241–262.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_engine.py tests/test_octave_engine.py
git commit -m "feat(octave): native figure, ji, shi and the Lo Shu palace"
```

---

### Task 3: The ledger module and the composed reading

**Files:**
- Create: `octave_ledger.py`
- Test: `tests/test_octave_ledger.py`

**Interfaces:**
- Consumes: `data/octave_ledger.json` (Task 0).
- Produces:
  - `load() -> dict` (lru_cached; path from `OCTAVE_LEDGER_JSON` or `data/octave_ledger.json`).
  - `brief(n: int) -> dict` (the `BRIEF[n]` entry with keys `name, fn, img, shadow, q, practice, family, fam, tarot, status, since`), `tending(n) -> dict | None`, `house(n) -> dict(dir, line)`, `star(n) -> str`, `pair(from_n: int, to_n: int) -> dict(verb, title, kind, lines, practice, hex, shadows)` (from `PAIRS["f>t"]` + `VERB`), `condition_text(actor: str, field: str) -> str`, `relation_word(rel) -> str`, `flow_word(rel) -> str`.
  - `statement(q: str, rel: dict | None) -> str`: `rel = {"cond": relation, "ne": native_element, "pe": period_element}`; the question with `COND_CLAUSE[ne][pe]` appended before its final `?`/`.`.
  - `trad(rel, level: str) -> str` and `trad_key(rel, level) -> str`: port `TRAD_OPEN`, `TRAD`, `TRAD_KEY` from `src/briefs.js` lines 169–183 verbatim (the opening image of the condition reading is kept as the clause unless it only restates the pair).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_octave_ledger.py`)

```python
def test_statement_appends_the_condition_clause():
    rel = {"cond": "controlled_by", "ne": "Earth", "pe": "Wood"}
    assert L.statement("What is being received?", rel) == "What is being received, with roots drawing on you?"
    assert L.statement("What is being received?", None) == "What is being received?"

def test_trad_and_its_key():
    rel = {"cond": "resonates", "ne": "Earth", "pe": "Earth"}
    assert L.trad(rel, "hour") == "Your earth in an earth hour. Weight and stillness. Nothing cuts, nothing pushes; the risk is Stagnation. Do not grasp."
    assert L.trad_key(rel, "hour") == "Your earth in an earth hour."
    rel2 = {"cond": "controlled_by", "ne": "Earth", "pe": "Wood"}
    assert L.trad(rel2, "day").startswith("Your earth in a wood day: roots in the soil.")

def test_pair_and_brief():
    assert L.pair(8, 5)["verb"] == "keep" and L.pair(8, 5)["kind"] == "octave trace"
    assert L.pair(1, 4)["kind"] == "interval trace"
    assert L.brief(5)["q"] == "What landed here from above?"
    assert L.tending(2)["scale"] == "all" and L.tending(3) is None
    assert L.house(1)["dir"] == "North" and L.star(9) == "Purple Fire"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_ledger.py -v`
Expected: FAIL, `octave_ledger` not found.

- [ ] **Step 3: Implement `octave_ledger.py`**

Data access is dict lookups over the JSON (keys are strings in JSON: `str(n)`). `trad` needs `LABEL` from `octave_engine` for the level word and the page's `AN` helper (a/an by first letter).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_ledger.py tests/test_octave_ledger.py
git commit -m "feat(octave): ledger access and the composed statement, quiet sentence and key"
```

---

### Task 4: The packet

**Files:**
- Create: `octave_packet.py`
- Test: `tests/test_octave_packet.py`

**Interfaces:**
- Consumes: Task 1–3; `octave.octave_reading(hexagram, lines, full)` for the book's text.
- Produces: `packet(level: str, idx: int, natal: str) -> dict` with exactly the page's keys: `level, idx, natal, number, global, span{start,end}` (ISO, America/New_York), `point{name, question, image, practice}`, `house{number, dir, line}`, `tending`, `ba{n, name, gnostic?, upper, lower} | None`, `inherited`, `native{..., natalMonth} | None`, `ji: list[int]`, `shi{to, ba, lines, span}`, `condition{native, field, relation, word, text, statement} | None`, `flow{field, container, containerLevel, relation, word, text} | None`, `sources{ba, ji, shi, native, point, ground}` each `{label, short, full} | None`. Also `packet_at(level, dt: datetime, natal) -> dict` and `book_text(n, lines, full) -> str | None`, `line_text(n, lines) -> str | None` (the markdown after `## Line n`).

- [ ] **Step 1: Write the failing tests**

```python
def test_packet_month_9_nov_2026_natal_1986():
    pk = P.packet_at("month", datetime(2026, 11, 9, 12), "1986-05-01")
    assert pk["ba"]["n"] == 36 and pk["native"]["n"] == 11 and pk["ji"] == [2]
    assert pk["point"]["question"] == L.brief(pk["number"])["q"]
    assert pk["condition"]["native"] == "Earth"             # 1986 → 5, Earth
    assert pk["flow"]["containerLevel"] == "year"
    assert pk["sources"]["ji"]["label"].startswith("what the person meets: 36 at line 2")
    assert "## Line 2" in pk["sources"]["ji"]["short"]
    assert pk["sources"]["shi"]["full"].endswith(P.book_text(pk["shi"]["ba"]["n"], [], False)) or "Where it lands" in pk["sources"]["shi"]["full"]
    assert pk["span"]["start"] < pk["span"]["end"]

def test_packet_top_level_has_no_flow_and_no_figure():
    pk = P.packet_at("great_age", datetime(2026, 11, 9, 12), "1986-05-01")
    assert pk["ba"] is None and pk["flow"] is None and pk["sources"]["ba"] is None
    assert pk["shi"]["to"] in range(1, 10)

def test_packet_rejects_bad_level():
    with pytest.raises(ValueError):
        P.packet("week", 0, "1986-05-01")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_packet.py -v`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `octave_packet.py`**

Port `lib/forecast.js` lines 32–74 one to one; the source labels and the `ground` short/full strings are copied verbatim.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_packet.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_packet.py tests/test_octave_packet.py
git commit -m "feat(octave): the packet — one period, its figures, condition, flow, house and sources"
```

---

### Task 5: The seven deterministic tools

**Files:**
- Create: `octave_tools.py`
- Modify: `stella_server.py:6485-6486` (add `from octave_tools import register_octave_tools; register_octave_tools(mcp)`)
- Modify: `tests/test_tool_registry.py:17` (93 → 100)
- Test: `tests/test_octave_tools.py`

**Interfaces:**
- Produces `register_octave_tools(mcp)` registering, each returning JSON (`indent=1, ensure_ascii=False`) or `{"error": ...}`:
  - `get_octave_period(level: str, datetime: str | None = None, idx: int | None = None, natal: str | None = None)` → the packet (natal) or, without natal, the Global period: `number, global, span, ba, shi, house, point, palace`.
  - `get_octave_condition(natal: str, level: str, datetime: str | None = None, idx: int | None = None)` → `{condition, flow, statement, trad, trad_key}`.
  - `get_native_figure(natal, level, datetime=None, idx=None)` → `{ba, native, ji, text}` where `text` is the ba's text at the ji lines.
  - `get_octave_shi(level, datetime=None, idx=None, natal=None)` → `{ba, shi, text, next}`.
  - `get_palace(level, datetime=None, idx=None, natal=None)` → `palace(...)` plus `house{number, dir, line}` and `star`.
  - `get_octave_point(number: int)` → the brief plus `tending`, `family`, `force` (3, 6, 9: the Tri-force figure number and name).
  - `get_octave_line(from_number: int, to_number: int, datetime: str | None = None, level: str = "day")` → the pair (verb, kind, title, lines, practice) plus its figure: fixed where no 5 is involved, else resolved on the stack at `datetime`/`level`.
- `datetime` parsed by `ki_solar.parse_target`; `idx` wins when both are given; neither means now.

- [ ] **Step 1: Write the failing tests**

```python
def test_get_octave_period_natal():
    d = json.loads(run(stella_server.get_octave_period(level="month", datetime="2026-11-09T12:00", natal="1986-05-01")))
    assert d["ba"]["n"] == 36 and d["ji"] == [2] and "sources" in d

def test_get_octave_period_global_has_palace_and_no_ji():
    d = json.loads(run(stella_server.get_octave_period(level="year", datetime="2026-06-01T12:00")))
    assert d["global"] == 1 and d["palace"]["five_yellow"] == 9 and "ji" not in d

def test_get_octave_condition_names_whose_element():
    d = json.loads(run(stella_server.get_octave_condition(natal="1986-05-01", level="hour", datetime="2026-11-11T12:22")))
    assert d["trad"].startswith("Your earth in ") and d["trad_key"].endswith(".")
    assert d["statement"] != d["condition"]["statement"] or d["statement"].endswith("?")

def test_get_octave_point_and_line():
    p = json.loads(run(stella_server.get_octave_point(number=3)))
    assert p["name"] == "Power" and p["force"]["n"] == 51
    l = json.loads(run(stella_server.get_octave_line(from_number=7, to_number=1)))
    assert l["verb"] == "shape" and l["figure"]["n"] == 60 and l["kind"] == "octave trace"

def test_get_palace_month_8():
    d = json.loads(run(stella_server.get_palace(level="month", datetime="2026-02-10T12:00", natal="1986-05-01")))
    assert d["five_yellow"] == 2 and d["star"]

def test_tools_report_bad_input_as_error():
    assert "error" in json.loads(run(stella_server.get_octave_period(level="week")))
    assert "error" in json.loads(run(stella_server.get_octave_period(level="year", idx=-3000)))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_tools.py tests/test_tool_registry.py -v`
Expected: FAIL, attribute errors and `93 == 100`.

- [ ] **Step 3: Implement `octave_tools.py` and register it**

Docstrings name the lens words (ba, shi, ji), say peaks of nothing (this is not ZR), and state the time zone rule. Every tool catches `ValueError` and returns `{"error": str(e)}`.

- [ ] **Step 4: Run the tests and the whole suite**

Run: `.venv/bin/python -m pytest tests -q --ignore=tests/test_stella_http.py --ignore=tests/test_stella_ws.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add octave_tools.py stella_server.py tests/test_octave_tools.py tests/test_tool_registry.py
git commit -m "feat(octave): seven tools — period, condition, native figure, shi, palace, point, line"
```

---

### Task 6: Jev and writer clients

**Files:**
- Create: `octave_models.py`
- Test: `tests/test_octave_models.py`

**Interfaces:**
- Produces:
  - `jev_ask(state: str, questions: dict, *, timeout: float = 8.0) -> dict`: `{"ok": True, "answers": {...}, "latency_ms": int}` or `{"ok": False, "error": "no_key" | "timeout" | "transport" | "bad_reply" | <JevError code>}`; never raises. Imports `jevkit.client` from `JEVKIT_PATH` (default `~/hermes-jev-skills`), added to `sys.path` on first call; when the import fails returns `{"ok": False, "error": "no_jevkit"}`.
  - `choice(instructions, criteria: dict) -> dict`, `score(instructions, levels: list) -> dict`, `noul(instructions) -> dict` (thin wrappers over `jevkit.client`, same shapes as `lib/jev.js`).
  - `level_word(answer: dict) -> str | None` (nearest legend word for a score answer, as `lib/jev.js` `levelWord`).
  - `write(system: str, prompt: str, *, max_tokens: int = 1600, timeout: float = 60.0, key=None, model=None, url=None, post=None) -> dict`: `{"ok": True, "text": str}` or `{"ok": False, "status": 502, "error": "upstream", "message": str}`; body `{model, max_tokens, temperature: 0.7, reasoning: {enabled: false}, messages: [system, user]}`; headers `Authorization: Bearer`, `HTTP-Referer: http://octave.lan`, `X-Title: Stella Octave`; `post` is an injectable `(url, body: bytes, headers) -> (status, json)` for tests; empty text with `reasoning` present → message `"the model spent its budget reasoning and sent no text"`.
  - `writer_config(key=None, model=None, url=None) -> dict(key, model, url)` reading the env defaults.
  - `Cache`: `load_cache(data_dir) -> dict` (read once, memoized per dir) and `save_cache(data_dir, cache)` (write to `forecasts.json.tmp` then rename).

- [ ] **Step 1: Write the failing tests**

```python
def test_write_parses_an_openai_reply():
    post = lambda url, body, headers: (200, {"choices": [{"message": {"content": "  One thought.  "}}]})
    r = M.write("sys", "user", key="k", model="m", url="http://x", post=post)
    assert r == {"ok": True, "text": "One thought."}

def test_write_reports_reasoning_without_text():
    post = lambda url, body, headers: (200, {"choices": [{"message": {"content": "", "reasoning": "..."}}]})
    assert M.write("s", "u", key="k", model="m", url="http://x", post=post)["message"] == "the model spent its budget reasoning and sent no text"

def test_write_sends_reasoning_off_and_temperature(monkeypatch):
    seen = {}
    def post(url, body, headers): seen.update(json.loads(body)); return (200, {"choices": [{"message": {"content": "t"}}]})
    M.write("s", "u", key="k", model="m", url="http://x", post=post)
    assert seen["reasoning"] == {"enabled": False} and seen["temperature"] == 0.7 and seen["max_tokens"] == 1600

def test_jev_ask_without_key_is_no_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("JEVKIT_PATH", "/nonexistent")
    r = M.jev_ask("state", {"q": M.noul("x")})
    assert r["ok"] is False and r["error"] in ("no_key", "no_jevkit")

def test_cache_round_trip(tmp_path):
    c = M.load_cache(tmp_path); c["k"] = {"text": "t"}; M.save_cache(tmp_path, c)
    assert json.load(open(tmp_path / "forecasts.json")) == {"k": {"text": "t"}}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_models.py -v`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `octave_models.py`**

`write` uses `urllib.request` with the given timeout; `jev_ask` calls `jevkit.client.ask(state, questions, timeout=timeout, retries=1)` and maps `JevError.code` (or the first arg) to `error`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_models.py tests/test_octave_models.py
git commit -m "feat(octave): Jev and writer clients, forecast cache"
```

---

### Task 7: The three pipelines

**Files:**
- Create: `octave_forecast.py`
- Test: `tests/test_octave_forecast.py`

**Interfaces:**
- Consumes: Task 4 `packet`, Task 6 clients.
- Produces, each taking `(level, idx, natal, *, fresh=False, data_dir=None, post=None, jev=None, key=None, model=None, url=None)` where `post` and `jev` are injectable (`jev(state, questions) -> dict` as `jev_ask`):
  - `forecast(...) -> dict`: `{ok, status, cached, model, text, jev, jevNote, grade, rewritten, at}`; cache key `f"v{PROMPT_VERSION}|{model}|{level}|{idx}|{natal}"`.
  - `statement(...) -> dict`: `{ok, status, cached, model, text | None, draft?, composed, jev, jevNote, grade, rewritten, at}`; key `f"s{STATEMENT_VERSION}|…"`.
  - `explain(...) -> dict`: `{ok, status, cached, model, of, parts, whole, questions, close, grade, jevNote, rewritten, at}`; key `f"x{EXPLAIN_VERSION}|…"`; `{"ok": False, "status": 404, "error": "no_statement"}` when `statement` wrote nothing.
  - Module constants and helpers, all ported verbatim from `lib/forecast.js`: `PROMPT_VERSION`, `STATEMENT_VERSION`, `EXPLAIN_VERSION`, `SOURCE_KEYS`, `WEIGHT`, `FRAME`, `RULES`, `ST_RULES`, `EX_SYSTEM`, `TEND_WORD`, `read_questions(pk)`, `read_state(pk)`, `read_of(answers)`, `GRADE_Q`, `grade_of`, `compose_system(pk, read)`, `compose_user(pk, read, feedback)`, `statement_questions(pk)`, `st_read_of(answers, pk)`, `compose_statement_system(pk, read)`, `compose_statement_user(pk, feedback)`, `ST_GRADE_Q`, `shape_of(text, form)`, `st_grade_of(answers, shape)`, `tidy(text)`, `ex_user(pk, text, feedback)`, `parse_explain(raw)`, `EX_GRADE_Q`, `ex_grade_of`, `ex_flat`.

- [ ] **Step 1: Write the failing tests** (a fake writer returning canned text; a fake Jev returning canned answers; `tmp_path` as `data_dir`; `level="month"`, `idx` of 9 Nov 2026, natal 1986-05-01)

```python
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

def test_explain_keyed_to_the_thought(tmp_path):
    ...  # a passing statement, then explain twice: second call cached is True and `of` equals the statement text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_forecast.py -v`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `octave_forecast.py`**

Port `lib/forecast.js` lines 76–375. Keep the three pipelines as three functions sharing `_config(opts)` and `_jev(opts)`; the rewrite ranking rules are copied exactly (forecast: higher synthesis wins; statement: `rank = 2*pass + form`, then adds; explain: pass over fail, then explains).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_forecast.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_forecast.py tests/test_octave_forecast.py
git commit -m "feat(octave): forecast, statement and explain pipelines — Jev decides, the writer phrases, Jev grades"
```

---

### Task 8: The three pipeline tools

**Files:**
- Modify: `octave_tools.py`
- Modify: `tests/test_tool_registry.py:17` (100 → 103)
- Test: `tests/test_octave_tools.py`

**Interfaces:**
- `write_octave_forecast(natal: str, level: str, datetime: str | None = None, idx: int | None = None, fresh: bool = False)`, `write_octave_statement(same)`, `explain_octave_statement(natal, level, datetime=None, idx=None)` → the pipeline result as JSON; `system` prompt never included; keys never included.

- [ ] **Step 1: Write the failing tests**

```python
def test_write_octave_statement_without_keys_says_so(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    d = json.loads(run(stella_server.write_octave_statement(natal="1986-05-01", level="month", datetime="2026-11-09T12:00")))
    assert d["ok"] is False and d["error"] == "no_key" and "system" not in d

def test_explain_tool_passes_through_404(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    d = json.loads(run(stella_server.explain_octave_statement(natal="1986-05-01", level="month", datetime="2026-11-09T12:00")))
    assert d["ok"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_tools.py tests/test_tool_registry.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the three tools**

Each resolves `idx` from `datetime` as Task 5 does, calls the pipeline with `data_dir` from `DATA_DIR`, and returns `json.dumps(result, indent=1, ensure_ascii=False)`.

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/python -m pytest tests -q --ignore=tests/test_stella_http.py --ignore=tests/test_stella_ws.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add octave_tools.py tests/test_octave_tools.py tests/test_tool_registry.py
git commit -m "feat(octave): write_octave_forecast, write_octave_statement, explain_octave_statement"
```

---

### Task 9: The synodic gate anchor

**Files:**
- Modify: `stella_server.py:822-870` (`get_synodic_gate_now`)
- Test: `tests/test_octave_tools.py`

**Interfaces:**
- The tool's numbers come from `ki_levels.global_great_year(ki_year)` and `ki_levels.gate_start`; its docstring says "Lichun 2010 opened 2; Lichun 2022 opened 1" and nothing about gate 8.

- [ ] **Step 1: Write the failing test**

```python
def test_synodic_gate_matches_the_live_stack():
    d = json.loads(run(stella_server.get_synodic_gate_now(date="2026-11-11")))   # adapt to the tool's parameter name
    assert d[<gate ki key>] == 1 and str(d[<gate start key>]).startswith("2022")
    assert "gate 8" not in stella_server.get_synodic_gate_now.__doc__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_octave_tools.py -k synodic -v`
Expected: FAIL on the docstring (and on the number if the arithmetic was also wrong).

- [ ] **Step 3: Replace the tool's arithmetic with `ki_levels` and rewrite the docstring**

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add stella_server.py tests/test_octave_tools.py
git commit -m "fix(ki): synodic gate anchored with ki_levels — 2022 opened 1, not 8"
```

---

### Task 10: Framework, skill, resources and docs

**Files:**
- Modify: `octave.py:22-89` (`FRAMEWORK`), `octave.py:151-168` (`hermes_skill`, version 2.0.0), `octave.py:170-225` (add `@mcp.resource("octave://ledger")` returning the JSON text, and `@mcp.prompt(name="octave_period_reading")`)
- Create: `docs/OCTAVE_REFERENCE.md`
- Modify: `TOOLS.md`, `CHANGELOG.md`
- Test: `tests/test_octave.py`

**Interfaces:**
- `FRAMEWORK` gains sections, in this order after "The figures": "The three lenses" (ba, shi, ji as the spec's "Figures" section states them), "Elements: condition and flow" (the five relation words, whose element it is), "The palace" (flight rule, flags, the nine house lines), "The ledger" (the nine points' names and questions, the six verbs with their trace kinds, tending at three scales, the Tri-force), "Reading order" (head, condition, ji, shi, in practice; interval trace before octave trace), and "Standing rules" (the seven rules from the spec's last section, verbatim). "How to read" lists the ten tools by name.
- `octave://ledger` serves `data/octave_ledger.json`.

- [ ] **Step 1: Write the failing tests**

```python
def test_framework_v2_carries_the_lenses_and_rules():
    f = octave.FRAMEWORK
    for s in ("Ba (場)", "Shi (勢)", "Ji (機)", "resonates", "fed by", "Five Yellow", "What's under the surface?", "nourish", "tends everything", "Tri-force", "Jev decides and grades; Jev never writes", "get_octave_period", "write_octave_statement"):
        assert s in f, s
    assert "version: 2.0.0" in octave.hermes_skill()

def test_ledger_resource_registered():
    import stella_server
    names = {str(r.uri) for r in asyncio.run(stella_server.mcp.list_resources())}
    assert "octave://ledger" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the FRAMEWORK sections, the resource, the prompt, `docs/OCTAVE_REFERENCE.md` (the spec's tables: levels and anchors, relation table, flags, houses, points, lines, the 25 readings as a table, the tool map), the `TOOLS.md` rows (94–103, header "103 Tools") and the CHANGELOG entry**

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/python -m pytest tests -q --ignore=tests/test_stella_http.py --ignore=tests/test_stella_ws.py`
Expected: all pass. Then: `.venv/bin/python -c "import octave; print(octave.hermes_skill())" | head -5` prints the v2 header.

- [ ] **Step 5: Commit**

```bash
git add octave.py docs/OCTAVE_REFERENCE.md TOOLS.md CHANGELOG.md tests/test_octave.py
git commit -m "docs(octave): framework 2.0 — lenses, elements, palace, ledger, standing rules; ledger resource"
```

---

### Task 11: Cross-check against the page (verification only, no code)

- [ ] **Step 1:** For 2026-11-11 12:22 and natal 1986-05-01, at every level, compare `get_octave_period` with the page's `GET /api/forecast` packet fields (`number, global, ba.n, native.n, ji, shi.lines, condition.relation, flow.relation`) via `curl http://192.168.1.181:3333/api/...` or the page's `node -e "require('./lib/forecast.js').packet(...)"`. Every field equal; span boundaries within 10 seconds.
- [ ] **Step 2:** Run the page's own tests (`cd /Volumes/Shirahoshi/HermesNode/octave && node --test`) to confirm nothing there was touched.
- [ ] **Step 3:** Record both results in the CHANGELOG entry's last line.

---

## Parked (out of this plan, by the spec)

- Indexing the ledger into `knowledge_search` (Neo4j): needs the rebuild script from the 2026-10-23 retrieval work; one line in `docs/OCTAVE_REFERENCE.md` says the `octave://ledger` resource is the source when that happens.
- The Japanese names for the three lenses (wa, kairo, mitsudomoe); the 9 and 10 Nov ledger touches not yet in the Ki Octave Study page.
- Merging `feat/palace-field-ji` into the page's `main` is the owner's call and does not affect Stella.
