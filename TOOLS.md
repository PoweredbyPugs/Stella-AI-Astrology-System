# Stella MCP Server — 105 Tools

*Last updated: Nov 13, 2026*

## Helios Bridge (current sky data)

| # | Tool | Description |
|---|------|-------------|
| 1 | `get_current_moon` | Current moon phase and sign |
| 2 | `get_planet_positions` | Current positions of all planets |
| 3 | `get_planet_aspects` | Current aspects between planets |
| 4 | `get_weekly_moon_phase` | This week's major moon phase |
| 5 | `get_natal_chart` | Calculate natal chart from birth data |
| 6 | `generate_chart` | Generate and optionally save a natal chart |
| 7 | `get_chart` | Retrieve a stored natal chart by name |
| 8 | `list_charts` | List all stored natal charts |

## pyswisseph Native (no Helios dependency)

| # | Tool | Description |
|---|------|-------------|
| 9 | `get_void_of_course_moons` | VOC periods (modern planet set, validated vs MoonTracks) |
| 10 | `transit_timing` | When a transit enters orb, perfects, and leaves orb |
| 11 | `search_next_transit` | Scan for upcoming transits to a natal chart |
| 12 | `lunar_return` | Chart for Moon's return to natal position |
| 13 | `solar_return` | Chart for Sun's return to natal position |
| 14 | `secondary_progressions` | Progressed chart (1 day = 1 year) with solar arc ASC/MC |
| 15 | `find_elections` | Electional windows scored by Moon condition + aspects |
| 16 | `find_eclipses` | Solar/lunar eclipses with natal contact detection |
| 17 | `get_exact_ingresses` | Precise sign ingress times via binary search |
| 18 | `get_planetary_hours` | 24 planetary hours, Chaldean order, sunrise/sunset |

## Timing Techniques

| # | Tool | Description |
|---|------|-------------|
| 19 | `get_profections` | Annual profections with lord of year |
| 20 | `get_zodiacal_releasing` | ZR L1–L5 at one instant, with peaks (from Fortune), angular-triad phase, and the loosing of the bond at every level |
| 21 | `get_zr_report` | Comprehensive ZR report (Brennan worksheet framework); `lot` spirit or fortune, `format` markdown or json |
| 93 | `get_zr_periods` | Every ZR period overlapping a window at the requested levels (timelines, Octave, next loosing or peak) |
| 94 | `get_sky_window` | The sky over a window, for Octave's sky layer: at the start the positions, the Moon's phase, the ascendant (with lat/lon), transits to a chart with orbs, the profection; inside it lunations, ingresses, the Moon's 15° gates, stations, eclipses, void of course, exact transits, the turnings; releasing periods for both lots at chosen levels (by default the level the window's length is read at: a few hours L5, a day L4, a month L3, a year L2, longer L1); UTC in and out |
| 105 | `skyki_hour` | One Ki double-hour in one call for the hour reading: Ki hour and numbers, rising sign and sect, the seven planets with dignity and houses, the Moon, planetary hours, the rising sign read natally, releasing L4/L5 with natal joins, and the changes inside the hour; facts only |

ZR conventions (`zr.py`): 360-day years, 30-day months (Brennan's published tables reproduce date for date). Sub-periods run the twelve signs from the parent's sign; after 211 units the bond is loosed and they jump to the sign opposite the parent, continuing in order; the last sub-period is cut at the parent's end. Spirit in Fortune's sign releases from the next sign. Peaks and triads always count from Fortune: 1st/10th Major, 7th Moderate, 4th Minor; cadent = preparatory, angular = peak, succedent = completion.

Sky conventions (`sky.py`): every instant out is UTC ISO with `Z`; an input with an offset or `Z` is taken as given, a naive one is New York; transit orbs per body (Moon 3, Sun 3, Mercury 2, Venus 2, Mars 2.5, Jupiter 3, Saturn 3, Uranus, Neptune, Pluto 2.5; sextiles two thirds), `exact` within 0.5° (the Moon 1°), `exact_at` by bisection within a per-body span, `applying` from `exact_at` when it is known; a body's aspects to its own natal place are included (returns, halfway points). One call per Octave period; windows over 13 years are refused.
| 22 | `get_transits_now` | All current transits to a natal chart |
| 23 | `get_transit_summary` | High-level outer planet transit summary |
| 24 | `get_dignity_score` | Essential dignity score for any planet/position |
| 25 | `get_current_dignities` | Dignity scores for all planets right now |

## Vimshottari Dasha & Timing Stack *(NEW 2026-03-26)*

| # | Tool | Description |
|---|------|-------------|
| 26 | `get_timing_stack` | **Full timing stack** — 4 systems in one call: Dasha (5 levels), ZR (Spirit + Fortune, L1-L5), Nakshatra transit (lord + pada), Ki (5 levels). Includes glyphs, resonance detection. |
| 27 | `get_dasha_periods` | 5-level Vimshottari dasha only (maha→prana) with dates and durations |
| 28 | `get_nakshatra_transit` | Live Moon nakshatra position with lord, pada, entry/exit times |

### Vimshottari Dasha — Key Facts

- **Lord sequence (nakshatra order):** ☋Ketu(7yr), ♀Venus(20yr), ☉Sun(6yr), ☽Moon(10yr), ♂Mars(7yr), ☊Rahu(18yr), ♃Jupiter(16yr), ♄Saturn(19yr), ☿Mercury(17yr) = 120 years
- **NOT the sequence:** Ke,Su,Mo,Ma,Ra,Ju,Sa,Me,Ve — that's a common misquote
- **Each lord owns 3 nakshatras:** position i → nakshatras i, i+9, i+18
- **5 levels:** Maha (decades) → Bhukti (months-years) → Pratyantara (weeks-months) → Sookshma (days-weeks) → Prana (hours)
- **Sub-division:** Each level divides parent period proportionally by the same 9 lords, starting from parent's lord
- **Birth seeding:** Natal Moon nakshatra determines first lord; fraction of nakshatra traversed = fraction of first period elapsed
- **Nakshatra transit (levels 6-7):** Live Moon position gives daily lord (~24h per nakshatra) and pada quality (~6h per pada: Dharma/Artha/Kama/Moksha)
- **Module:** `dasha.py`

## 9 Star Ki & I Ching

| # | Tool | Description |
|---|------|-------------|
| 29 | `get_ki` | 9 Star Ki numbers for a date |
| 30 | `get_ki_cycle` | Full Ki profile with personal year/month cycle |
| 31 | `get_ki_reading` | Combined Ki + I Ching reading (hexagram from Ki) |
| 32 | `get_ki_transition` | Ki month transition report with hexagram derivation |
| 33 | `cast_hexagram` | Cast I Ching hexagram (coins or yarrow) |
| 34 | `retrieve_wisdom` | Search Gnostic Book of Changes + I Ching texts |

The three-number reading has no hierarchy: a 5 in the middle takes the other numbers' character (`ki_reading.py`). This is different from the timekeeping rule below.

## Octave *(computed in Stella since 2026.10.20)*

| # | Tool | Description |
|---|------|-------------|
| — | `get_octave` | A life as nine-year octaves on Gurdjieff's enneagram: natal triple, every octave, today's position, the nine years with their figures (year over great year), echo pairs with moving lines, shocks, the next cycle. Months of the current year by default, all 108 with `include_months=true`. |
| — | `get_octave_reading` | A hexagram from The Gnostic Book of Changes: judgment, superior-man line, editor's notes, moving lines. |
| 95 | `get_octave_period` | The Octave period at a level (instant or index), with or without a birth date: number, global, span, ba, shi, house, point, palace; with `natal` the full packet with ji and the six sources |
| 96 | `get_octave_condition` | The condition (the native's element in the period's) and the flow (the period in its container) with their words and readings, the composed statement, the quiet sentence and its key |
| 97 | `get_native_figure` | The ba, the native hexagram, the ji lines where they differ, and the ba's text at those lines |
| 98 | `get_octave_shi` | The lines that change from this period's ba into the next, the ba's text at them, and the next figure |
| 99 | `get_palace` | The Lo Shu palace of a period: nine cells, Five Yellow, Broken, Own and Opposite flags, the house line and direction, the star |
| 100 | `get_octave_point` | One of the nine points: name, question, function, image, shadow, practice, family, tending, and the Tri-force figure at 3, 6, 9 |
| 101 | `get_octave_line` | One of the six circuit lines: verb, kind, practice and its figure; a line through 5 resolves the 5 at a datetime |
| 102 | `write_octave_forecast` | One paragraph of synthesis for a period: Jev reads and grades, the writer phrases, one rewrite, cached (prompt v4) |
| 103 | `write_octave_statement` | One written thought of two or three sentences under the headline: Jev decides and grades, the writer phrases, cached (statement s2); null with the composed sentence if nothing passes |
| 104 | `explain_octave_statement` | The reading of the written thought: each phrase quoted and opened, the whole, questions to sit with, a closing line (explain x1) |

Math in `octave_math.py`; text in `data/gnostic.json`. Rows 95-104 are in `octave_tools.py` (engine `octave_engine.py`, ledger `octave_ledger.py`, pipelines `octave_forecast.py`). Row 105 is in `skyki.py`. Framework as the `octave://framework` resource and the `octave_reading` and `octave_period_reading` prompts; the ledger as `octave://ledger`. Reference: `docs/OCTAVE_REFERENCE.md`.

## Convergence Ki (5-level solar-terrestrial cascade)

Based on the -3 cascade and 365-day continuity breakthrough (March 6, 2026). Research: `stella/research/convergence-sockets.md`

| # | Tool | Description |
|---|------|-------------|
| 35 | `get_convergence_ki_now` | The full Ki stack at an instant, read from the Sun: great year (synodic), year, month, day (1° of the Sun), hour (5′), with the Moon and ascendant as observation layers. Takes an ISO datetime; a bare date is read at noon. Carries a `build` block (git sha, load time). |
| 36 | `get_synodic_gate_now` | The 12-year great-year gate: arithmetic from Lichun 2010 = 2 (2022 = 1), gates on Lichun, always on Earth years |
| 37 | `get_natal_gates` | Map a chart's planets to their permanent 15° gates and San Cai triads |

## Ki Changes — Mercury's Reading *(NEW 2026-03-27)*

Mercury reads the delta, not the state. These tools show what's transitioning at each level: changing lines (trigram yin↔yang), Wu Xing phase relationships, I Ching hexagrams formed by adjacent level pairs, and Gnostic Book of Changes interpretations.

| # | Tool | Description |
|---|------|-------------|
| 38 | `get_ki_changes` | **Full Ki changes** — all 5 levels at once. Current→next Ki, changing lines, hexagrams from level pairs, Wu Xing transitions. `include_gnostic=true` for I Ching text. |
| 39 | `get_ki_change_schedule` | Next N changes at a specific level (default 9 = full cycle). Shows rhythm of transitions. |
| 40 | `ki_change_hour` | Hour-level Ki change (~2h cycle). Hexagram with day level. Fastest pulse. |
| 41 | `ki_change_day` | Day-level Ki change (midnight). Hexagrams with month and hour levels. |
| 42 | `ki_change_month` | Month-level Ki change (Sun crosses 30° boundary). Hexagrams with year and day levels. |
| 43 | `ki_change_year` | Year-level Ki change (Lichun, Sun at 15° Aquarius). Hexagrams with great-year and month levels. |
| 44 | `ki_change_global` | Great-year (synodic) change at the next 12-year gate Lichun. Hexagram with year level. Slowest pulse; the Ki Age and great age above it are reported in the stack. |

### Ki Changes — Architecture

**Core insight:** Ki numbers map to I Ching trigrams (1=Kan☵, 2=Kun☷, 3=Zhen☳, 4=Xun☴, 6=Qian☰, 7=Dui☱, 8=Gen☶, 9=Li☲). Two adjacent Ki levels form a hexagram: slower level = lower trigram (stable ground), faster level = upper trigram (what's cycling).

**The 5 rule (2026.10.20):** 5 has no trigram. It inherits the trigram of the nearest level above it that is not 5 (`hub_inheritance.py`), and the output names what was inherited. A personal 5 inherits up the personal chain only. Moving lines are always the difference between two resolved figures; there are no fixed tables.

**Changing lines:** When a Ki level transitions (e.g. day Ki 9☲→8☶), the trigram lines that differ are "changing lines" in I Ching terms. This gives direction of change (yin→yang or yang→yin). Both figures are resolved from the full stack at their own instant, so a parent that turns first (month and year at Lichun, the day at midnight before the 01:00 hour) is already advanced.

**64 = Mercury's grid:** Mercury's magic square is 8×8 = 64 cells = 64 hexagrams. The I Ching IS Mercury's square. Every Ki transition is a hexagram reading.

**Modules:** `ki_changes.py`, `hub_inheritance.py`, `ki_levels.py`

### Ki — Key Architecture (Definitive, October 25 2026)

**7 levels, one hand (the Sun past Lichun at 15° Aquarius):**
```
Great age   — 12 Ki Ages = 1,728 years = 24° of precession (25,920 / 15); Lichun 2010 opens 8
Ki Age      — 12 great years = 144 years; Lichun 2010 opens 5
Great year  — 12 Ki years; Lichun 2010 opens 2, 2022 opens 1, 2034 opens 9; gates on Lichun
Year Ki     — 360° of the Sun, Lichun to Lichun; 2026 = 1
Month Ki    — 30° of the Sun (15° of each sign); Feb 2026 = 8
Day Ki      — 1° of the Sun (a degree-day, 23.5–25.2 h); 30 per month; every Lichun opens 8
Hour Ki     — 5′ of the Sun (a degree-hour, ~2 h); 12 per day; opening = 3·day + 8
```

**The lock is the count:** twelve of anything is its parent, nine of anything is one cycle
of its numbers. 12 mod 9 = 3 and 30 mod 9 = 3, so every level opens on an Earth number
(2, 5, 8) and the running count lands on exactly that number at the seam. Nothing resets,
nothing turns at midnight or on the clock. At Lichun 2010 every level turned together and the
stack read 8 · 5 · 2 · 8 · 2 · 8 · 5. A level is Earth at its own seam only when its parent
turns too. Module: `ki_solar.py`.

**Moon is NOT structural for Ki.** Moon's 12-gate/convergence socket rhythm is real but kept as a parallel observation layer. Ki is purely solar + terrestrial.

**Personal Ki:** Flying Star transformation — `_flying_star(natal_year_ki, global_ki)` applied independently to each level.

**Month gate crossings:** Sun at 15° of each sign (Chinese solar terms / 节气). NOT Gregorian months.

- **Module:** `ki_solar.py` (the numbers), `convergence_ki.py` (the full payload with observation layers)
- **Synodic module:** `convergence_ki.py` → `get_synodic_gate()`

## BaZi — Four Pillars of Destiny *(NEW 2026-11-11)*

Traditional Zi Ping, computed on Stella (`bazi.py`). Conventions and tables: `docs/BAZI_REFERENCE.md`. Defaults: true solar time on, day boundary 23:00; both are parameters.

| # | Tool | Description |
|---|------|-------------|
| 90 | `get_bazi` | Natal four pillars with hidden stems, Ten Gods, Nayin, life stages, void, Day Master strength (season/roots/support), structure (格局), element tallies and climate, interactions, core symbolic stars, and the ten luck pillars. Stored chart or raw birth data; `format="json"` for data. |
| 91 | `get_bazi_luck_pillars` | The 大運: direction, start age (days to the jie at 3 days per year), each ten-year pillar with Ten Gods and natal interactions, and the current one. |
| 92 | `get_bazi_time_pillars` | Year/month/day/hour pillars at any instant; with a chart, their Ten Gods against the Day Master and every interaction with the natal pillars and the current luck pillar. |

## Midpoints & Cosmobiology

| # | Tool | Description |
|---|------|-------------|
| 45 | `get_midpoint_interpretation` | Ebertin COSI lookup for a midpoint pair |
| 46 | `get_midpoint_pictures` | Natal midpoint pictures (90° dial) |
| 47 | `get_midpoint_transits` | Transiting planets activating natal midpoints |
| 48 | `get_solar_arcs` | Solar arc directions hitting natal midpoints |

## Chart Reading & Synthesis

| # | Tool | Description |
|---|------|-------------|
| 49 | `chart_reading` | Full chart reading (size × type × framework) |

## Knowledge Graph (10,548 chunks, 41 texts)

| # | Tool | Description |
|---|------|-------------|
| 50 | `knowledge_search` | Semantic search across interpretation nodes |
| 51 | `knowledge_search_json` | Structured JSON search results |
| 52 | `knowledge_stats` | Graph statistics |
| 53 | `interpret_placement` | Multi-layered interpretation for a placement |

## Neo4j Graph Traversal

| # | Tool | Description |
|---|------|-------------|
| 54 | `graph_traverse_chain` | Depositor chain from planet to final dispositor |
| 55 | `graph_find_receptions` | All mutual receptions in a chart |
| 56 | `graph_aspect_network` | Natal aspect network (tightest first) |
| 57 | `graph_midpoint_pictures` | Midpoint pictures from graph |
| 58 | `graph_chart` | Complete chart as graph structure |
| 59 | `graph_walk` | Deep walk from a placement (all connections) |
| 60 | `graph_compare` | Compare two charts (synastry + structural) |
| 61 | `graph_query` | Structured graph query with filters |
| 62 | `graph_cypher` | Raw Cypher query against Neo4j |
| 63 | `graph_stats` | Neo4j graph statistics |
| 64 | `graph_synthesize` | Narrative scaffold for one planet |
| 65 | `graph_synthesize_chart` | Full chart synthesis scaffold (all 7 traditional planets) |
| 66 | `graph_rulership_web` | Complete rulership web for a sign |
| 67 | `graph_planet_condition` | Planet's full condition in a sign |

## Chart Storage

| # | Tool | Description |
|---|------|-------------|
| 68 | `store_chart` | Save a natal chart |
| 69 | `load_chart` | Load a chart (local storage → Helios fallback) |
| 70 | `list_stored_charts` | List locally stored charts |
| 71 | `delete_chart` | Delete a stored chart |

## Emergent Triad (chart memory)

| # | Tool | Description |
|---|------|-------------|
| 72 | `discover` | What's most active in a chart right now |
| 73 | `reflect` | Store a validated insight/prediction/event |
| 74 | `recall` | Search chart's accumulated insights |
| 75 | `validate` | Confirm or invalidate a stored insight |
| 76 | `chart_memory_stats` | What the system has learned about a chart |

## Autopoietic

| # | Tool | Description |
|---|------|-------------|
| 77 | `autopoietic_init` | Initialize autopoietic chart session |
| 78 | `autopoietic_submit` | Submit a diverge/converge pass |
| 79 | `autopoietic_converge` | Get convergence prompt for current round |
| 80 | `autopoietic_status` | Check session status |

## Sweph Passthroughs (Helios REST)

| # | Tool | Description |
|---|------|-------------|
| 81 | `sweph_test` | Test server connectivity |
| 82 | `sweph_profections_calc` | Profections without stored chart |
| 83 | `sweph_zr_calc` | ZR without stored chart |
| 84 | `sweph_planetary_retrogrades` | Current retrograde status |
| 85 | `sweph_daily_transits` | Transits to a natal chart |
| 86 | `sweph_moon_for_date` | Moon phase/sign for a date |
| 87 | `sweph_planetary_ingresses` | Planetary sign changes |
| 88 | `sweph_planetary_stations` | Retrograde/direct stations |
| 89 | `sweph_important_transits` | Significant outer planet aspects |
