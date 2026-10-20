# Hub Inheritance and Octave Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every timekeeping hexagram in Stella resolve Ki 5 by inheriting the nearest non-5 parent's trigram, add the Ki Age and great age levels, and move the octave math into Stella.

**Architecture:** Two new pure modules carry the rules: `hub_inheritance.py` (trigram resolution, hexagram lines, moving lines, King Wen) and `ki_levels.py` (Lo Shu arithmetic for every level and its gates). `ki_changes.py`, `ki.py` and the `stella_server.py` Ki tools are rewired to form figures from full stacks through those modules. `octave_math.py` is a Python port of the Nine-Year Spiral library using the same modules, and `octave.py` serves it instead of calling the app over HTTP.

**Tech Stack:** Python 3.14, pytest (`.venv/bin/python -m pytest`), pyswisseph via `ki_calendar.py` for boundaries. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-20-hub-inheritance.md`

## Global Constraints

- The reading path is untouched: `ki_reading.py`, `get_ki`, `get_ki_cycle`, `get_ki_reading`, `get_ki_transition`, `tests/test_hexagram_five.py` keep passing unchanged.
- Personal and global stacks never mix: a 5 inherits only within its own chain.
- Anchors: Lichun 2022 opens great year 8, Ki Age 2, great age 5 (the stack there reads 5.2.8.5.2). Periods 12, 144, 1,296 years. Global year 2026 = 1. Global Feb 2026 = month 8.
- `personal(natal, g) = ki(natal - g + 5)` where `ki(n) = ((n - 1) mod 9) + 1`, at every level.
- Hexagram lines are bottom → top, 1 = yang; lower trigram = parent level, upper = child.
- Moving lines are always the line-by-line difference of two six-line figures.
- No fixed moving-line tables anywhere in code; the old table lives only in a test.
- Existing tests in `tests/` keep passing except `tests/test_octave.py`, which this plan rewrites to run without the app.
- Every commit message ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. **A level change that coincides with a gate.** When the next Lichun opens a great-year gate (2034), `ki_change_year` must advance the great year (and Ki Age / great age when their gates coincide) in the "next" stack, so a next-year 5 inherits the new parent. Test in Task 3.
2. **A personal 5 whose global twin is not 5.** Chris in 2022 has personal year 5 over global year 5 and global great year 8; the personal hexagram's lower trigram must be Kun (personal great year 2), never Gen. Test in Task 3.
3. **An octave year that is 5.** Every month figure of a personal-5 year forms over the inherited great-year trigram, and a 5 month in a 5 year yields hexagram 2 (Chris, Aug 2022), never "no figure". Test in Task 6.
4. **A schedule stepping through 5.** `get_ki_change_schedule` walks Ki 6 → 5 → 4 at one level; the 5 step must show the inherited trigram and compute its lines against it. Test in Task 4.
5. **An unresolvable stack.** A caller that builds a stack with every level 5 (possible only with synthetic input) gets `HubUnresolvable`, and the tools return a readable message, not a traceback. Test in Task 1 (raise) and Task 4 (message).

---

### Task 1: hub_inheritance module

**Files:**
- Create: `hub_inheritance.py`
- Test: `tests/test_hub_inheritance.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `TRIGRAM_LINES: dict[int, tuple[int,int,int]]` for 1,2,3,4,6,7,8,9 (values from the spec's module).
  - `TRIGRAM_NAME: dict[int, str]` e.g. `9: "☲ Li"`.
  - `TRIGRAM_SYMBOL: dict[int, str]`, `TRIGRAM_PINYIN: dict[int, str]`, `TRIGRAM_ELEMENT: dict[int, str]` (Water, Earth, Wood, Wood, Metal, Metal, Earth, Fire for 1,2,3,4,6,7,8,9; the Wu Xing elements `ki_changes.py` already uses: 3 Thunder→Wood, 4 Wind→Wood).
  - `LEVELS = ("great_age", "ki_age", "great_year", "year", "month", "day", "hour")`.
  - `class HubUnresolvable(ValueError)`.
  - `@dataclass(frozen=True) class ResolvedTrigram: ki: int; lines: tuple[int,int,int]; inherited_from: Optional[str]` with properties `source_ki -> int` and `name -> str` ("☲ Li" or "☲ Li (inherited from month)").
  - `resolve(stack: dict[str,int], level: str) -> ResolvedTrigram`.
  - `hexagram_lines(stack, upper: str, lower: str) -> tuple[int,...]` (six lines, lower level's trigram first).
  - `moving_lines(deposit: tuple, charge: tuple) -> list[dict]` items `{"line": int, "from": "yin"|"yang", "to": "yin"|"yang"}`.
  - `king_wen(lines: tuple[int,...]) -> int` using the spec's `KING_WEN` dict keyed by binary with bit 0 = line 1.
  - `hexagram(stack, upper: str, lower: str) -> dict` returning `{"hexagram": int, "lines": list[int], "lower": {"level", "ki", "trigram": name, "symbol", "pinyin", "element", "inherited_from"}, "upper": {...same...}, "inherited": [ {"level": str, "from": str}, ... ] }` where `inherited` lists each of the two levels that inherited (empty list when none).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_hub_inheritance.py
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hub_inheritance import (HubUnresolvable, hexagram, hexagram_lines, king_wen,
                             moving_lines, resolve, TRIGRAM_LINES)

PURE = {1: 29, 2: 2, 3: 51, 4: 57, 6: 1, 7: 58, 8: 52, 9: 30}

@pytest.mark.parametrize("month,expected", PURE.items())
def test_day_five_over_month_is_pure_hexagram(month, expected):
    stack = {"great_year": 2, "year": 9, "month": month, "day": 5}
    assert king_wen(hexagram_lines(stack, upper="day", lower="month")) == expected
    assert resolve(stack, "day").inherited_from == "month"

def test_chain_of_fives_resolves_to_first_non_five_parent():
    chain = {"great_year": 2, "year": 9, "month": 5, "day": 5}
    assert resolve(chain, "day").inherited_from == "year"
    assert resolve(chain, "month").inherited_from == "year"
    assert king_wen(hexagram_lines(chain, "day", "month")) == 30

def test_all_five_raises_and_ki_age_resolves_great_year():
    with pytest.raises(HubUnresolvable):
        resolve({"great_age": 5, "ki_age": 5, "great_year": 5, "year": 5}, "year")
    deep = {"ki_age": 8, "great_year": 5, "year": 5, "month": 5, "day": 5}
    assert resolve(deep, "great_year").inherited_from == "ki_age"
    assert king_wen(hexagram_lines(deep, "day", "month")) == 52

def test_five_seven_under_kun_parent_matches_old_table():
    dep = hexagram_lines({"great_year": 2, "year": 5}, "year", "great_year")
    chg = hexagram_lines({"great_year": 2, "year": 7}, "year", "great_year")
    assert king_wen(dep) == 2 and king_wen(chg) == 45
    assert moving_lines(dep, chg) == [
        {"line": 4, "from": "yin", "to": "yang"}, {"line": 5, "from": "yin", "to": "yang"}]

def test_five_seven_under_dui_parent_has_no_moving_lines():
    dep = hexagram_lines({"great_year": 7, "year": 5}, "year", "great_year")
    chg = hexagram_lines({"great_year": 7, "year": 7}, "year", "great_year")
    assert moving_lines(dep, chg) == []

def test_one_four_and_two_eight_stay_line_six_under_any_parent():
    for parent in TRIGRAM_LINES:
        for a, b in ((1, 4), (2, 8)):
            dep = hexagram_lines({"great_year": parent, "year": a}, "year", "great_year")
            chg = hexagram_lines({"great_year": parent, "year": b}, "year", "great_year")
            assert moving_lines(dep, chg) == [{"line": 6, "from": "yin", "to": "yang"}]

def test_spec_example_oct_22_2026():
    stack = {"great_year": 2, "year": 9, "month": 1, "day": 5}
    h = hexagram(stack, upper="day", lower="month")
    assert h["hexagram"] == 29
    assert h["upper"]["trigram"] == "☵ Kan (inherited from month)"
    assert h["inherited"] == [{"level": "day", "from": "month"}]
    assert hexagram({**stack, "day": 7}, "day", "month")["inherited"] == []

def test_king_wen_covers_all_64():
    assert sorted(king_wen(tuple((n >> i) & 1 for i in range(6))) for n in range(64)) == list(range(1, 65))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_hub_inheritance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hub_inheritance'`

- [ ] **Step 3: Implement `hub_inheritance.py`**

Start from the spec's drop-in module verbatim (tables, `resolve`, `hexagram_lines`, `moving_lines`, `KING_WEN`, `king_wen`). Add the symbol/pinyin/element tables and `hexagram()` as described in Interfaces. The `source_ki` lookup must use the lines tuple, not the level's own ki.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_hub_inheritance.py -v`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add hub_inheritance.py tests/test_hub_inheritance.py
git commit -m "Add hub inheritance: Ki 5 takes the nearest non-5 parent's trigram"
```

---

### Task 2: ki_levels module and Ki Age / great age arithmetic

**Files:**
- Create: `ki_levels.py`
- Modify: `convergence_ki.py:284-297` (the three synodic constants and `synodic_ki_for_year` delegate to `ki_levels`)
- Test: `tests/test_ki_levels.py`

**Interfaces:**
- Consumes: nothing (pure arithmetic; no ephemeris).
- Produces:
  - `ki(n: int) -> int`, `personal(natal: int, g: int) -> int`.
  - `GREAT_YEAR_ANCHOR_YEAR = 2022`, `GREAT_YEAR_ANCHOR_KI = 8`, `KI_AGE_ANCHOR_YEAR = 2022`, `KI_AGE_ANCHOR_KI = 2`, `GREAT_AGE_ANCHOR_YEAR = 2022`, `GREAT_AGE_ANCHOR_KI = 5`, `PERIOD_YEARS = {"great_age": 1296, "ki_age": 144, "great_year": 12, "year": 1}`. A comment beside the Ki Age anchor names the two other lattices the arithmetic allows (opening 1914, next 2058; opening 1950, next 2094).
  - `global_year(ki_year: int) -> int` = `ki(2027 - ki_year)`.
  - `global_month(abs_month: int) -> int` = `ki(8 - (abs_month - 2026*12))`, with `abs_month = ki_year*12 + index`.
  - `global_great_year(ki_year) -> int`, `global_ki_age(ki_year) -> int`, `global_great_age(ki_year) -> int`: each `ki(anchor_ki - floor((ki_year - anchor_year) / period))`.
  - `gate_start(ki_year: int, level: str) -> int` for `great_year|ki_age|great_age`: the Ki year that opens the period containing `ki_year`.
  - `global_stack(ki_year: int, abs_month: Optional[int] = None) -> dict[str,int]` with keys `great_age, ki_age, great_year, year` and `month` when `abs_month` is given.
  - `personal_stack(natal_year: int, stack: dict[str,int]) -> dict[str,int]` applying `personal` to every value.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ki_levels.py
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ki_levels import (gate_start, global_great_age, global_great_year, global_ki_age,
                       global_month, global_stack, global_year, ki, personal, personal_stack)

def test_digits():
    assert [ki(n) for n in (0, 1, 9, 10, -1)] == [9, 1, 9, 1, 8]
    assert (personal(5, 1), personal(5, 9), personal(5, 8)) == (9, 1, 2)

def test_year_and_month():
    assert (global_year(2026), global_year(1986), global_year(2022)) == (1, 5, 5)
    assert global_month(2026 * 12) == 8 and global_month(2022 * 12) == 2
    assert global_month(2026 * 12 + 8) == 9  # Oct 2026

@pytest.mark.parametrize("year,expected", [(2009, 1), (2010, 9), (2021, 9), (2022, 8), (2033, 8), (2034, 7), (1986, 2)])
def test_great_year(year, expected):
    assert global_great_year(year) == expected

@pytest.mark.parametrize("year,expected", [(2021, 3), (2022, 2), (2165, 2), (2166, 1), (1878, 3), (1877, 4)])
def test_ki_age(year, expected):
    assert global_ki_age(year) == expected

@pytest.mark.parametrize("year,expected", [(2021, 6), (2022, 5), (3317, 5), (3318, 4), (726, 6)])
def test_great_age(year, expected):
    assert global_great_age(year) == expected

def test_gates_land_on_earth_children():
    for g in range(2022 - 144 * 20, 2022 + 144 * 20, 144):
        assert global_great_year(g) in (2, 5, 8) and global_year(g) == 5
    for g in range(2022 - 1296 * 3, 2022 + 1296 * 3, 1296):
        assert global_ki_age(g) == 2 and global_great_year(g) == 8
    assert (gate_start(2026, "great_year"), gate_start(2026, "ki_age"), gate_start(2165, "ki_age"), gate_start(2021, "great_age")) == (2022, 2022, 2022, 726)

def test_stacks():
    g = global_stack(2026, 2026 * 12 + 8)
    assert g == {"great_age": 5, "ki_age": 2, "great_year": 8, "year": 1, "month": 9}
    assert personal_stack(5, g) == {"great_age": 5, "ki_age": 8, "great_year": 2, "year": 9, "month": 1}

def test_convergence_delegates():
    from convergence_ki import synodic_ki_for_year, synodic_gate_start
    assert synodic_ki_for_year(2022) == 8 and synodic_gate_start(2026) == 2022
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ki_levels.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ki_levels'`

- [ ] **Step 3: Implement `ki_levels.py` and delegate from `convergence_ki.py`**

In `convergence_ki.py` replace the bodies of `synodic_gate_start` and `synodic_ki_for_year` with calls to `ki_levels.gate_start(ki_year, "great_year")` and `ki_levels.global_great_year(ki_year)`, and set `SYNODIC_ANCHOR_YEAR`, `SYNODIC_ANCHOR_KI`, `SYNODIC_GATE_YEARS` from the `ki_levels` constants so existing imports keep working.

- [ ] **Step 4: Run tests to verify they pass, including the existing great-year fixtures**

Run: `.venv/bin/python -m pytest tests/test_ki_levels.py tests/test_great_year_fixtures.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ki_levels.py convergence_ki.py tests/test_ki_levels.py
git commit -m "Add ki_levels: Lo Shu arithmetic for every level, Ki Age and great age anchored at 2022"
```

---

### Task 3: ki_changes forms figures from full stacks

**Files:**
- Modify: `ki_changes.py` (module docstring lines 1-16, `KI_TO_TRIGRAM` lines 26-37, `_hexagram_from_ki` 65-92, `_changing_lines` 94-125, `get_ki_changes` 142-410, `_get_transformed_hex` 567-571, `format_ki_changes_full` 574-693, `format_ki_changes` 696-end)
- Test: `tests/test_ki_changes_hub.py`

**Interfaces:**
- Consumes: Task 1 `hexagram`, `hexagram_lines`, `moving_lines`, `resolve`, `HubUnresolvable`, `TRIGRAM_*`; Task 2 `global_stack`, `personal_stack`, `global_ki_age`, `global_great_age`, `gate_start`.
- Produces (new shape of `get_ki_changes(target_date, birth_date) -> dict`; existing keys keep their meaning):
  - `global.current` and `global.next`: keys `great_age, ki_age, synodic, year, month, day, hour` (synodic = great year, name kept for the tools).
  - `global.change_times`: as today plus `ki_age` and `great_age` strings `"Lichun <year> (next Ki Age gate)"`.
  - `level_changes[level]` for `LEVEL_NAMES = ["synodic","year","month","day","hour"]`: `{"current": {"ki","trigram","symbol","lines","inherited_from"}, "next": {...}, "changing_lines": [{"line","direction"}], "num_changes", "changes_at", "wu_xing"}` where `direction` is `"yin→yang"` or `"yang→yin"`. Current and next trigrams come from `resolve(stack_now, level)` and `resolve(stack_next, level)`.
  - `hexagrams[pair_key]` for pairs `synodic_year, year_month, month_day, day_hour`: the Task 1 `hexagram()` dict plus `"pair"`, `"wu_xing"`, `"transformed": {"hexagram": int, "lines": list[int]}` (the same lower level, the upper level advanced), `"changing": [{"line","direction"}]` (moving lines between `lines` and `transformed.lines`).
  - `personal`: same structure built from the personal stacks, or `None`.
  - New helper `next_stack(stack_now: dict, level: str, change_times: dict) -> dict`: copies `stack_now`, advances `level` by one (descending), and also advances every parent whose change instant equals this level's (synodic, ki_age, great_age advance together with `year` only when the next Lichun is their gate; nothing else coincides).
  - `KI_TO_TRIGRAM` loses key 5. `_hexagram_from_ki(stack, lower_level, upper_level)` and `_changing_lines(level, stack_now, stack_next)` are the new signatures; `_get_transformed_hex` is deleted.
  - `hub_level(name: str) -> str` maps `synodic → great_year`, else identity, for building hub stacks.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ki_changes_hub.py
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ki_changes import KI_TO_TRIGRAM, get_ki_changes, next_stack

BIRTH = "1986-05-01"

def test_five_is_not_kun():
    assert 5 not in KI_TO_TRIGRAM

def test_personal_five_inherits_up_the_personal_chain():
    d = get_ki_changes("2022-06-15", birth_date=BIRTH)
    p = d["personal"]
    assert p["current"]["year"] == 5 and p["current"]["synodic"] == 2
    hx = p["hexagrams"]["year_month"]
    assert hx["lower"]["trigram"] == "☷ Kun (inherited from great_year)"
    assert hx["inherited"] == [{"level": "year", "from": "great_year"}]
    assert d["global"]["current"]["ki_age"] == 2 and d["global"]["current"]["great_age"] == 5
    assert p["current"]["ki_age"] == 8

def test_day_five_over_month_is_pure():
    # Oct 22 2026: Chris personal month 1, personal day 5 (spec example)
    d = get_ki_changes("2026-10-22", birth_date=BIRTH)
    hx = d["personal"]["hexagrams"]["month_day"]
    assert d["personal"]["current"]["day"] == 5
    assert hx["hexagram"] == 29 and hx["transformed"]["hexagram"] == 47
    assert hx["changing"] == [{"line": 4, "direction": "yin→yang"}]

def test_next_stack_advances_parents_only_at_a_shared_gate():
    now = {"great_age": 5, "ki_age": 2, "great_year": 8, "year": 2, "month": 5, "day": 1, "hour": 9}
    times = {"year": "L2034", "synodic": "L2034", "ki_age": "L2166", "great_age": "L3318"}
    nxt = next_stack(now, "year", times)
    assert nxt["year"] == 1 and nxt["great_year"] == 7 and nxt["ki_age"] == 2
    assert next_stack(now, "day", times)["day"] == 9 and next_stack(now, "day", times)["month"] == 5

def test_year_change_at_a_gate_uses_the_new_great_year():
    d = get_ki_changes("2033-06-01")
    lc = d["level_changes"]["year"]
    assert d["global"]["current"]["synodic"] == 8 and d["global"]["next"]["synodic"] == 7
    assert lc["current"]["ki"] == 3 and lc["next"]["ki"] == 2

def test_level_change_lines_are_a_difference_of_resolved_trigrams():
    d = get_ki_changes("2026-10-22", birth_date=BIRTH)
    lc = d["personal"]["level_changes"]["day"]  # 5 (Kan, inherited) → 4 (Xun)
    assert lc["current"]["inherited_from"] == "month" and lc["next"]["inherited_from"] is None
    assert lc["changing_lines"] == [{"line": 1, "direction": "yang→yin"}, {"line": 3, "direction": "yin→yang"}]
```

Note for the implementer: lines 1 and 3 above follow from Kan 010 → Xun 011? No: Kan is (0,1,0) and Xun is (0,1,1), so only line 3 changes. Fix the last assertion to `[{"line": 3, "direction": "yin→yang"}]` before running; the test is written to be checked against the tables, not trusted.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ki_changes_hub.py -v`
Expected: FAIL (`ImportError: cannot import name 'next_stack'` and `5 in KI_TO_TRIGRAM`)

- [ ] **Step 3: Rewrite the formation code in `ki_changes.py`**

Build `stack_now` from `get_convergence_ki` values plus `global_ki_age`/`global_great_age` of the current Ki year, keyed by hub level names; the personal stack via `personal_stack(natal, stack_now)`. Compute `stack_next` per level with `next_stack`. Form every pair with `hexagram()`; the transformed figure uses `next_stack(stack_now, upper_level, change_times)`. Replace the `KI_TO_TRIGRAM[...]["element"]` Wu Xing lookups with `TRIGRAM_ELEMENT[resolved.source_ki]`. Rewrite `format_ki_changes_full` and `format_ki_changes` to read `lines`, `transformed`, `changing` and `inherited` from the dicts instead of recomputing; the line diagram and "Changing lines:" text keep their shape, and a trigram line gains ` (inherited from <level>)` when `inherited_from` is set. Update the module docstring to state the inheritance rule. Wrap `HubUnresolvable` at the top of `get_ki_changes` into a returned dict `{"error": str(e)}`.

- [ ] **Step 4: Run tests to verify they pass, plus the existing Ki suites**

Run: `.venv/bin/python -m pytest tests/test_ki_changes_hub.py tests/test_ki_fixtures.py tests/test_ki_continuity.py tests/test_great_year_fixtures.py tests/test_hexagram_five.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ki_changes.py tests/test_ki_changes_hub.py
git commit -m "Ki changes: form every figure from the full stack with hub inheritance"
```

---

### Task 4: server tools consume the new Ki changes shape

**Files:**
- Modify: `stella_server.py:5426-5506` (`get_ki_change_schedule`), `stella_server.py:5508-5696` (`_ki_change_single_level`)
- Test: `tests/test_ki_change_tools.py`

**Interfaces:**
- Consumes: Task 3 dict shape; Task 1 `resolve`, `moving_lines`, `hexagram_lines`, `TRIGRAM_SYMBOL`, `TRIGRAM_PINYIN`; Task 3 `next_stack`, `hub_level`.
- Produces: no new interfaces. Output text keeps its current layout. In `get_ki_change_schedule`, each step forms its lines by resolving the tracked level against the current parents (`stack_now` with only the tracked level stepped), and prints `Ki 5 ☲ Li (inherits month)` for a 5 step. Both tools return the `error` string when `get_ki_changes` returns `{"error": ...}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ki_change_tools.py
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stella_server

BIRTH = "1986-05-01"

def test_single_level_prints_inherited_tag(monkeypatch):
    import ki_changes
    real = ki_changes.get_ki_changes
    monkeypatch.setattr(ki_changes, "get_ki_changes", lambda **kw: real(target_date="2026-10-22", **kw))
    out = asyncio.run(stella_server.ki_change_day(birth_date=BIRTH))
    assert "Hexagram 29" in out or "Hex 29" in out
    assert "inherited from month" in out
    assert "Kun" not in out.split("── PERSONAL ──")[1]

def test_schedule_steps_through_five_with_inheritance(monkeypatch):
    import ki_changes
    real = ki_changes.get_ki_changes
    monkeypatch.setattr(ki_changes, "get_ki_changes", lambda **kw: real(target_date="2026-10-20", **kw))
    out = asyncio.run(stella_server.get_ki_change_schedule(birth_date=BIRTH, level="day", count=9))
    assert "Ki 5" in out and "inherits month" in out
    assert "☷" not in out.split("Ki 5")[1].split("\n")[0]

def test_tools_surface_hub_error(monkeypatch):
    import ki_changes
    monkeypatch.setattr(ki_changes, "get_ki_changes", lambda **kw: {"error": "day is 5 and every parent above it is 5"})
    out = asyncio.run(stella_server.ki_change_day(birth_date=BIRTH))
    assert out.startswith("Ki stack unresolvable:")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ki_change_tools.py -v`
Expected: FAIL (`KeyError: 5` or missing "inherited from" text)

- [ ] **Step 3: Rewire the two tools**

In `_ki_change_single_level`, delete every `KI_TO_TRIGRAM[...]` lookup and the local line/transform recomputation; read `hx["lines"]`, `hx["transformed"]`, `hx["changing"]`, `hx["upper"]["trigram"]`, `hx["lower"]["trigram"]`. In `get_ki_change_schedule`, build the hub stack from `data["global"]["current"]` (and the personal stack when `birth_date`), step the tracked level each iteration, and resolve with `resolve()`; show `(inherits <level>)` when `inherited_from` is set. Both tools: `if "error" in data: return f"Ki stack unresolvable: {data['error']}"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ki_change_tools.py tests/test_ki_changes_hub.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add stella_server.py tests/test_ki_change_tools.py
git commit -m "Ki change tools read resolved figures; schedule steps through 5 by inheritance"
```

---

### Task 5: daily cascade gains the upper levels and resolved trigrams

**Files:**
- Modify: `ki.py:302-430` (`calculate_daily_ki`), `stella_server.py:548-625` (`get_daily_ki`)
- Test: `tests/test_daily_ki_hub.py`

**Interfaces:**
- Consumes: Task 1 `resolve`, `TRIGRAM_NAME`; Task 2 `global_great_year`, `global_ki_age`, `global_great_age`, `personal`.
- Produces: `calculate_daily_ki(...)["global"]` and `["personal"]` gain keys `great_age`, `ki_age`, `great_year`, each `{"ki": int, "info": KI_TRIGRAMS[ki]}`; every level dict gains `"hub": {"trigram": ResolvedTrigram.name, "inherited_from": Optional[str]}`. `sequences.global` / `sequences.personal` become seven dotted digits `great_age.ki_age.great_year.year.month.day.hour`. `get_daily_ki` prints the three new levels above Year in both sections and appends ` → inherits <trigram> from <level>` on any line whose Ki is 5.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_ki_hub.py
import asyncio, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ki import calculate_daily_ki
import stella_server

def test_stack_has_upper_levels_and_hub_tags():
    r = calculate_daily_ki(date(1986, 5, 1), date(2026, 10, 22))
    g, p = r["global"], r["personal"]
    assert (g["great_age"]["ki"], g["ki_age"]["ki"], g["great_year"]["ki"], g["year"]["ki"]) == (5, 2, 8, 1)
    assert (p["great_year"]["ki"], p["year"]["ki"], p["month"]["ki"], p["day"]["ki"]) == (2, 9, 1, 5)
    assert p["day"]["hub"] == {"trigram": "☵ Kan (inherited from month)", "inherited_from": "month"}
    assert p["month"]["hub"]["inherited_from"] is None
    assert r["sequences"]["personal"].count(".") == 6

def test_tool_prints_inheritance():
    out = asyncio.run(stella_server.get_daily_ki("1986-05-01", "2026-10-22"))
    assert "**Ki Age:**" in out and "**Great Age:**" in out
    assert "inherits ☵ Kan from month" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_daily_ki_hub.py -v`
Expected: FAIL with `KeyError: 'great_age'`

- [ ] **Step 3: Implement**

In `calculate_daily_ki`, after `year_ki` is known compute the three upper global levels from `ki_year` via `ki_levels`, derive personal ones with `personal(natal_year_ki, g)`, then build a hub stack per chain and attach `hub` to each level dict with `resolve`. Keep `KI_TRIGRAMS[5]` (☯ Tai Chi) for the reading path. Update `get_daily_ki` formatting.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_daily_ki_hub.py tests/test_ki_fixtures.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ki.py stella_server.py tests/test_daily_ki_hub.py
git commit -m "Daily Ki: great year, Ki Age and great age in the stack; 5 shows its inherited trigram"
```

---

### Task 6: octave_math port

**Files:**
- Create: `octave_math.py`
- Test: `tests/test_octave_math.py`

**Interfaces:**
- Consumes: Task 1 `hexagram_lines`, `moving_lines`, `king_wen`, `resolve`; Task 2 `ki`, `personal`, `global_year`, `global_month`, `global_great_year`, `global_ki_age`, `global_great_age`; `ki_calendar.ki_year_of`, `ki_month_of`, `ki_month_span`, `ki_month_label`.
- Produces (port of `lib/report.ts` + `lib/summary.ts`; names are Python snake_case, JSON keys stay the app's camelCase so `tests/test_octave.py` assertions hold):
  - `HEX_NAMES: list[str]` (index = King Wen number; copy of the app's `NAMES`).
  - `ECHO = {1: 4, 4: 1, 2: 8, 8: 2, 5: 7, 7: 5}`, `rim_role(k) -> str`, `rim_label(k, partners: Optional[list[str]]) -> str`, `rim_text(k, partner_year)`, `PAIR_TEXT`, `SHOCK_TEXT`, `ki_name(k)`, `ki_image(k)` (5 → "Centre"/"centre").
  - `natal(birth: date) -> dict` keys `year, month, third, kiYear, monthAbs`; `natal_label(n) -> "5 · 9 · 1"`.
  - `octaves(natal_year: int, birth_ki_year: int, until_age: int = 90) -> list[dict]` keys `index, start, end, enteredAt?, greatYears: [{from, global, personal}]`; `octave_label`, `great_year_label`.
  - `figure(stack: dict, upper: str, lower: str) -> dict` keys `number, name, lines (str of 6 chars), upperKi, lowerKi, upper, lower, inherited: list[{level, from}]`; the personal stack passed in always carries `great_age, ki_age, great_year, year` and `month` when forming a month. Never returns None.
  - `change(primary: dict, transformed: dict) -> dict` keys `primary, transformed, moving: list[int], lowerMoved: bool`.
  - `year_figure(natal_year, ki_year) -> dict`, `month_figure(natal_year, ki_year, index) -> dict`.
  - `build_report(birth: date, octave_index: Optional[int], today: date, name: Optional[str]) -> dict`: the app's `summarize(buildReport(...))` output exactly, with every `figure` object carrying `inherited`, and month `figure` strings never "no figure (5 over 5)".
  - `_fig(f) -> dict` as in `summary.ts` (`number, name, upper, lower, lines`) plus `inherited`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_octave_math.py
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from octave_math import (build_report, change, great_year_label, natal, natal_label,
                         octave_label, octaves, year_figure, month_figure)

N = 5

def test_natal_and_octaves():
    n = natal(date(1986, 5, 1))
    assert (n["year"], n["month"], n["third"], n["kiYear"]) == (5, 9, 1, 1986)
    assert natal_label(n) == "5 · 9 · 1"
    lst = octaves(N, 1986)
    assert [o["start"] for o in lst[:7]] == [1982, 1991, 2000, 2009, 2018, 2027, 2036]
    assert lst[0]["index"] == 0 and lst[0]["enteredAt"] == 5
    assert octave_label(lst[4]) == "Octave 4 · Feb 2018 → Jan 2027"
    assert great_year_label(lst[4]) == "great year 1 → 2 in 2022"
    assert great_year_label(lst[5]) == "great year 2 → 3 in 2034"

def test_year_figures_match_the_app():
    want = {2018: 29, 2019: 7, 2020: 40, 2021: 59, 2022: 2, 2023: 12, 2024: 45, 2025: 23, 2026: 35, 2027: 8}
    for y, n in want.items():
        assert year_figure(N, y)["number"] == n, y
    assert year_figure(N, 2022)["inherited"] == [{"level": "year", "from": "great_year"}]

def test_month_figures():
    assert month_figure(N, 2026, 8)["number"] == 63   # Oct 2026 = 9.1
    assert month_figure(N, 2026, 7)["number"] == 30   # Sep 2026 = 9.9
    assert month_figure(N, 2018, 0)["number"] == 29   # Feb 2018 = 1.5
    aug22 = month_figure(N, 2022, 6)                  # Aug 2022 = 5.5 → both inherit Kun
    assert aug22["number"] == 2 and aug22["inherited"] == [{"level": "year", "from": "great_year"}, {"level": "month", "from": "great_year"}]
    mar22 = month_figure(N, 2022, 1)                  # Mar 2022 = 5.9 → Li over inherited Kun = 35
    assert mar22["number"] == 35

def test_echo_pairs_of_octave_4():
    pair = lambda a, b: change(year_figure(N, a), year_figure(N, b))
    assert (pair(2018, 2021)["moving"], pair(2018, 2021)["lowerMoved"], pair(2018, 2021)["transformed"]["number"]) == ([6], False, 59)
    assert (pair(2019, 2025)["moving"], pair(2019, 2025)["lowerMoved"]) == ([2, 6], True)
    assert (pair(2022, 2024)["moving"], pair(2022, 2024)["lowerMoved"]) == ([4, 5], False)

def test_report_matches_the_app_fixture():
    r = build_report(date(1986, 5, 1), None, date(2026, 10, 16), "Chris")
    assert r["natal"]["triple"] == "5 · 9 · 1"
    assert (r["today"]["kiMonth"], r["today"]["personal"], r["today"]["greatYear"]) == ("Oct 2026", "9.1", 2)
    assert r["today"]["monthFigure"]["number"] == 63 and r["today"]["yearFigure"]["number"] == 35
    assert r["today"]["monthPosition"] == "1 ↔ 4 · with Apr 2026, Jan 2027"
    assert r["today"]["nextGreatYearShift"] == {"kiYear": 2034, "from": 2, "to": 3}
    assert r["octave"] == {"index": 4, "label": "Octave 4 · Feb 2018 → Jan 2027", "greatYear": "great year 1 → 2 in 2022", "enteredAt": None, "containsToday": True}
    assert len(r["years"]) == 9 and r["years"][0]["kiYear"] == 2018
    assert [p["movingLines"] for p in r["echoPairs"]] == [[6], [2, 6], [4, 5]]
    assert [(p["years"], p["primary"]["number"], p["transformed"]["number"]) for p in r["echoPairs"]] == [([2018, 2021], 29, 59), ([2019, 2025], 7, 23), ([2022, 2024], 2, 45)]
    assert r["nextCycle"]["label"] == "Feb 2027" and r["nextCycle"]["personal"] == "1.5" and r["nextCycle"]["yearFigure"]["number"] == 8
    sep = next(m for y in r["years"] for m in y["months"] if m["label"] == "Sep 2026")
    assert sep["position"] == "Source and arrival · 9"
    assert all("no figure" not in m["figure"] for y in r["years"] for m in y["months"])

def test_birth_octave_marks_months_before_birth():
    r = build_report(date(1986, 5, 1), 0, date(2026, 10, 16), None)
    assert r["octave"]["index"] == 0 and r["octave"]["enteredAt"] == 5
    months = {m["label"]: m for y in r["years"] for m in y["months"]}
    assert months["Mar 1986"].get("beforeBirth") is True and not months["Apr 1986"].get("beforeBirth")
```

Note: the app's summary omits `beforeBirth` on months; add it to the month summary (`"beforeBirth": True` only when true, like `now`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave_math.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'octave_math'`

- [ ] **Step 3: Implement `octave_math.py`**

Port `lib/ki/{natal,octaves}.ts`, `lib/enneagram/{rim,text}.ts`, `lib/iching/form.ts` (`form` becomes `figure(stack, upper, lower)` through the hub), `lib/report.ts` and `lib/summary.ts`, in that order, one function per TypeScript export. Month boundaries and labels come from `ki_calendar`; `monthAbs = ki_year * 12 + index`. The stack for a year figure is `personal_stack(natal_year, global_stack(ki_year))`; for a month figure add `month`. `lowerMoved` is true when any moving line is 1–3.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave_math.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave_math.py tests/test_octave_math.py
git commit -m "Port the Nine-Year Spiral octave math into Stella with hub inheritance"
```

---

### Task 7: octave tools serve the port and read the Gnostic text locally

**Files:**
- Create: `data/gnostic.json` (copy of `/Volumes/Shirahoshi/HermesNode/octave/lib/iching/gnostic.json`, 2.1 MB)
- Modify: `octave.py` (module docstring 1-11, `FRAMEWORK` lines 60-69 "The figures", `_get`/`octave_report`/`octave_reading` 83-137, `hermes_skill` 139-157, `register_octave` 159-204), `api_bridge/Dockerfile:29` (add `COPY data/gnostic.json ./data/gnostic.json`)
- Modify: `tests/test_octave.py`

**Interfaces:**
- Consumes: Task 6 `build_report`.
- Produces:
  - `octave_report(birth_date: str, octave=None, target_date=None, tz=None, name=None, include_months=False) -> dict`: same signature; computes via `build_report`; `tz` other than `None`/`"America/New_York"` raises `ValueError("Only America/New_York boundaries are supported")`, which `get_octave` returns as text.
  - `GNOSTIC_JSON = os.environ.get("GNOSTIC_JSON") or <repo>/data/gnostic.json`; `load_gnostic() -> dict[int, dict]` cached; `octave_reading(hexagram, lines, full)` reads from it. `OCTAVE_URL` and `httpx` are removed.
  - `FRAMEWORK` "The figures" bullet becomes: "5 is the centre and has no trigram: it inherits the trigram of the nearest level above it that is not 5 (month from year, year from great year, great year from Ki Age). A 5 over 5 is the parent's trigram doubled. The output names what was inherited." Add the Ki Age (144 years) and great age (1,296 years) lines to "The clock". `hermes_skill` drops the port-3333 sentence.

- [ ] **Step 1: Rewrite `tests/test_octave.py` as the failing test**

```python
"""Octave tools, computed in Stella (no app required).

Run: .venv/bin/python -m pytest tests/test_octave.py
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import octave

def test_report():
    r = octave.octave_report("1986-05-01", target_date="2026-10-16")
    assert r["natal"]["triple"] == "5 · 9 · 1"
    assert (r["today"]["kiMonth"], r["today"]["personal"], r["today"]["greatYear"]) == ("Oct 2026", "9.1", 2)
    assert r["octave"]["greatYear"] == "great year 1 → 2 in 2022"
    assert [p["movingLines"] for p in r["echoPairs"]] == [[6], [2, 6], [4, 5]]
    assert sum("months" in y for y in r["years"]) == 1

def test_reading():
    t = octave.octave_reading(29, [6], full=False)
    assert t.startswith("# 29 ") and "## Line 6" in t
    assert octave.octave_reading(99).startswith("No reading for hexagram 99")

def test_no_http():
    assert not hasattr(octave, "OCTAVE_URL")
    assert "inherits the trigram" in octave.FRAMEWORK and "doubling it" not in octave.FRAMEWORK

def test_tool_rejects_other_tz():
    import stella_server
    out = asyncio.run(stella_server.get_octave("1986-05-01", tz="Europe/London"))
    assert "America/New_York" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_octave.py -v`
Expected: FAIL (`test_no_http` and `test_tool_rejects_other_tz`; `test_report` fails or hangs if the app is down)

- [ ] **Step 3: Implement**

```bash
cp /Volumes/Shirahoshi/HermesNode/octave/lib/iching/gnostic.json data/gnostic.json
```

Then rewrite `octave.py` per Interfaces. `get_octave`'s docstring keeps its wording minus "Uses the corrected Ki math" → "Computed in Stella: continuous months, 12-year great-year gates, hub inheritance for 5." Add the Dockerfile `COPY` line.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_octave.py tests/test_octave_math.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add octave.py data/gnostic.json api_bridge/Dockerfile tests/test_octave.py
git commit -m "Octave tools compute in Stella and read the Gnostic text locally"
```

---

### Task 8: whole-suite verification and framework docs

**Files:**
- Modify: `docs/KI_REFERENCE.md` (append a "Timekeeping stack and the 5 rule" section: the seven levels with periods and anchors, the inheritance rule, and the sentence that reading tools keep the three-number doubling rule)

- [ ] **Step 1: Run the full suite**

Run: `.venv/bin/python -m pytest tests -v --ignore=tests/test_stella_http.py`
Expected: all PASS, including `tests/test_hexagram_five.py` unchanged.

- [ ] **Step 2: Smoke the tools end to end**

Run:
```bash
.venv/bin/python -c "
import asyncio, stella_server as s
print(asyncio.run(s.ki_change_day(birth_date='1986-05-01'))[:1200])
print(asyncio.run(s.get_octave('1986-05-01', target_date='2026-10-22'))[:800])
print(asyncio.run(s.get_daily_ki('1986-05-01', '2026-10-22')))"
```
Expected: no traceback; the daily output shows Ki Age and Great Age lines; the day line for 2026-10-22 shows `inherits ☵ Kan from month`.

- [ ] **Step 3: Write the reference section and commit**

```bash
git add docs/KI_REFERENCE.md docs/superpowers
git commit -m "Docs: the timekeeping stack, Ki Age and great age, and how 5 inherits"
```

---

## Not in this plan

- What a 5 in the first position of a natal triple means (e.g. 5.9.1) is a knowledge-graph question, to be researched with `knowledge_search`, not coded.
- The Nine-Year Spiral app keeps its own five rule; aligning it is a separate change in that repo.
