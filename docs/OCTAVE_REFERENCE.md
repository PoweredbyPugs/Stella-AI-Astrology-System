# Octave reference

Tables for the Octave system (`octave_engine.py`, `octave_ledger.py`, `octave_packet.py`, `octave_forecast.py`, `octave_tools.py`). The ledger text is copied from `data/octave_ledger.json`, dumped from the Octave Calendar page by `scripts/export_octave_ledger.sh`. The `octave://ledger` resource serves the same JSON and is the source for a future knowledge-graph index.

## Levels and anchors

Seven levels, each a continuous count that descends one Ki number per unit and never resets at a seam. Global number at a level: `ki(anchorKi - (idx - anchorIdx))`. Personal number at every level: `ki(natal - global + 5)`.

| Level | Unit | Anchor (live Stella) | Index |
|---|---|---|---|
| great age | 1,728 years, gate at Lichun 2010 | opens 8 | gates since 2010 |
| Ki Age | 144 years, gate at Lichun 2010 | opens 5 | gates since 2010 |
| great year | 12 years, gate at Lichun 2022 | opens 1 | gates since 2010 in Stella (the page's idx + 1) |
| year | Lichun to Lichun (Sun at 315°) | 2026 = 1 | the Ki year |
| month | the Sun's 15° crossings, 12 per Ki year | Feb 2026 = 8 | year × 12 + month |
| day | one degree of solar longitude from Lichun, 360 per year | degree-day 258 of 2026 = 3 | year × 360 + degree |
| hour | one twelfth of a degree, 4,320 per year | degree-hour 3089 of 2026 = 4 | year × 4320 + twelfth |

The 5 rule: 5 has no trigram of its own. It inherits the trigram of the nearest level above it that is not 5; a stack that is 5 all the way up has no figure. A 5 period's element is the element of the trigram it inherits; a 5 native is earth.

Trigrams: 1 Kan, 2 Kun, 3 Zhen, 4 Xun, 6 Qian, 7 Dui, 8 Gen, 9 Li. Elements: 1 water; 3, 4 wood; 9 fire; 2, 5, 8 earth; 6, 7 metal.

## Relation table

Generative cycle Wood, Fire, Earth, Metal, Water. Controlling cycle Wood, Earth, Water, Fire, Metal. The condition is `relation(nativeElement, periodElement)`; the flow is `relation(periodElement, containerElement)`.

| Relation | Rule | Word (condition) | Word (flow) |
|---|---|---|---|
| resonates | actor = field | resonates | resonates |
| fed_by | the field generates the actor | fed by | fed |
| feeds | the actor generates the field | feeds | feeds |
| controls | the actor controls the field | controls | controls |
| controlled_by | the field controls the actor | controlled by | controlled |

## Palace flags

The Lo Shu has south at the top, home arrangement 4 9 2 / 3 5 7 / 8 1 6. The period's global number takes the center; the number in a palace is `ki(home - 5 + global)`.

| Flag | Rule |
|---|---|
| Five Yellow | the home palace where 5 landed |
| Broken | the palace opposite Five Yellow (10 - home) |
| Own | the home palace of the person's number at the level |
| Opposite | the palace opposite Own |
| Coincides | Own is the Five Yellow palace |

## The nine houses

| House | Star | Direction | Line |
|---|---|---|---|
| 1 | White Water | North | Winter. Dormancy and the hidden work; rest, plan, do not push. |
| 2 | Black Earth | South-west | Germination. Preparation, listening, slow groundwork; the risk is Stagnation. |
| 3 | Jade Wood | East | Spring. Sudden starts and new energy that outruns its body; begin, but keep Composure. |
| 4 | Green Wood | South-east | Growth. Expansion, travel, communication; things take off and can scatter. |
| 5 | Yellow Earth | Center | The pivot. Everything comes to you and nothing is displaced; stay put, receive, do not initiate. |
| 6 | White Metal | North-west | Authority. Responsibility and the first harvest; maturity with a perfectionist edge. |
| 7 | Red Metal | West | Harvest. Joy, money, reflection, pleasure and its excesses. |
| 8 | White Earth | North-east | The turning point. Stillness before change; revolution held in the mountain. |
| 9 | Purple Fire | South | Illumination. Recognition and exposure; things come to light. |

## The nine points

| Point | Name | Question | Family |
|---|---|---|---|
| 1 | Potential | What's under the surface? | 1·4·7 receptive |
| 2 | Field | What is being received? | 2·5·8 substrate |
| 3 | Power | What arrived? | 3·6·9 expansive |
| 4 | River | Which way? | 1·4·7 receptive |
| 5 | Delta | What landed here from above? | 2·5·8 substrate |
| 6 | Will | What was the ego magnetic to? | 3·6·9 expansive |
| 7 | Lake | What is the yield? | 1·4·7 receptive |
| 8 | Mountain | This is what lasted. Not touching it yet. | 2·5·8 substrate |
| 9 | Clarity | What is clear from here? | 3·6·9 expansive |

The Tri-force: 3, 6, 9 each take their own trigram doubled at any scale: 51 at 3, 1 at 6, 30 at 9. It touches the path of time and never the circuit.

## The six lines of the circuit

| Line | Verb | Kind | Practice |
|---|---|---|---|
| 1 → 4 | nourish | interval trace | What the one day went under for, the four day points one way. |
| 4 → 2 | break | octave trace | The direction stops being something you steer and becomes something you give to the ground. |
| 2 → 8 | inherit | interval trace | 2 says yes to everything; 8 keeps the one thing that lasted and holds it still, visible, not planted. |
| 8 → 5 | keep | octave trace | 5 is the one place the day touches the larger cycle; 8 is the virtue that opens it. The one held thing carried into the Delta together with the larger picture. |
| 5 → 7 | reflect | interval trace | 5 hands what it received to the lake. 7 sees the reflection, leaves it still, acts from it right away. |
| 7 → 1 | shape | octave trace | In practice it is a seed: 7 writes the sentence, acts once, closes the entry and does not reread it; 1 reads it. |

Fixed line figures where no 5 is involved: 1 to 4 = 59, 4 to 2 = 46, 2 to 8 = 23, 7 to 1 = 60. Where a 5 is involved the figure is built on the stack and the 5 inherits.

## The 25 condition readings

Rows are the actor (the native), columns the field (the period). The flow uses the same table with the period as actor and its container as field.

| Actor \ Field | Water | Wood | Fire | Earth | Metal |
|---|---|---|---|---|---|
| Water | Deep water. Stillness doubled. Rest and listen; nothing here answers to force. | Water nourishing the root. You give and the field grows. Spend freely, but keep your source. | Water on flame. You cool the field; your restraint is wanted, but take care not to extinguish. | The river in its bank. The field contains you. Move within the channel; the limit is the gift. | Metal gathering dew. The field provides. Receive and collect; let it come to you. |
| Wood | Roots in water. Growth is supported. Take it; this is the season to extend. | The forest. Growth crowds growth. Choose one trunk and prune the rest. | Wood becoming light. You are spent into the field's brightness. Glorious and consuming; keep a reserve. | Roots breaking soil. You draw from the field and it yields slowly. Push at a tree's pace, not a shoot's. | The axe. The field prunes you. Accept the cut; what remains is what grows. |
| Fire | Flame under rain. Keep small and go inward. Protect the ember. | Dry fuel. The field feeds your flame. Abundant; watch for wildfire. | The blaze. Brilliance and exhaustion together. Shine, then rest before you are asked to. | Fire becoming ash. You give yourself to the field. An ending that fertilizes. | The forge. You shape the field; you are the smith. Patience with the heat. |
| Earth | The bank shaping the river. You regulate the field. This is responsibility, not support. | Roots in the soil. The field draws on you. Yield; do not resist what is growing. | Ash enriching the ground. The field feeds you. A carried time; receive it. | Earth on earth. Weight and stillness. Nothing cuts, nothing pushes; the risk is Stagnation. Do not grasp. | Earth bearing ore. You give the field its form. It costs, and something is made. |
| Metal | Metal yielding water. You are drained into flow. Let go; you are turning into motion. | The blade. You cut the field. Discernment: cut only what needs cutting. | In the forge. You are being reshaped by heat you did not choose. Hold form; submit to the work. | Ore in the mountain. The field holds and forms you. Rest in it. | Metal on metal. Sharpness doubled. Clarity or brittleness; do not over-cut. |

## Tool map

| Tool | Inputs | Returns | Module function |
|---|---|---|---|
| `get_octave_period` | level, datetime or idx, natal (optional) | the period: number, global, span, ba, shi, house, point, palace; with natal the full packet with ji and the six sources | `octave_packet.packet`, `octave_engine.period` |
| `get_octave_condition` | natal, level, datetime or idx | the condition and the flow with relation words and readings, the composed statement, the quiet sentence and its key | `octave_ledger.statement`, `trad`, `trad_key` |
| `get_native_figure` | natal, level, datetime or idx | the ba, the native hexagram, the ji lines, the ba's text at those lines | `octave_engine.native_figure`, `ji_lines` |
| `get_octave_shi` | level, datetime or idx, natal (optional) | the lines that change into the next period, the ba's text at them, the next figure | `octave_engine.shi` |
| `get_palace` | level, datetime or idx, natal (optional) | the nine cells, the flags, the house line and direction, the star name | `octave_engine.palace` |
| `get_octave_point` | number | the point's brief, tending, family and Tri-force figure | `octave_ledger.brief`, `tending` |
| `get_octave_line` | from_number, to_number, datetime and level (to resolve a 5) | the line's verb, kind, practice and figure | `octave_engine.line_figure` |
| `write_octave_forecast` | natal, level, datetime or idx, fresh (optional) | the paragraph with Jev's read and grade | `octave_forecast.forecast` |
| `write_octave_statement` | natal, level, datetime or idx, fresh (optional) | the written thought with Jev's read and grade, or null with the composed sentence | `octave_forecast.statement` |
| `explain_octave_statement` | natal, level, datetime or idx | the reading of the thought: parts, whole, questions, close | `octave_forecast.explain` |

Resources: `octave://framework` (the way of thinking), `octave://ledger` (this ledger as JSON). Prompts: `octave_reading`, `octave_period_reading`.

## Conventions

- Stella's period indexes count gate levels from 2010, so `idx` for the great year is the page's idx + 1.
- All times are America/New_York unless an offset is given; a bare date is read at local noon.
- Cache versions: forecast `v4`, statement `s2`, explain `x1` (keys `<version>|model|level|idx|natal` in `DATA_DIR/forecasts.json`).
- Environment: `TYPESAFE_API_KEY` (Jev), `OPENROUTER_API_KEY` (writer), `FORECAST_MODEL` (default `deepseek/deepseek-v4.1-flash`), `FORECAST_URL` (default OpenRouter, any OpenAI-compatible endpoint), `DATA_DIR`, `GNOSTIC_JSON`, `OCTAVE_LEDGER_JSON`, `JEVKIT_PATH`. Without a Jev key the writer runs unbriefed and ungraded; without `OPENROUTER_API_KEY` the written tools report no key.
- Worked example: natal 1986-05-01 is natal year 5, natal month 9 (triple 5 · 9 · 1). Month of 2026-11-09: ba 36 Darkening of the Light, native 11 Peace, ji line 2.
