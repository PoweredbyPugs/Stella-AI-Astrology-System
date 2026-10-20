# Stella feature: hub inheritance (the 5 rule) and the octave port

Agreed in conversation on 2026-10-20 between Chris and Claude. Supersedes the pasted plan where they differ.

## Two uses of 5, kept apart

**Reading** (the natal triple and the reading tools `get_ki`, `get_ki_cycle`, `get_ki_reading`,
`get_ki_transition`): no hierarchy, three numbers. A 5 in the middle takes the other numbers'
character. The doubling rule in `ki_reading.py` stays exactly as it is. A 5 in the first
position (e.g. 5.9.1) is an open doctrinal question, to be looked up in the knowledge graph,
not decided in code.

**Timekeeping** (the octave, `get_ki_changes`, `ki_change_*`, `get_ki_change_schedule`,
`get_daily_ki`): the chain hour → day → month → year → great year → Ki Age → great age.
Ki 5 has no trigram. A 5 at any level inherits the trigram of the nearest parent level that
is not 5, walking up as far as needed. If every level up to the top is 5 or missing, raise
`HubUnresolvable`. The map 5 → ☷ Kun in `ki_changes.py` is wrong and is removed.

## Two chains, never mixed

Every global level is a Lo Shu number descending 1 per period. Every personal level is the
natal year read against the matching global level by the one formula
`personal(natal, global) = ki(natal - global + 5)`. A personal 5 inherits up the personal
chain only; a global 5 up the global chain only. Gates (when a level turns) come from the
global chain.

## Levels above the great year

Each level is ×12 the one below and descends by 1 per period:

| Level | Length | Gate rule |
|---|---|---|
| great year | 12 years | opens at a Lichun; the year there is always 2, 5 or 8. Anchor: Lichun 2022 opens 8. |
| Ki Age | 12 great years = 144 years | opens at a great-year gate; the great year there is always 2, 5 or 8. 144 mod 9 = 0, so the year Ki at its opening and closing are equal. |
| great age | 9 Ki Ages = 1,296 years | opens at a Ki Age gate; the Ki Age there is always 2, 5 or 8. 1,296 is a multiple of 108, so every great age opens on an 8.5.2 row. |

**Ki Age anchor.** Read the global stack at Lichun 2022 upward and each level is the next Earth
number in the cycle 2 → 5 → 8 → 2: month 2, year 5, great year 8. The great year became 8 because
8 follows 5 over 2; no other fact was needed. The same rule one level up gives Ki Age 2 (2 follows
8), and one more gives great age 5. So Lichun 2022 opened global Ki Age 2 and global great age 5,
and the global stack at that instant reads:

| great age | Ki Age | great year | year | month |
|---|---|---|---|---|
| 5 | 2 | 8 | 5 | 2 |

Constants: `KI_AGE_ANCHOR_YEAR = 2022`, `KI_AGE_ANCHOR_KI = 2`, `GREAT_AGE_ANCHOR_YEAR = 2022`,
`GREAT_AGE_ANCHOR_KI = 5`, documented beside the two other lattices the arithmetic allows
(Ki Age opening 1914 → next 2058; opening 1950 → next 2094) so a doctrinal fact can replace them
in one line. Ki Age gates: 2022, 2166, 2310. Great age gates: 726, 2022, 3318.

Chris (natal 5) from Lichun 2022: personal great year 2, personal Ki Age 8, personal great age 5.

## Consequences the code must preserve

- A day 5 over its month is the month's trigram doubled: one of 1, 2, 29, 30, 51, 52, 57, 58.
- Moving lines are always the line-by-line difference between two figures, never a fixed table.
  1↔4 and 2↔8 stay line 6 yin→yang under any parent. 5↔7 varies with the parent: lines 4,5
  yin→yang under Kun; nothing under Dui; line 5 yin→yang and line 6 yang→yin under Li.
- Single-level changing lines (current Ki → next Ki at one level) are computed from the full
  stack at both instants, because a 5 depends on what its parent is at that instant.
- Every hexagram in output that involved inheritance carries
  `"inherited": {"level": "<child>", "from": "<parent>"}` and the trigram name is tagged
  `(inherited from <parent>)`.

## Octave math moves into Stella

`octave.py` stops being an HTTP client. The Nine-Year Spiral library at
`/Volumes/Shirahoshi/HermesNode/octave/lib` (ki/, iching/form.ts, enneagram/, report.ts,
summary.ts) is ported to Python, with inheritance replacing its "five rule" (which took the
other digit, including a child's). The app keeps running untouched; its vitest fixtures become
Stella's fixtures wherever the five rule does not change the answer. `get_octave` returns the
same JSON shape as the app's `/api/report` summary, plus `inherited` tags. `get_octave_reading`
reads the Gnostic JSON file directly (`GNOSTIC_JSON` env, default the octave repo's file),
falling back to the HTTP app only if the file is absent.

## Tests that must exist

1. Day 5 under month X yields the pure hexagram of X, for all eight X.
2. Chain of 5s resolves to the first non-5 parent.
3. All-5 stack through the great age raises `HubUnresolvable`; a 5 great year with a non-5
   Ki Age resolves to the Ki Age.
4. 5↔7 under a Kun parent reproduces lines 4,5 yin→yang (regression against the old table).
5. 5↔7 under a Dui parent returns no moving lines.
6. Ki Age and great age gates: 2022 → 2, 2166 → 1, 1878 → 3 (Ki Age); 2022 → 5, 3318 → 4,
   726 → 6 (great age); every Ki Age gate lands on an Earth great year, every great age gate on Ki Age 2.
7. Octave port reproduces the app's fixtures for 1986-05-01 at 2026-10-16 (natal 5·9·1,
   today 9.1, great year 2, year figure 35, month figure 63, octave 4, echo pairs
   [[6],[2,6],[4,5]], next shift 2034 2→3) and every figure in the app's `want` table except
   where a 5 was formed against a child (none in that table).
