# The Octave System — a breakdown for Stella (text export of https://claude.ai/artifact/QJZHtLnVMwKxfB3M6owWjb, read 2026-11-12, rev 16)

 · 
## What the Octave is, and what Stella has versus what it needs
The Octave is Nine Star Ki laid on Gurdjieff's enneagram: seven nested cycles of time, each counted down 9 to 1, each period given a trigram, a hexagram, an element, a place on the Lo Shu square and a point on the nine-point figure, and all of it read for one person against their natal numbers. The page (the Octave Calendar, 
[code]
octave/ in HermesNode, live on punk at http://192.168.1.181:3333) is the reference build; this document is what Stella needs to answer the same questions as tools.
Stella today has the time engine and the book: 
[code]
get_daily_ki, 
[code]
get_ki, 
[code]
get_octave, 
[code]
get_ki_cycle, 
[code]
get_ki_change_schedule, 
[code]
ki_change_*, 
[code]
get_octave_reading (the Gnostic Book of Changes as markdown). Those stay the anchors; the page's engine mirrors them and its tests pin them.
Checked against Stella's server, 11 Nov 2026 (
[code]
clawd/stella: 
[code]
stella_server.py, 
[code]
octave.py, 
[code]
octave_math.py, 
[code]
hub_inheritance.py, 
[code]
ki_levels.py, 
[code]
ki_changes.py, 
[code]
ki_reading.py; and the live tools). The stacks agree exactly: for 2026-11-11 12:22, natal 1986-05-01, Stella gives 8.5.1.1.8.4.8 global and 2.5.9.9.2.6.2 personal, the page the same.
[table]

|  | 
Capability | 
Stella today | 
Gap
|  | 
seven-level stack, anchors, hub inheritance for 5 | 

[code]
get_daily_ki, 
[code]
get_ki_periods, 
[code]
get_convergence_ki_now, 
[code]
hub_inheritance.resolve | 
none
|  | 
period figure (ba) and moving lines into the next period (shi) | 

[code]
get_ki_changes, 
[code]
ki_change_hour/day/month/year, 
[code]
hub_inheritance.hexagram, 
[code]
moving_lines | 
none for the figures; the ba's text at the shi lines is one 
[code]
get_octave_reading call away
|  | 
the book | 

[code]
get_octave_reading | 
none
|  | 
nine-year octave with echo pairs and shocks | 

[code]
get_octave, 
[code]
octave_math | 
the page's circuit (the six line figures, the trace verbs) and the Tri-force figures are not in it
|  | 
element relation | 

[code]
ki_reading.get_element_relationship (prose: \"feeds / controls\") | 
no 
[code]
resonates / fed_by / feeds / controls / controlled_by function with the page's words; no condition (native in period) or flow (period in container) tools; the 25 readings are absent
|  | 
native figure and ji | 
none | 

[code]
nativeFigure (personal trigram over the natal month's house) and the ji lines are missing entirely
|  | 
the Lo Shu palace | 

[code]
ki.py has the fixed palace layout for natal placement | 
no flight for a period (
[code]
ki(home − 5 + global)), no Five Yellow / Broken / Own / Opposite flags, no house lines, no star names
|  | 
the ledger vocabulary | 

[code]
octave://framework resource, 
[code]
octave_reading prompt, 
[code]
hermes_skill() (FRAMEWORK text, version 1.0.0) | 
the framework predates the ledger of 30 Oct and every decision since; the nine points' questions and practices, the six verbs, tending, the forces are not data Stella can return
|  | 
the composed reading (statement, quiet sentence, key) | 
none | 

[code]
STATEMENT, 
[code]
TRAD, 
[code]
TRAD_KEY, 
[code]
COND_CLAUSE missing
|  | 
Jev + writer pipelines (forecast, statement, explain) | 
none; 
[code]
get_ki_reading writes its own prose from templates | 
the three pipelines, the Jev questions and grades, the cache
One discrepancy to settle: 
[code]
get_synodic_gate_now describes its anchor as \"Lichun 2022 = gate 8\", while 
[code]
ki_levels.py and the live stack open the 2022 great year on 1 (2010 opened 2). The page follows the live stack. The old tool's text, or its arithmetic, needs the same anchor.
## The engine: levels, anchors, the personal number, the 5 rule
Seven levels, each a continuous integer count that descends one Ki number per unit and never resets at a seam. Stella's 
[code]
ki_levels.py is the source; the page's 
[code]
src/engine.js mirrors the live server (verified 25 Oct 2026) and 
[code]
test/ pins it.
[table]

|  | 
Level | 
Unit | 
Anchor (live Stella) | 
Index
|  | 
great age | 
1,728 years, gate at Lichun 2010 | 
opens 8 | 
gates since 2010
|  | 
Ki Age | 
144 years, gate at Lichun 2010 | 
opens 5 | 
gates since 2010
|  | 
great year | 
12 years, gate at Lichun 2022 | 
opens 1 | 
gates since 2022
|  | 
year | 
Lichun to Lichun (Sun at 315°) | 
2026 = 1 | 
the Ki year
|  | 
month | 
the Sun's 15° crossings, 12 per Ki year | 
Feb 2026 = 8 | 
year × 12 + month
|  | 
day | 
one degree of solar longitude from Lichun, 360 per year | 
degree-day 258 of 2026 = 3 | 
year × 360 + degree
|  | 
hour | 
one twelfth of a degree, 4,320 per year | 
degree-hour 3089 of 2026 = 4 | 
year × 4320 + twelfth
Global number at a level: 
[code]
ki(anchorKi − (idx − anchorIdx)), where 
[code]
ki wraps into 1..9. The personal number at every level is 
[code]
ki(natal − global + 5), natal being the person's year number (1986 → 5 for the owner, ki(2027 − 1986); the natal month number, 9 for 1986-05-01, is used only by the native figure). The hour boundary is a solar-longitude twelfth, not a clock double-hour; boundaries land within about ten seconds of Stella's (truncated VSOP87 Sun, nutation, aberration, ΔT table).
The 5 rule (ledger, 30 Oct 2026, second revision): 5 has no trigram and no hexagram of its own. It inherits the trigram of the nearest level above it that is not 5 (
[code]
resolve(stack, level) returns 
[code]
{ki, source, tri, inherited}); a stack that is 5 all the way up has no figure, by decision. A 5 period's element is the element of the trigram it inherits; a 5 native is earth.
The trigram of a number: 1 Kan ☵, 2 Kun ☷, 3 Zhen ☳, 4 Xun ☴, 6 Qian ☰, 7 Dui ☱, 8 Gen ☶, 9 Li ☲. Elements: 1 water; 3, 4 wood; 9 fire; 2, 5, 8 earth; 6, 7 metal.
## Figures: ba, shi, ji, line figures, the Tri-force
Three Japanese-named lenses on one period, settled 10 Nov 2026. Ba (場) is the field, the period's hexagram. Shi (勢) is its movement, the lines that change into the next period. Ji (機) is the native in the field, where the person's own hexagram differs from the ba.
Ba, the period's figure. The period's resolved trigram over its container's resolved trigram: hour over day, day over month, month over year, year over great year (
[code]
figure(stack, level, upper) → King Wen number, name, the six lines bottom to top as 0/1, the two trigrams). The top level has no container and no figure. A 5 uses its inherited trigram. The Gnostic text for the figure is 
[code]
get_octave_reading(hexagram).
Shi, the movement. 
[code]
moving(ba.lines, nextBa.lines) → the lines (1 = bottom) where the next period's figure differs, each with from/to yin/yang. The reading quotes the ba's text at those lines (
[code]
get_octave_reading(ba, lines)), and where it lands is the next figure.
Ji, the native in the field. The native hexagram is the personal number's trigram at the level over the house of the natal month number at the same level: 
[code]
nativeFigure(period, natalMonth) builds a second personal stack from the natal month (
[code]
ki(natalMonth − global + 5) at every level), resolves both at the level (a 5 inherits), and stacks upper over lower. The ji lines are 
[code]
moving(ba.lines, native.lines), read field → native, so the text quoted is the ba's at those lines. Profiles only; Global has no ji. Worked example (month of 9 Nov 2026, natal 1986-05-01): ba 36 Darkening of the Light, native 11 Peace, ji line 2.
Line figures of the circuit (the hexad 1→4→2→8→5→7→1). Every line has one figure: destination over origin, both resolved (
[code]
lineFigure(fromRes, toRes)); its moving lines are the figure against the origin doubled. Fixed where no 5 is involved: 1→4 = 59, 4→2 = 46, 2→8 = 23, 7→1 = 60. Built on the day where 5 inherits: 8→5 = inherited over Gen, 5→7 = Dui over inherited. Open discrepancy, by decision: the ledger's text gives 47 for 7→1 and 60 for 5→7 in a Kan month; the code follows the stated rule.
The Tri-force (3, 6, 9, the Law of Three): each takes its own trigram doubled at any scale, 51 at 3, 1 at 6, 30 at 9. It touches the path of time and never the circuit.
Reading order (owner's rule, 4 Nov 2026): a circuit point's two lines are read interval trace first (1→4, 2→8, 5→7, inside the octave), octave trace second (4→2, 8→5, 7→1, leaving it), whichever is incoming. The two modes are the path of time (the circle, a period against its neighbors in time) and the circuit (each line by its one figure).
## Elements: the relation, the condition, the flow
One function, 
[code]
relation(actor, field), with the generative cycle Wood → Fire → Earth → Metal → Water → Wood and the controlling cycle Wood → Earth → Water → Fire → Metal → Wood:
[table]

|  | 
Relation | 
Rule | 
Word (condition) | 
Word (flow)
|  | 
resonates | 
actor = field | 
resonates | 
resonates
|  | 
fed_by | 
the field generates the actor | 
fed by | 
fed
|  | 
feeds | 
the actor generates the field | 
feeds | 
feeds
|  | 
controls | 
the actor controls the field | 
controls | 
controls
|  | 
controlled_by | 
the field controls the actor | 
controlled by | 
controlled
The condition is the native in the period: 
[code]
relation(nativeElement, periodElement). The native element is the element of the person's natal year number (a 5 native is earth); the period element is the element of the period's resolved trigram (a 5 period takes what it inherits). Its reading is 
[code]
CONDITION[native][period], one of the 25 texts in the next section. The page marks it on the rail and the plot and writes it quietly under the statement.
The flow is the period in its container: 
[code]
relation(periodElement, containerElement), the hour in the day, the day in the month, and so on; none at the top level. Its reading is 
[code]
CONDITION[period][container], the same table with the period as actor. The page shows it as the eyebrow (
[code]
Earth hour in a Metal day · feeds), folded since 11 Nov, and gives it to the writer.
Always name whose element it is (\"Your earth in an earth hour\"): an earth hour feeds its metal day while the earth native resonates in it, and without the subject the two read as a contradiction.
## The palace: Lo Shu flight, houses, flags, stars
The Lo Shu with south at the top, home arrangement 4 9 2 / 3 5 7 / 8 1 6. The period's global number takes the center and every other number flies the fixed path, so the number in a palace is 
[code]
ki(home − 5 + global). 
[code]
palace(global, personal) returns the nine cells (home, direction, number, element) and the flags:
[table]

|  | 
Flag | 
Rule
|  | 
Five Yellow | 
the home palace where 5 landed
|  | 
Broken | 
the palace opposite Five Yellow (
[code]
10 − home)
|  | 
Own | 
the home palace of the person's number at the level
|  | 
Opposite | 
the palace opposite Own
|  | 
Coincides | 
Own is the Five Yellow palace
The nine houses, with the direction and the line the reading leads with on the palace face (
[code]
HOUSES in briefs.js, from the 9 Nov 2026 handoff):
[table]

|  | 
House | 
Direction | 
Line
|  | 
1 | 
North | 
Winter. Dormancy and the hidden work; rest, plan, do not push.
|  | 
2 | 
South-west | 
Germination. Preparation, listening, slow groundwork; the risk is Stagnation.
|  | 
3 | 
East | 
Spring. Sudden starts and new energy that outruns its body; begin, but keep Composure.
|  | 
4 | 
South-east | 
Growth. Expansion, travel, communication; things take off and can scatter.
|  | 
5 | 
Center | 
The pivot. Everything comes to you and nothing is displaced; stay put, receive, do not initiate.
|  | 
6 | 
North-west | 
Authority. Responsibility and the first harvest; maturity with a perfectionist edge.
|  | 
7 | 
West | 
Harvest. Joy, money, reflection, pleasure and its excesses.
|  | 
8 | 
North-east | 
The turning point. Stillness before change; revolution held in the mountain.
|  | 
9 | 
South | 
Illumination. Recognition and exposure; things come to light.
On the palace face each number is headed by its traditional star, not the owner's point name: 1 White Water, 2 Black Earth, 3 Jade Wood, 4 Green Wood, 5 Yellow Earth, 6 White Metal, 7 Red Metal, 8 White Earth, 9 Purple Fire. 5 is the center there, with no trigram and no inheritance named. The palace steps one period at a time, reads no traces and no circuit; it is the house, the condition and the folded ba only.
## The ledger vocabulary: the nine points, the six lines, tending, families
All of this is data: 
[code]
src/ledger.js verbatim, 
[code]
src/briefs.js with the reading-view overrides. 
[code]
lib/forecast.js texts() returns 
[code]
BRIEF, CONDITION, HOUSES, RELATION_WORD, FLOW_WORD, STATEMENT, TRAD, TRAD_KEY, PAIRS, VERB, TENDING; dump it to JSON for Stella rather than retyping.
The nine points. Each has a name, a question, a function, an image, a shadow axis and a practice. The question is what every reading is built from.
[table]

|  | 
Point | 
Name | 
Question | 
Family
|  | 
1 | 
Potential | 
What's under the surface? | 
1·4·7 receptive
|  | 
2 | 
Field | 
What is being received? | 
2·5·8 substrate
|  | 
3 | 
Power | 
What arrived? | 
3·6·9 expansive
|  | 
4 | 
River | 
Which way? | 
1·4·7 receptive
|  | 
5 | 
Delta | 
What landed here from above? | 
2·5·8 substrate
|  | 
6 | 
Will | 
What was the ego magnetic to? | 
3·6·9 expansive
|  | 
7 | 
Lake | 
What is the yield? | 
1·4·7 receptive
|  | 
8 | 
Mountain | 
This is what lasted. Not touching it yet. | 
2·5·8 substrate
|  | 
9 | 
Clarity | 
What is clear from here? | 
3·6·9 expansive
The three forces take their own trigram doubled: 3 Power, 51 Shock, force from the outside in; 6 Will, 1 The Dynamic, force from the inside out, brought under will; 9 Clarity, 30 Clarity, the force that sees the two as one. Each point's function, image, shadow axis and practice are in 
[code]
BRIEF.
The six lines of the circuit, each a verb, a trace kind and a practice (
[code]
PAIRS, 
[code]
VERB):
[table]

|  | 
Line | 
Verb | 
Kind | 
Practice
|  | 
1 → 4 | 
nourish | 
interval trace | 
What the one day went under for, the four day points one way.
|  | 
4 → 2 | 
break | 
octave trace | 
The direction stops being something you steer and becomes something you give to the ground.
|  | 
2 → 8 | 
inherit | 
interval trace | 
2 says yes to everything; 8 keeps the one thing that lasted and holds it still, visible, not planted.
|  | 
8 → 5 | 
keep | 
octave trace | 
5 is the one place the day touches the larger cycle; 8 is the virtue that opens it.
|  | 
5 → 7 | 
reflect | 
interval trace | 
5 hands what it received to the lake. 7 sees the reflection, leaves it still, acts from it right away.
|  | 
7 → 1 | 
shape | 
octave trace | 
7 writes the sentence, acts once, closes the entry and does not reread it; 1 reads it.
Tending (owner, 10 Nov 2026): the three earth points are three scales of tending. 2 tends everything: all of it generated in the dark, in private, not for show. 5 tends the self: unblocking, whatever that means in the moment, mental, emotional or physical, so that what is coming through can land; not pushing outward. 8 tends one thing, with great care. An earth period closes on a tending at that scale, not a push; the other points are asked (Jev) whether they are a tending and at what scale, or none.
## The 25 condition readings, verbatim

[code]
CONDITION[actor][field], from the handoff \"Element Condition Table — Native in House\" (9 Nov 2026), respelled American on 10 Nov. Row = the actor (the native for the condition, the period for the flow); column = the field it stands in.
[table]

|  | 
Actor ↓ / Field → | 
Water | 
Wood | 
Fire | 
Earth | 
Metal
|  | 
Water | 
Deep water. Stillness doubled. Rest and listen; nothing here answers to force. | 
Water nourishing the root. You give and the field grows. Spend freely, but keep your source. | 
Water on flame. You cool the field; your restraint is wanted, but take care not to extinguish. | 
The river in its bank. The field contains you. Move within the channel; the limit is the gift. | 
Metal gathering dew. The field provides. Receive and collect; let it come to you.
|  | 
Wood | 
Roots in water. Growth is supported. Take it; this is the season to extend. | 
The forest. Growth crowds growth. Choose one trunk and prune the rest. | 
Wood becoming light. You are spent into the field's brightness. Glorious and consuming; keep a reserve. | 
Roots breaking soil. You draw from the field and it yields slowly. Push at a tree's pace, not a shoot's. | 
The axe. The field prunes you. Accept the cut; what remains is what grows.
|  | 
Fire | 
Flame under rain. Keep small and go inward. Protect the ember. | 
Dry fuel. The field feeds your flame. Abundant; watch for wildfire. | 
The blaze. Brilliance and exhaustion together. Shine, then rest before you are asked to. | 
Fire becoming ash. You give yourself to the field. An ending that fertilizes. | 
The forge. You shape the field; you are the smith. Patience with the heat.
|  | 
Earth | 
The bank shaping the river. You regulate the field. This is responsibility, not support. | 
Roots in the soil. The field draws on you. Yield; do not resist what is growing. | 
Ash enriching the ground. The field feeds you. A carried time; receive it. | 
Earth on earth. Weight and stillness. Nothing cuts, nothing pushes; the risk is Stagnation. Do not grasp. | 
Earth bearing ore. You give the field its form. It costs, and something is made.
|  | 
Metal | 
Metal yielding water. You are drained into flow. Let go; you are turning into motion. | 
The blade. You cut the field. Discernment: cut only what needs cutting. | 
In the forge. You are being reshaped by heat you did not choose. Hold form; submit to the work. | 
Ore in the mountain. The field holds and forms you. Rest in it. | 
Metal on metal. Sharpness doubled. Clarity or brittleness; do not over-cut.

[code]
COND_CLAUSE holds the short clause per pair that the composed statement appends to the point's question (Earth in Wood: \"with roots drawing on you\"); export it with the table.
## How the page composes a reading
The reading is a reading, not a system explanation (owner's rule): no attribute lists, no method words, no account of how the numbers are made. Explanation lives in the ledger view. The ledger text is verbatim; every reword for the reading is an override in briefs.js.
The head, on every face, in order:
[list]

- 
The number and the point's name (on the palace, the traditional star).
- 
One row: the 
[code]
now tag; on the octave face the two traces as ghost text (
[code]
2 → 8 inherit · 4 → 2 break, or 
[code]
Triforce · Power · the first force on 3, 6, 9); a 
[code]
+ that folds open the trigram and span line, the flow line (
[code]
Earth hour in a Metal day · feeds), the family and the stack of all levels.
- 
The statement. Without a profile, the point's plain question. With one, at first the composed sentence (
[code]
STATEMENT(q, rel): the question with the condition clause, \"What is being received, with roots drawing on you?\") and under it the quiet sentence (
[code]
TRAD(rel, level): \"Your earth in an earth hour. Weight and stillness. Nothing cuts, nothing pushes; the risk is Stagnation. Do not grasp.\"; the reading's opening image is kept as the clause unless it only restates the pair). Then the written thought replaces the composed sentence and the quiet sentence shrinks to its key, \"Your earth in an earth hour.\" (
[code]
TRAD_KEY).
- 
On the palace face, between the fold and the statement: 
[code]
House of N · direction · house line and the flags.
## The forecast pipeline
One paragraph per period, under Ji on the plot, behind a toggle. 
[code]
GET /api/forecast?level=&idx=&natal= → 
[code]
forecast() in lib/forecast.js, 
[code]
PROMPT_VERSION 4.
The packet (
[code]
packet(level, idx, natal)) is the deterministic half: the period and its span, the ba, the native, the ji and shi lines, the condition and the flow with their readings, the house, the point (name, question, image, practice, tending) and six sources, each in a short form for Jev and a full form for the writer: 
[code]
ba (the figure's text), 
[code]
ji (the ba's text at the ji lines), 
[code]
shi (the ba's text at the shi lines and where it lands), 
[code]
native (the native figure's text), 
[code]
point (the brief with the tending), 
[code]
ground (condition, flow, house).
Jev's read (
[code]
readQuestions), typed answers from TypeSafe's systemone API on the packet's state text:
[table]

|  | 
Question | 
Type | 
Choices
|  | 
lead | 
choice | 
ji (what the person meets) or shi (what is moving)
|  | 
stance | 
choice | 
one of the six verbs: nourish, break, inherit, keep, reflect, shape; its practice closes the paragraph
|  | 
motion | 
score | 
Still, Stirring, Moving, Turning, Breaking
|  | 
warning | 
noul | 
the period carries a warning to hear first
|  | 
w_ba, w_ji, w_shi, w_native, w_point, w_ground | 
score | 
background, supporting, central
The writer (one OpenAI-compatible chat call, reasoning off, 1,600 tokens) gets a system prompt composed from the read plus the rules: one paragraph of 70 to 110 words, second person, synthesis not summary, the image from the book's words at the lines, never the method's words, no numbers. The exact prompts are 
[code]
RULES, 
[code]
composeSystem and 
[code]
composeUser in lib/forecast.js.
Jev's grade (
[code]
GRADE_Q): synthesis (recites / mixed / one new thing, pass ≥ 1.2), usable (the person could act on it today, pass ≥ 0.45), method (talks about the method, pass ≤ 0.8). A failing draft is written once more with the verdict; the one with the higher synthesis is kept. Without a Jev key the writer runs unbriefed and ungraded.
Cache: 
[code]
DATA_DIR/forecasts.json, key 
[code]
v<PROMPT_VERSION>|model|level|idx|natal; 
[code]
?fresh=1 rewrites. 503 
[code]
no_key without 
[code]
OPENROUTER_API_KEY, 502 on a model failure.
## The written statement (v2): one thought under the headline

[code]
GET /api/statement?level=&idx=&natal= → 
[code]
statement(), 
[code]
STATEMENT_VERSION 2. One thought of two or three sentences, under fifty words, carrying the flow, the point's question and the condition in one voice; it replaces the composed sentence under the headline.
Jev decides (
[code]
statementQuestions), on the packet's state text plus the question and the composed sentence:
[table]

|  | 
Question | 
Type | 
Choices
|  | 
tending | 
choice, only for points other than 2, 5, 8 (theirs is fixed) | 
none, all, self, one
|  | 
stance | 
choice | 
one of the six verbs
|  | 
condition | 
score | 
Whisper (background), Present (one clause), Turn (the thought turns on it)
|  | 
flow | 
score, only where the period has a container | 
Whisper, Present (a few words), Turn (the thought opens on it)
|  | 
form | 
choice | 
ask (ends in a question the person carries) or tell (ends in a statement)
The writer (200 tokens) gets the frame, Jev's lines and the rules: two or three sentences, at most fifty words, as you, one voice telling one thing, something the question alone does not say, ending as Jev decided, never the method's words, no dashes. Exact text: 
[code]
ST_RULES, 
[code]
composeStatementSystem, 
[code]
composeStatementUser in lib/forecast.js.
The grade. Jev answers 
[code]
adds (restates / adds a little / says something new, pass ≥ 1.2), 
[code]
method (pass ≤ 0.8) and 
[code]
whole (one thought in one voice, not three facts, pass ≥ 0.5). The code counts the shape and asks no one: sentences ≤ 3, words ≤ 60, and whether it ends as Jev decided (
[code]
shapeOf). A failing thought, or one that ends the wrong way, is written once more with the verdict; the rewrite is kept if it passes where the first did not, then if it ends right, then if it adds more. If nothing passes, 
[code]
text is null and the composed sentence stays. 
[code]
tidy joins lines and turns dashes into commas.
Cache: 
[code]
s<STATEMENT_VERSION>|model|level|idx|natal in forecasts.json, with 
[code]
text, draft, composed, jev, grade, rewritten, at.
Still to tune: Jev answers ask and Turn almost every time; the writer slips element words in as things (\"earth on earth\").
## The reading of the thought (explain)

[code]
GET /api/explain?level=&idx=&natal= → 
[code]
explain(), 
[code]
EXPLAIN_VERSION 1 (11 Nov 2026). A tap on the written thought opens a window that reads it back the way a friend reads a poem with you: each phrase quoted and opened, the whole in one paragraph, questions to sit with, one closing line. Nothing marks the thought as tappable and nothing in the window names the method or the sources, by decision.
The writer (1,400 tokens) answers as JSON only, in this shape:
[code]
<\",\"meaning\":\"]]><\"}],\"whole\":\"]]><\",\"questions\":[\"]]><\"],\"close\":\"]]><\"}]]>
Rules: quotes copied exactly, in order, two to five, covering the passage; speak as you; an open image gets a few concrete alternatives, not one fixed reading; three to five first-person questions; no \"yes\", no praise, nothing outside the JSON; never a source, method, number, figure, line, trigram, hexagram, element or calendar. The user prompt is the passage plus, marked never to be named, the span in words, the point's question, the condition reading and the ji line's text. Exact text: 
[code]
EX_SYSTEM, 
[code]
exUser in lib/forecast.js.

[code]
parseExplain strips fences and preamble, parses the first 
[code]
{ to the last 
[code]
}, requires two or more parts, a whole, three or more questions and a close, and turns dashes into commas. A wrong shape is asked for once more; a second wrong shape is a 502 
[code]
shape.
Jev's grade: 
[code]
explains (restates / opens a little / opens it up, pass ≥ 1.2) and 
[code]
method (names the method, pass ≤ 0.8). A fail is written once more and the better kept; the reading is returned either way, with its grade.
Cache: 
[code]
x<EXPLAIN_VERSION>|model|level|idx|natal with 
[code]
of, the thought's text, so a rewritten thought gets a new reading. 404 
[code]
no_statement where no thought was written. The page keeps the readings per key for the session and shows \"Reading it…\" while one is written.
## Proposed Stella tools
The page's engine functions port one to one into 
[code]
ki_levels.py / 
[code]
octave.py: 
[code]
resolve, 
[code]
figure, 
[code]
moving, 
[code]
lineFigure, 
[code]
relation, 
[code]
palace, 
[code]
nativeFigure, 
[code]
numberAt, 
[code]
period, 
[code]
octave. The ledger tables ship as JSON dumped from 
[code]
texts(). The three model pipelines are the same shape each time: packet, Jev decides, writer phrases, Jev grades, one rewrite, cache keyed by version and period.
[table]

|  | 
Tool | 
Inputs | 
Returns | 
Maps to
|  | 

[code]
get_octave_period | 
level, datetime or idx, natal (optional) | 
the full packet: number, global, personal, span, ba, native, ji lines, shi lines and where they land, condition, flow, house, point (name, question, image, practice, tending), the six sources | 

[code]
packet()
|  | 

[code]
get_octave_condition | 
natal, level, datetime | 
the condition and the flow with their relation words and readings, the composed statement, the quiet sentence and its key | 

[code]
relation, 
[code]
CONDITION, 
[code]
STATEMENT, 
[code]
TRAD, 
[code]
TRAD_KEY
|  | 

[code]
get_native_figure | 
natal, level, datetime | 
the native hexagram, the ji lines, the ba's text at those lines | 

[code]
nativeFigure, 
[code]
moving, 
[code]
get_octave_reading
|  | 

[code]
get_octave_shi | 
level, datetime, natal (optional) | 
the lines that change into the next period, the ba's text at them, the next figure | 

[code]
moving, 
[code]
get_octave_reading
|  | 

[code]
get_palace | 
level, datetime, natal (optional) | 
the nine cells, the flags, the house line and direction, the star name | 

[code]
palace, 
[code]
HOUSES, 
[code]
STAR
|  | 

[code]
get_octave_point | 
number | 
the point's brief: name, question, function, image, shadow, practice, family, tending; the reading-view overrides applied | 

[code]
BRIEF, 
[code]
TENDING
|  | 

[code]
get_octave_line | 
from, to | 
the line's verb, kind, what changes, practice, its figure | 

[code]
PAIRS, 
[code]
VERB, 
[code]
lineFigure
|  | 

[code]
write_octave_statement | 
natal, level, datetime, fresh (optional) | 
the written thought with Jev's read and grade, or null with the composed sentence | 

[code]
statement()
|  | 

[code]
explain_octave_statement | 
natal, level, datetime | 
the reading of the thought: parts, whole, questions, close | 

[code]
explain()
|  | 

[code]
write_octave_forecast | 
natal, level, datetime, fresh (optional) | 
the paragraph with Jev's read and grade | 

[code]
forecast()
One skill alongside them, the Octave reading: how to read a period for a person in the page's order (head, condition, ji, shi, in practice), with the rules below as its constraints. The ledger itself (
[code]
LPOINTS, 
[code]
LLINKS, 
[code]
LRULES, 
[code]
LREADINGS, 
[code]
LLOG, 
[code]
LARCHIVE) is the knowledge base the skill cites; Stella's 
[code]
knowledge_search could index it as is.
## Sources of truth, routes, env, standing rules
Repo: 
[code]
HermesNode/octave, its own git repo, remote github.com/PoweredbyPugs/octave-calendar, branch 
[code]
feat/palace-field-ji (main untouched at 8a175fd; merging is the owner's call). 
[code]
CLAUDE.md there is the running record of every decision by date. Live on punk as the Docker container 
[code]
octave at http://192.168.1.181:3333; 
[code]
sh scripts/deploy-punk.sh tests, builds and deploys.
Routes: 
[code]
/api/reading?hexagram=&lines=&full=, 
[code]
/api/forecast, 
[code]
/api/statement, 
[code]
/api/explain (each 
[code]
?level=&idx=&natal=[&fresh=1]), 
[code]
/api/profiles, 
[code]
/api/health.
Env: 
[code]
TYPESAFE_API_KEY (Jev; the same key 
[code]
jev setup-key keeps in 
[code]
~/.config/jev/credentials), 
[code]
OPENROUTER_API_KEY, 
[code]
FORECAST_MODEL (default 
[code]
deepseek/deepseek-v4.1-flash), 
[code]
FORECAST_URL (default OpenRouter, any OpenAI-compatible endpoint), 
[code]
DATA_DIR, 
[code]
GNOSTIC_JSON. Keys live in 
[code]
.env beside docker-compose.yml on punk, gitignored and never rsynced.
Standing rules (the owner's, dated in CLAUDE.md):
[list]

- 
The reading is a reading, not a system explanation: no attribute lists, no method words, no account of the mechanics in anything a person reads. Explanation lives in the ledger.
- 
The ledger text is verbatim; change it in the study ledger first. Rewords for the reading are overrides in briefs.js.
- 
Jev decides and grades; Jev never writes. Never ask Jev what code can count (sentences, words, an ending).
- 
The forecast and the statement are synthesis, \"something new, not a cookbook recipe\".
- 
Always say whose element it is (\"Your earth in an earth hour\"); never the bare pair.
- 
American spelling everywhere. No em-dashes in page text (the pipelines turn them into commas). No emoji in UI.
- 
UI names: the three faces octave, plot, palace; the path of time and the circuit; Tri-force with the hyphen; Ba, Shi, Ji, In Practice. The ledger keeps rim, hexad, Triforce.
Related docs: the 9 Nov handoff with the 10 Nov decisions, \"Element Condition Table — Native in House\" (https://claude.ai/artifact/EyRtSczvedVHHHzdxW5ir7); the original page artifact, version 10 of 30 Oct 2026 (https://claude.ai/artifact/MQaUNrWKB41ZAgyNZuCZ8v). Parked: the Japanese names for the three lenses (wa, kairo, mitsudomoe); the 9 and 10 Nov ledger touches not yet mirrored into the Ki Octave Study page.","complete":true},"frame":{"slug":"bcb5bbbe-ebc5-4781-90d0-7a150cdd942a","url":"https://claude.ai/artifact/QJZHtLnVMwKxfB3M6owWjb","artifactUrl":"https://claude.ai/artifact/QJZHtLnVMwKxfB3M6owWjb"}}

This doc takes suggestions. Rewording what is already here ("tighten", "improve", "review", "clean up", "this is clunky") → lay the changes in the doc as suggestions: guide( items = ["topic.index", "topic.suggestions"] ) first. Small fixes met on the way (a typo) go in as suggestions with them. The same when asked to suggest, propose or mark up, when the person wants to look before it goes in, and for a question that invites changes ("Any suggestions?", "What would you change?"): suggestions in the doc on this reply, not a list in chat and not comments. An ask for only an exact fix (a typo, a stated fact), new content, a delete or a move → save the edit as usual; the same in a doc you made in this chat, for a rewrite of the whole doc, when told to edit directly, and on an unattended run. While the person is in Suggesting mode, lay it as a suggestion. The person tells you in chat to go ahead with suggestions you laid on an earlier reply ("go ahead", "do the second one") → accept the ones they mean, one call each (topic.suggestions), rather than write the change again. Any other question about the doc → answer in chat.