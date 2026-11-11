# Stella feature: BaZi (Four Pillars of Destiny)

Agreed in conversation on 2026-11-10 between Chris and Claude.

## Intent

Add traditional BaZi (八字, Four Pillars) to Stella so it can be used in practice on the
stored charts and on the present moment, to see what the system offers and how its readings
differ from the Western and Ki tools. BaZi is here for its own sake. It is built the way a
classically trained Zi Ping (子平) practitioner would build it, and it is **not** mapped onto
the Ki stack, the octave, or any model Stella already has. The Ki calendar and BaZi happen
to share the Lichun gate and the twelve jie solar terms, so they share the boundary code
in `ki_calendar.py`; they share nothing else. Where BaZi doctrine and Ki doctrine differ,
BaZi wins inside BaZi.

The tools compute facts. The LLM reading those facts is the intelligence layer, and it
should read as a traditionally trained practitioner, not one modern school. So the tools
must surface everything such a practitioner would look at, in traditional vocabulary, and
must not collapse the contested parts of the tradition into a single verdict.

## Where it lives

On Stella's server, not Helios. Helios is a Western-chart Swiss Ephemeris wrapper and knows
nothing of stems and branches. BaZi needs only the Sun's longitude (already in-process via
pyswisseph and `ki_calendar.py`) and arithmetic. No Helios call, no new dependency.

## Goals

1. **Natal four pillars** for a stored chart (by name) or raw birth data (date, time,
   place, time zone, gender). Each pillar carries its stem and branch in Chinese characters,
   pinyin and English element/polarity, plus its Nayin (納音).
2. **The traditional reading data** a Zi Ping practitioner lays out before reading:
   - Day Master (日主): stem, element, polarity.
   - Hidden stems (藏干) for every branch, primary qi first.
   - Ten Gods (十神) for every visible stem and every hidden stem, relative to the Day
     Master, in Chinese, pinyin and English.
   - Five-element tally: counts of each element across the eight characters, and a second
     tally that includes hidden stems.
   - Day Master strength, reported as its components and then a verdict: seasonal command
     (得令, the Day Master's **element** in the month by the five seasonal states 旺相休囚死,
     not the twelve-stage table), rooting (得地, roots in the branches), support (得勢,
     same-element and resource stems). The verdict names the method so the LLM can disagree.
   - Chart structure (格局) by the Ziping Zhenquan rules, labelled as such: the month
     branch's primary qi if revealed in a stem; otherwise a revealed middle qi (中氣) before a
     revealed residual qi (餘氣); otherwise the primary qi unrevealed. When the chosen qi is
     比肩 or 劫財 the structure is 建祿格 or 月刃格 (陽刃格) respectively. Special structures
     (從格 and friends) are flagged as possibilities, never asserted.
   - Season of birth and climate: the month's season, whether the chart runs hot, cold, dry
     or damp, and which elements would temper it. This is the raw material for seasonal
     adjustment (調候); the full 120-entry Qiongtong Baojian table is a non-goal for v1.
   - Interactions among the four pillars, each one named and located: stem combinations
     (天干五合, with the transformed element and whether it can transform), branch six
     combinations (六合), three combinations (三合, full and half), directional combinations
     (三會), clashes (六沖), harms (六害), punishments (三刑, 自刑), destructions (破).
   - Twelve life stages (十二長生) of the Day Master in each branch, using the classical
     convention that yin stems run backward (陰逆), labelled as such. This line is reported
     for the reader; it does not feed the strength verdict (see 得令 above).
   - Void branches (空亡) from the day pillar.
   - A core set of symbolic stars (神煞), limited to the ones nearly every school uses:
     Nobleman (天乙貴人), Peach Blossom (桃花), Travelling Horse (驛馬), Academic Star
     (文昌), Prosperity (祿神), Goat Blade (羊刃), Solitary and Widow (孤辰寡宿). No more
     without a source. Branch-cast stars (桃花, 驛馬, 孤辰寡宿) are cast from both the year
     branch and the day branch; stem-cast stars (天乙, 文昌, 祿, 羊刃) from the day stem, with
     the year stem as a second reference for 天乙. Every hit names the pillar it was cast
     from. 天乙貴人 uses the Yuanhai Ziping / Sanming Tonghui table (庚 → 丑未); the output
     notes the Xieji Bianfang Shu variant (庚 → 寅午) once, as a footnote, not as extra hits.
3. **Luck pillars (大運).** Start age from the days between birth and the nearest jie
   (forward for yang-year males and yin-year females, backward otherwise), at three days
   per year, one day per four months, one double-hour per ten days. Ten pillars, each with
   its exact start date, stems and branches, Ten Gods, and interactions with the natal
   pillars. Report the current luck pillar.
4. **Time pillars for any instant.** The year, month, day and hour pillars at a given date
   and time (default: now, in the chart's time zone or New York if no chart). Against a
   natal chart: Ten Gods of the annual (流年), monthly (流月) and daily pillars relative to
   the Day Master, and their interactions with the natal pillars and the current luck
   pillar.
5. **Two contested mechanics are parameters**, with the defaults stated in every tool's
   docstring:
   - `true_solar_time` (default `True`): the birth instant is converted to apparent solar
     time, that is standard time corrected for the place's longitude against its zone
     meridian and for the equation of time, **before** the day-boundary rule and the hour
     pillar are read. So a 22:50 clock birth with a +20 minute correction is 23:10 and, under
     the `"23:00"` boundary, takes the next day's pillar. This is the Chinese-calculator
     convention. `False` uses clock time throughout. Fixtures state which setting they were
     pinned with, since Joey Yap's calculator reads clock time and the Chinese ones read
     apparent time.
   - `day_boundary` (default `"23:00"`): the day pillar changes at the start of the Zi hour.
     The alternative `"midnight"` keeps the day pillar until 00:00 but derives the 23:00 to
     00:00 hour stem from the next day's day stem (the early/late Zi convention, 早子/晚子).
6. **Validated against independent calculators.** Tests pin the pillars of at least six
   charts checked against two independent sources (Joey Yap's online calculator and one
   Chinese calculator such as Wenmo Tianji or the Wenzhen BaZi site), covering both
   day-boundary conventions, a birth within an hour of a jie, a Southern Hemisphere birth,
   and a pre-1950 birth. Betsy's stored chart is one of the six.

## Non-goals

- Any bridge to Ki, the octave, hub inheritance, or Convergence Ki. No shared numbers.
- Ingesting BaZi texts into Neo4j. The LLM's own knowledge reads the facts for now; source
  texts can come later if the readings earn it.
- The full seasonal-adjustment (調候用神) table, Blind School (盲派) methods, Zi Wei Dou Shu,
  minor luck pillars (小運), the long tail of symbolic stars, Southern Hemisphere element
  reversal, and any scoring that reduces a chart to a single number.
- Changing any existing tool.

## Anti-goals (would make it a failure even if it ran)

- Quietly blending BaZi with Ki, in code or in output.
- Presenting one school's useful god (用神) as the answer. The tools give structure, balance
  and season; the reader weighs them.
- Inventing a symbolic star, a hidden stem, or an interaction that is not in the tables.
- An hour pillar that silently uses clock time.

## Mechanics that are settled (the builder implements these as written)

- **Year pillar** changes at the exact Lichun instant (`ki_calendar.lichun_jd`). 1984 is a
  甲子 year; 2024 is 甲辰.
- **Month pillar** changes at the twelve jie, the Sun at 15° of each sign
  (`ki_calendar.boundaries_jd`). Month index 0 (opens at Lichun) is 寅. Month stem by the
  Five Tigers rule (五虎遁): year stem 甲/己 → 丙寅, 乙/庚 → 戊寅, 丙/辛 → 庚寅, 丁/壬 → 壬寅,
  戊/癸 → 甲寅, then counting on.
- **Day pillar** is the sexagenary index `(JDN + 49) mod 60` with 甲子 = 0, where JDN is the
  Julian Day Number of the local civil date (after the day-boundary rule is applied).
  Fixtures: 1900-01-01 is 甲戌 (index 10); 2000-01-01 is 戊午 (index 54).
- **Hour pillar**: twelve double-hours, 子 spanning 23:00 to 01:00. Hour stem by the Five
  Rats rule (五鼠遁): day stem 甲/己 → 甲子, 乙/庚 → 丙子, 丙/辛 → 戊子, 丁/壬 → 庚子, 戊/癸 →
  壬子, then counting on.
- **True solar time**: local standard time (DST removed via `zoneinfo`) + 4 minutes per
  degree of longitude east of the zone's meridian + equation of time (pyswisseph
  `swe.time_equ`). Zone meridian is derived from the zone's standard UTC offset at that
  instant, not the DST offset.
- **Hidden stems** (primary first): 子 癸 · 丑 己癸辛 · 寅 甲丙戊 · 卯 乙 · 辰 戊乙癸 · 巳 丙庚戊 ·
  午 丁己 · 未 己丁乙 · 申 庚壬戊 · 酉 辛 · 戌 戊辛丁 · 亥 壬甲.
- **Ten Gods** by element relation and polarity to the Day Master: same element same
  polarity 比肩 Friend, same element other polarity 劫財 Rob Wealth; Day Master produces:
  食神 Eating God (same polarity), 傷官 Hurting Officer; Day Master controls: 偏財 Indirect
  Wealth (same), 正財 Direct Wealth; controls Day Master: 七殺 Seven Killings (same), 正官
  Direct Officer; produces Day Master: 偏印 Indirect Resource (same), 正印 Direct Resource.
- **Luck pillars** run through the sexagenary sequence from the month pillar, forward or
  backward by the gender and year-stem polarity rule above. The first pillar is the one
  after (or before) the natal month pillar.

## Input and output

- Stored charts come in two shapes and both must load: the Helios shape with
  `birthInfo.dateTime` (e.g. `November 20, 1978 10:31:00 PM`), `birthInfo.coordinates`,
  `birthInfo.timezone` and top-level `gender` (betsy.json), and the older shape with
  `birthData = {date, time, timezone, location{latitude, longitude}}` and usually no gender
  (most of `charts/`). Chart lookup uses the existing local-then-Helios loader; that is
  chart storage, not computation, and is the one Helios touch allowed. Raw birth data
  accepts an ISO local datetime, latitude, longitude, an IANA zone and gender.
- Every tool takes an optional `gender` argument that overrides or supplies the chart's.
  With no gender from either source, luck pillars are omitted and the output says why.
- With no coordinates, true solar time is impossible: the tool computes on clock time and
  the output opens with a one-line warning saying so. Never silently.
- Tools are `@mcp.tool()` async functions in `stella_server.py` returning Markdown, in the
  style of the Ki tools: the doctrine in the docstring, the data in tables, Chinese
  characters with pinyin and English on every stem, branch and Ten God. A `format="json"`
  option returns the same data as JSON for other consumers.
- Births before the zone's recorded history or with no zone fall back to local mean time
  and say so in the output.

## Constraints

- Python 3.11, stdlib plus pyswisseph. No new packages. No Helios calls.
- One new module (suggested `bazi.py`) owning all tables and calculation, importing
  boundary helpers from `ki_calendar.py`. Tool functions in `stella_server.py` are thin.
- Tests in `tests/` with pytest, including the six validated charts, the two day-boundary
  conventions, true solar time against a hand-computed case, luck-pillar start ages in both
  directions, and every interaction table against at least one known example.
- `TOOLS.md`, `README.md` and `CHANGELOG.md` updated; a `docs/BAZI_REFERENCE.md` that
  states the conventions, the tables, and their sources, in the manner of `KI_REFERENCE.md`.

## Left to the builder

- Tool names and how many tools (one per goal 1 to 4 is the natural split).
- Internal data classes, Markdown layout, and the exact weights inside the strength verdict,
  provided the components are reported separately.
- Which Chinese calculator to use for validation, and the six fixture charts beyond Betsy.
- How the two stored-chart shapes are normalised internally.
- Whether `get_timing_stack` later gains a BaZi section. Not in this work.
