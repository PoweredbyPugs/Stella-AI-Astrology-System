# skyki_hour: Stella tool handoff (local copy)

Source of truth: the Claude Doc "skyki_hour: Stella tool handoff",
https://claude.ai/artifact/5ten6He7oa4Hpi8cJRCZKB (rev 7, 2026-11-13). This file
restates it for executors who cannot open the doc. Where they differ, the doc wins.

## The ask

One new Stella MCP tool, `skyki_hour`, returning every fact the hour reading needs
for one Ki double-hour in a single call. It grades nothing and writes no prose.

In scope: the tool; dignity scoring for any given time (Stella only has it for
"now", over HTTP); the fixture test passing. Out of scope: the Octave app, Jev
rules, the reading sentence, changes to existing tools, any level other than the hour.

## Inputs

| Argument | Required | Meaning |
|---|---|---|
| `name` | yes | stored chart name, e.g. `chris` |
| `at` | no | ISO 8601 time; default now; a time with no zone is America/New_York, as `get_sky_window` does |
| `lat`, `lon` | yes | location for the rising sign, sect and planetary hours |

The tool finds the Ki double-hour containing `at`, then reads everything else at
`at` itself. One instant serves every part of the reply.

## What it computes (houses are whole sign throughout)

1. Ki hour: start and end of the double-hour; global and personal Ki numbers for
   the hour and the day with trigram and element, as `get_daily_ki` returns them.
   No position counter.
2. Chart of the moment: rising sign with the times it entered and leaves; sect:
   day or night, sect light, sect benefic, sect malefic.
3. The seven planets: sign, degree, retrograde, dignity score, condition word,
   dignity flags, sect status; house from the rising sign and house in the natal
   chart. Name the rising sign's ruler.
4. The Moon: phase, void of course or not; if void, when it began and ends.
5. Planetary hours: every planetary hour overlapping the Ki hour, with ruler,
   start and end.
6. The rising sign read natally: its natal house, the natal planets and lots in
   that sign, whether its ruler is also the chart ruler. For the ruler: natal
   sign and house, transit sign and natal house, contacts to natal points within
   orb (aspect, orb, applying or separating, exact time).
7. Releasing: L4 and L5 for Spirit and Fortune with the `get_sky_window` fields
   (sign, ruler, start, end, peak type, house from Fortune, angularity, loosing
   of the bond). For each L5 overlapping the Ki hour: the sign's natal house, the
   natal planets in it, the ruler's natal and transit sign and house.
8. Changes inside the hour: one time-ordered list of everything above that
   changes between start and end: rising sign, planetary hour, L5 period, the
   Moon going void (or ceasing to be).
9. Failures: any part that cannot be computed is named in `absent`; the call
   does not raise.

Rules for the reply: no verdict, grade or score beyond the dignity score; no
interpretive text or keywords; every time ISO 8601 with an offset; nothing
slower than the hour.

## Output

The acceptance reply is `tests/fixtures/skyki_hour_chris.json`: chart `chris` at
2026-11-13T18:17:45-05:00, lat 28.6278, lon -81.3631 (Maitland). Field names
are a proposal; the content is the requirement.

## Tests

Fixture call: `skyki_hour(name="chris", at="2026-11-13T18:17:45-05:00", lat=28.6278, lon=-81.3631)`.

- Exact match: window, Ki numbers, rising sign and ruler, sect, each planet's
  sign, condition word and both houses, planetary hour rulers, every natal join,
  releasing signs, peaks and houses, the four changes in order.
- Within tolerance: degrees and orbs within 0.05; times within one minute.

Further checks:

| Case | What must hold |
|---|---|
| A daytime hour | sect reads day; Sun light, Jupiter benefic, Saturn malefic |
| An hour with a void Moon | `void` true with start and end; a start or end inside the window appears in `changes` |
| Rising sign changes mid-hour | the change is in `changes`; `rising` describes the sign at `at` |
| One minute either side of 8:01 pm on 13 November | the two calls return different windows |
| A second stored chart | natal houses and joins follow that chart, nothing carried from `chris` |

## Open points (decided for this pass)

- Ceres: not in the chart store; left out.
- The Moon's contacts to natal points: not in this version.
- The Ki figure: numbers, trigrams and elements only.
- Dignities: a local scorer that reproduces the API's scores and condition words.
- `get_natal_chart` 404: the tool runs on the local ephemeris and chart store only.
- `is_angular` vs `angularity`: the tool carries `angularity` only.
