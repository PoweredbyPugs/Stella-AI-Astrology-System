# Stella Changelog

## 2026.11.11 — BaZi: traditional Four Pillars on Stella

### `bazi.py`, `bazi_tables.py`, `bazi_render.py` (new)
- Zi Ping Four Pillars computed locally: year at the exact Lichun, months at the twelve jie (shared with the Ki calendar, and that is all that is shared), day by sexagenary count, hour by double-hour. Five Tigers and Five Rats rules for the month and hour stems.
- True solar time by default: the birth clock is corrected for longitude and the equation of time before the day boundary and hour are read, as Chinese calculators do. Day boundary 23:00 by default, midnight (early/late Zi) as the alternative. Both are parameters and both are printed with every result.
- Reading data in traditional vocabulary: hidden stems, Ten Gods for every visible and hidden stem, Nayin, twelve life stages (classical yin-backward table), void, Day Master strength as season + roots + support with the method printed, structure by Ziping Zhenquan with special structures flagged as candidates, element tallies and climate, every combination/clash/harm/punishment/destruction located by pillar, and a core set of symbolic stars that name the pillar they were cast from.
- Luck pillars with exact start age (days to the jie at three days per year) and direction by gender and year polarity; time pillars at any instant read against a natal chart and its current luck pillar.
- Both stored-chart shapes load; a chart without gender omits the luck pillars and says why; a chart without coordinates falls back to clock time with a warning on the first line.
- Validated against buyiju.com for three charts (pillars, Ten God rows, Nayin) and against published day anchors (1900-01-01 甲戌, 2000-01-01 戊午, Mao Zedong's chart). Tests: `tests/test_bazi_*.py`.

### Tools
- `get_bazi`, `get_bazi_luck_pillars`, `get_bazi_time_pillars` (92 tools). Reference: `docs/BAZI_REFERENCE.md`.

## 2026.10.25 — The stack reads the Sun: degree-days, degree-hours, precession-anchored great age

### `ki_solar.py` (new)
- Day and hour are no longer clock units. A day is one degree of the Sun past Lichun (30 per month, 23.5–25.2 hours long), an hour is five arcminutes (12 per day). Every level is now twelve (or thirty) of the one above with remainder 3, so every level opens on an Earth number and the running count is the lock. Nothing turns at midnight.
- Anchors: every Lichun opens day 8 (month 2 opened day 8; 360 ≡ 0), and the hour opening is `3·day + 8` so day 8 opens hour 5. Continuity forces the slope; the constant is doctrine.
- `solar_stack(jd)` gives all seven numbers, where the Sun is, and when the current degree-day and degree-hour began and end; `next_change_jd` and `stack_after` give the exact instants of coming changes at any level.

### Anchors above the year (`ki_levels.py`)
- A great age is 12 Ki Ages, 1,728 years, one fifteenth of the 25,920-year precession cycle, i.e. 24° of the vernal point against the stars. Nine Ki Ages were one cycle of the numbers, not the parent period.
- The seam is astronomical: the vernal point reached 24° past the Lahiri sidereal zero (285 CE) in 2010, and the gate is the Lichun before the crossing, as a great year's gate is the Lichun before Jupiter's perihelion. Lichun 2010 opened great age 8, Ki Age 5 and great year 2 together (year 8 there): the full staircase 8 · 5 · 2 · 8 · 2 · 8 · 5.
- Consequence: the great year that opened at Lichun 2022 is 1, not 8 (2034 opens 9). The old 2022 anchors had assumed all three seams coincided there.

### Fixed
- `get_daily_ki`, `ki_change_hour` and the other change tools never received the time of day: the cascade was built at midnight and the change tools truncated the timestamp to a date, so the hour Ki was always the day's first block. All tools now take an ISO datetime; a bare date is read at local noon.
- `convergence_ki` used a literal "day − 3" for the hour opening, which matched the table only when the day Ki was 5, and used Chinese zodiac double-hours starting at 23:00. Both removed.
- `get_synodic_gate` read the Ki year by calendar date; it now turns at the instant of Lichun like everything else.
- `get_ki_change_schedule` stepped hours by a fixed two clock hours and days by calendar date; it now steps to the Sun's next boundary.

### Tests
- `tests/test_ki_solar.py` (new): the Lichun 2010 staircase, Lichun 2022, today's reading, twelve hours descending by one through a degree-day, midnight not a boundary, the day count flowing through a month seam and through Lichun, next-change instants, the great-year numbers after the 2010 seam.
- Fixture tests updated to the new anchors; boundary-day rows now carry explicit times because the stack turns at the instant. The octave app's `lib/ki/kimonths.ts` still carries the old great-year anchor and will disagree with Stella on great years until it is updated.

## 2026.10.21 — WebSocket bridge for Obsidian

### `stella_ws.py` (new)
- Bulbasaur Chat's "http" transport is a bare WebSocket of stdio-style JSON-RPC frames, with no headers and no OAuth, so it could reach Stella only by spawning `ssh` to the mini. That broke when Remote Login was switched off.
- The bridge spawns one `stella_server.py` child per WebSocket connection, maps frames to stdin lines and back, and terminates the child when the socket closes. Line limit raised to 16 MiB: a `tools/list` reply already passes asyncio's 64 KiB default.
- Auth is a shared `STELLA_WS_TOKEN` carried as `?token=` (the plugin cannot send headers), compared constant-time, 401 before any child starts. Bound to loopback; `tailscale serve --https=8812` publishes it tailnet-only, never Funnel.
- launchd `com.poweredbypugs.stella-ws` via `scripts/run-stella-ws.sh`, under `.venv-http`. Eight tests in `tests/test_stella_ws.py` against a fake stdio child.
- The claude.ai endpoint (`stella_http.py`) and the Hermes stdio path are untouched.

## 2026.10.20 — Hub inheritance, Ki Age and great age, octave in Stella

### The 5 rule (`hub_inheritance.py`, new)
- Ki 5 has no trigram. In the timekeeping stack it inherits the trigram of the nearest level above it that is not 5, walking up as far as needed (hour → day → month → year → great year → Ki Age → great age). If the whole chain is 5, `HubUnresolvable` is raised instead of guessing.
- The old mapping 5 → ☷ Kun in `ki_changes.py` is removed. It was the great year 2 leaking into the hub.
- A 5 over 5 is the parent's trigram doubled. Every figure that inherited carries `"inherited": [{"level": …, "from": …}]` and the trigram name reads `☵ Kan (inherited from month)`.
- Moving lines are always the line-by-line difference between two six-line figures. No fixed tables anywhere. 1↔4 and 2↔8 stay line 6 under any parent; 5↔7 varies with the parent (lines 4–5 under Kun, nothing under Dui).
- The three-number reading path (`ki_reading.py`, `get_ki`, `get_ki_cycle`, `get_ki_reading`, `get_ki_transition`) is unchanged: a reading has no hierarchy, so a 5 there keeps taking the other numbers' character.

### Levels above the great year (`ki_levels.py`, new)
- Ki Age = 12 great years = 144 years; great age = 9 Ki Ages = 1,296 years. Each descends 1 per period.
- Anchors: Lichun 2022 opens great year 8, Ki Age 2, great age 5. Read upward at that instant the stack is 5 · 2 · 8 · 5 · 2, each level the next Earth number in the cycle 2 → 5 → 8 → 2. The two other lattices the arithmetic allows (Ki Age opening 1914 or 1950) are documented beside the constants.
- One module now holds the arithmetic for every level; `convergence_ki.py`'s synodic functions delegate to it.

### Ki Changes (`ki_changes.py`, rewritten formation)
- Every figure is formed from the full stack, personal figures from the personal stack only. Personal numbers rise by one where global numbers fall by one.
- Single-level changing lines compare the resolved trigram now against the resolved trigram after the change. When a parent turns at or before the child (month and year together at Lichun, the day at midnight before the 01:00 hour, a gate on that Lichun), the parent is advanced too.
- `get_ki_changes` output gains `ki_age` and `great_age` in the stack, and `lines`, `transformed`, `changing` and `inherited` on every hexagram. Returns `{"error": …}` instead of raising.
- `get_ki_change_schedule` reads its parents from the calendar at each step; a 5 along the way shows what it inherits.
- `get_daily_ki` shows all seven levels and names what a 5 inherits.

### Octave (`octave_math.py`, new; `octave.py`)
- The Nine-Year Spiral library is ported to Python. `get_octave` computes in Stella; no HTTP call to the app. Same JSON shape, plus `inherited` on every figure. A 5 year or month forms over the level above it, so there is no "no figure (5 over 5)" case.
- `get_octave_reading` reads The Gnostic Book of Changes from `data/gnostic.json` (`GNOSTIC_JSON` overrides the path). The API container copies it in.

### Tests
- New: `tests/test_hub_inheritance.py`, `test_ki_levels.py`, `test_ki_changes_hub.py`, `test_ki_change_tools.py`, `test_daily_ki_hub.py`, `test_octave_math.py`. `tests/test_octave.py` runs without the app. 155 tests pass.

### Docs
- `docs/KI_REFERENCE.md` gains the timekeeping stack and the 5 rule. Spec and plan under `docs/superpowers/`.

---

## 2026-03-27 — Ki Changes (Mercury's Reading)

### New Module: `ki_changes.py`
- **Ki transitions as I Ching hexagrams** — every Ki level change produces changing lines (trigram transitions), and every pair of adjacent levels forms a hexagram (lower=stable, upper=changing)
- Ki numbers mapped to Later Heaven trigrams: 1=Kan☵, 2=Kun☷, 3=Zhen☳, 4=Xun☴, 5=Kun☷, 6=Qian☰, 7=Dui☱, 8=Gen☶, 9=Li☲
- Wu Xing phase relationships computed for each transition
- Gnostic Book of Changes lookup from Neo4j for hexagram interpretations
- Core insight: 64 hexagrams = Mercury's 8×8 magic square. Mercury reads the delta.

### New Tools (7)
- `get_ki_changes(target_date?, birth_date?, include_gnostic?)` — Full Ki changes at all 5 levels with hexagrams
- `get_ki_change_schedule(birth_date?, level?, count?)` — Next N changes at a specific level
- `ki_change_hour(birth_date?, include_gnostic?)` — Hour-level changes (~2h cycle)
- `ki_change_day(birth_date?, include_gnostic?)` — Day-level changes (midnight)
- `ki_change_month(birth_date?, include_gnostic?)` — Month-level changes (Sun crosses 30° boundary)
- `ki_change_year(birth_date?, include_gnostic?)` — Year-level changes (Lichun ~Feb 4)
- `ki_change_global(birth_date?, include_gnostic?)` — Synodic-level changes (~12yr Jupiter cycle)

### Research Context
- Mercury's magic square: 8×8, 64 cells, constant 260 (Tiriel), total 2080 (Taphthartharath)
- 81 - 64 = 17 = Mercury's Vimshottari dasha period
- Agrippa: Mercury's square "conduceth to memory, understanding, and divination, and to the understanding of occult things by dreams"
- Book of Thoth: The Magus (Atu I), Intelligence of Transparency, the ape that distorts the Word
- Total tool count: 89

---

## 2026-03-26 — Dasha & Timing Stack + Ki Fixes

### New Module: `dasha.py`
- **Vimshottari Dasha** — 5-level computation (maha→prana) from natal Moon nakshatra
- **Correct lord sequence:** Ke, Ve, Su, Mo, Ma, Ra, Ju, Sa, Me (NOT Ke, Su, Mo, Ma, Ra, Ju, Sa, Me, Ve)
- **Nakshatra transit** — live Moon position with lord, pada (Dharma/Artha/Kama/Moksha), entry/exit times
- **Planetary glyphs:** ☋♀☉☽♂☊♃♄☿ on all dasha output

### New Tools (3)
- `get_timing_stack(name)` — Full stack: Dasha (5) + ZR Spirit/Fortune (L1-L5) + Nakshatra transit + Ki (5) + resonance detection
- `get_dasha_periods(name)` — Dasha only (5 levels with dates)
- `get_nakshatra_transit()` — Live Moon nakshatra/pada

### Bug Fixes in `convergence_ki.py`
- **FIXED: Month start groups were rotated.** Was `{1:5, 2:8, 3:2}`, should be `{1:8, 2:5, 3:2}`. Caused personal month to compute wrong (e.g., 6 instead of 3).
- **FIXED: Day Ki used Moon socket crossings.** Replaced with solar day cascade (-3 from month, descends 1/day from Lichun). Moon dropped as structural per March 6 definitive architecture.
- **FIXED: Hour Ki used ascendant gates.** Replaced with -3 cascade from day Ki, 12 double-hours/day.
- **ADDED: Synodic Ki (Great Year)** as 5th level above Year. Jupiter perihelion cycle (~11.86yr), pulled from `get_synodic_gate()`.
- **FIXED: Variable name collision** — `mki` was used for both month Ki and minute Ki, causing month to be overwritten.
- **Removed:** Moon socket crossing code for day Ki, ascendant gate scanning for hour Ki, minute Ki subdivision (not a primary level).

### Ki Architecture (5 levels, definitive)
```
Synodic  — Jupiter perihelion gate (~11.86yr), 9 gates = ~108 years
Year     — Sun orbit, Lichun to Lichun (~365 days)
Month    — Sun crosses 15° of each sign (~30 days)
Day      — Solar day, descends 1/day, 365 mod 9 = 5
Hour     — Double-hour (shíchén), 12/day, shifts 3/day
```

---

## 2026-02-02 — The Three-Axis Report System

### Major Features

**3-Axis Chart Reading System**
The `chart_reading` tool now operates on three independent axes:
- **Type** (the medium): `technical` | `narrative` | `poem`
- **Framework** (the lens): `psychological` | `deterministic` | `hellenistic` | `stoic` | `mythological`
- **Size** (the depth): `xs` | `s` | `m` | `l` | `xl`

75 possible combinations from a single chart. Each axis is independently configurable.

**Derivative Houses (Pelletier System)**
- `compute_derivative_houses(chart_data)` computes house-to-house relationships for every planet
- Formula: `(origin - target) % 12 + 1` (clockwise/Pelletier method)
- Asymmetric pairs always sum to 14
- Grouped by aspect geometry (conjunction, semisextile, sextile, square, trine, quincunx, opposition)
- Key connections identified: dignified planets to angular houses
- Pelletier's interpretations queried from ChromaDB for each key connection
- Integrated into `full_chart_computation()` and `_gather_knowledge_for_chart()`

**Dignity-Weighted Narrative Priority**
- Automatically analyzes chart ruler condition vs. strongest planets by dignity score
- Generates priority instructions injected into every reading
- Weak/peregrine chart ruler → ASC archetype treated as CONDITIONAL
- Strongest planet by dignity score gets most narrative weight
- Debilitated planets' shadows named directly (not softened)
- Central narrative tension = gap between ASC mask and dominant planet's reality

**Legacy Chart Format Normalization**
- `_normalize_legacy_chart()` converts old format (dict-keyed planets, string angles) to Helios format
- Handles charts imported before Helios integration
- Infers sect from Sun house position when not present

### New Constants
- `REPORT_TYPES` — 3 report types with full LLM instructions
- `FRAMEWORKS` — 5 interpretive frameworks (expanded from 2 `PERSPECTIVES`)
- `DERIVATIVE_HOUSES` — meanings for all 12 derivative positions
- `ASPECT_GEOMETRY` — 7 geometric relationship types
- `ANGULAR_HOUSES` — {1, 4, 7, 10}
- `PERSPECTIVES` maintained as legacy alias → `FRAMEWORKS`

### New Files
- `elections/2026-elections-brennan-schaim.pdf` — Brennan & Schaim electional report
- `elections/2026-elections-chart-data.pdf` — Chart data for elections
- `elections/2026-elections-summary.md` — Quick reference: all 24 elections + planetary events
- `reports/robin-natal-reading.md` — Robin's natal chart (first reading from new system)
- `reports/lisa-natal-reading.md` — Lisa's natal (narrative, psychological, M)
- `reports/lisa-natal-reading-v2.md` — Lisa's natal (calibrated dignity weighting)
- `reports/lisa-xl-technical.md` — Lisa's natal (technical, psychological, XL)

### Calibration Lessons
- Dignity score should drive narrative weight more than ASC archetype
- A peregrine/debilitated chart ruler delivers its sign's qualities CONDITIONALLY
- Leo ASC + peregrine Sun + Moon domicile 12H = warmth only when emotionally settled or externally recognized
- Mercury detriment = "jumps to conclusions," not "broad thinking" — name shadows directly
- Feedback from real people who know the chart subject is the ultimate calibration tool

### Future Roadmap (parked)
- **Evolutionary Astrology framework** — Pluto polarity point, nodal story, skipped steps
- **Archetypal Astrology framework** — Tarnas, outer planet cycle tracking
- **Framework-specific computation adjuncts** — extra data computed per framework
- **"What the chart wants" auto-detection** — scoring function recommends framework from chart signatures
- **Interactive Telegram flow** — inline buttons for chart selection → type → framework → size
- **Transit query language** — deeper drilling into specific transit periods
- **Full transit cycle tracking** — complete planetary return cycles
