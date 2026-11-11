# BaZi Reference — conventions, tables, sources

Stella's BaZi (八字, Four Pillars of Destiny) is traditional Zi Ping (子平). It lives in
`bazi.py` (calculation), `bazi_tables.py` (every table) and `bazi_render.py` (Markdown), and is
exposed as `get_bazi`, `get_bazi_luck_pillars` and `get_bazi_time_pillars`. It is computed
entirely on Stella with pyswisseph; Helios is touched only to fetch a chart Stella has not
stored. It shares the solar-term instants with the Ki calendar and nothing else: BaZi is here
for its own sake and is not mapped onto the Ki stack.

The tools compute. The reader interprets. Where the tradition is contested the output shows
the components (season, roots, support; structure, balance, climate) rather than one verdict.

## Settled mechanics

| Pillar | Rule |
|---|---|
| Year | Changes at the exact Lichun instant (Sun at 315°). 1984 is 甲子; 2024 is 甲辰. |
| Month | Changes at the twelve jie, the Sun at 15° of each sign (`ki_calendar.boundaries_jd`). 寅 opens at Lichun. Stem by the Five Tigers rule (五虎遁): year stem 甲/己 → 丙寅, 乙/庚 → 戊寅, 丙/辛 → 庚寅, 丁/壬 → 壬寅, 戊/癸 → 甲寅. |
| Day | Sexagenary index `(JDN + 49) mod 60`, 甲子 = 0, where JDN is the Julian Day Number of the civil date after the day-boundary rule. 1900-01-01 is 甲戌; 2000-01-01 is 戊午. |
| Hour | Twelve double-hours, 子 spanning 23:00–01:00. Stem by the Five Rats rule (五鼠遁): day stem 甲/己 → 甲子, 乙/庚 → 丙子, 丙/辛 → 戊子, 丁/壬 → 庚子, 戊/癸 → 壬子. |

## The two contested mechanics (parameters)

**`true_solar_time` (default on).** The birth clock is converted to apparent solar time
before the day boundary and the hour are read: standard time (daylight saving removed)
+ 4 minutes per degree of longitude east of the zone's standard meridian + the equation of
time (`swe.time_equ`). A 22:50 clock birth with a +20 minute correction is 23:10 and, under
the 23:00 boundary, takes the next day's pillar. This is what Chinese calculators do; Joey
Yap's calculator reads clock time. The year and month pillars always use the true instant.
With no coordinates the tools fall back to clock time and say so in the first line.

**`day_boundary` (default `"23:00"`).** The day pillar changes at the start of the Zi hour.
`"midnight"` keeps the civil date for the day pillar and derives the 23:00–00:00 hour stem from
the next day's stem (the early/late Zi convention, 早子/晚子).

## Tables

**Hidden stems (藏干), primary first:** 子 癸 · 丑 己癸辛 · 寅 甲丙戊 · 卯 乙 · 辰 戊乙癸 · 巳 丙庚戊 ·
午 丁己 · 未 己丁乙 · 申 庚壬戊 · 酉 辛 · 戌 戊辛丁 · 亥 壬甲.

**Ten Gods (十神)** by the other stem's relation and polarity to the Day Master: same element
比肩 Friend / 劫財 Rob Wealth; Day Master produces 食神 Eating God / 傷官 Hurting Officer; Day
Master controls 偏財 Indirect Wealth / 正財 Direct Wealth; controls the Day Master 七殺 Seven
Killings / 正官 Direct Officer; produces the Day Master 偏印 Indirect Resource / 正印 Direct
Resource. The first of each pair is the same polarity.

**Twelve life stages (十二長生):** 長生 starts at 亥 for 甲, 午 for 乙, 寅 for 丙 and 戊, 酉 for 丁
and 己, 巳 for 庚, 子 for 辛, 申 for 壬, 卯 for 癸. Yang stems count forward, yin stems backward
(陰逆, the classical table). Reported for the reader; it does not feed the strength verdict.

**Seasonal states (旺相休囚死):** the Day Master's element against the month's season (寅卯 wood,
巳午 fire, 申酉 metal, 亥子 water, 辰戌丑未 earth): 旺 in its own season, 相 when the season
produces it, 休 when it produces the season, 囚 when it controls the season, 死 when the season
controls it.

**Strength verdict:** strong when in season (旺/相) with a root in any branch or a supporting
stem; weak when out of season without both a root and support; otherwise middling. The
method is printed with every verdict.

**Structure (格局), Ziping Zhenquan:** 建祿格 when the month branch is the Day Master's 祿
branch; 月刃格 when it is a yang stem's 刃 branch; 月劫格 when a yin stem's month primary qi is
劫財. Otherwise the structure is taken from the month branch's hidden stems that are not 比肩
or 劫財: the first of them revealed in the year, month or hour stem (primary, then middle, then
residual), else the primary unrevealed. In the storage months 辰戌丑未 the result is a 雜氣
structure (e.g. 雜氣正官格). Special structures (從格, 專旺) are listed as candidates when their
precondition holds, never asserted.

**Nayin (納音):** the standard thirty names from 海中金 (甲子乙丑) to 大海水 (壬戌癸亥).

**Void (空亡):** by the decade of the day pillar: 甲子旬 戌亥, 甲戌旬 申酉, 甲申旬 午未, 甲午旬 辰巳,
甲辰旬 寅卯, 甲寅旬 子丑.

**Interactions:** stem combinations 甲己土 乙庚金 丙辛水 丁壬木 戊癸火 (transforms only when the
product is the month's season element); six combinations 子丑土 寅亥木 卯戌火 辰酉金 巳申水 午未土;
trines 申子辰水 亥卯未木 寅午戌火 巳酉丑金 (a half trine is any pair that includes the peak);
directional 寅卯辰木 巳午未火 申酉戌金 亥子丑水; clashes 子午 丑未 寅申 卯酉 辰戌 巳亥; harms 子未 丑午
寅巳 卯辰 申亥 酉戌; destructions 子酉 丑辰 寅亥 卯午 巳申 未戌; punishments 寅巳申 (any pair), 丑戌未
(any pair), 子卯, and the self-punishments 辰 午 酉 亥. A full trine or directional is reported
once as a triple, not again as its pairs.

**Symbolic stars, the core set.** Stem-cast from the day stem (and the year stem for 天乙):
天乙貴人 Nobleman (甲戊庚 丑未, 乙己 子申, 丙丁 亥酉, 辛 午寅, 壬癸 巳卯, per 淵海子平 / 三命通會; the
協紀辨方書 variant gives 庚 → 寅午 and is footnoted when 庚 is the caster), 文昌 Academic Star
(甲巳 乙午 丙申 丁酉 戊申 己酉 庚亥 辛子 壬寅 癸卯), 祿神 Prosperity (甲寅 乙卯 丙巳 丁午 戊巳 己午 庚申
辛酉 壬亥 癸子), 羊刃 Goat Blade (yang stems only: 甲卯 丙午 戊午 庚酉 壬子). Branch-cast from both
the year and the day branch: 桃花 Peach Blossom (申子辰 酉, 亥卯未 子, 寅午戌 卯, 巳酉丑 午), 驛馬
Travelling Horse (申子辰 寅, 亥卯未 巳, 寅午戌 申, 巳酉丑 亥), 孤辰 / 寡宿 Solitary / Widow (亥子丑
寅/戌, 寅卯辰 巳/丑, 巳午未 申/辰, 申酉戌 亥/未). Every hit names the pillar it was cast from.

**Luck pillars (大運):** forward for yang-year males and yin-year females, backward otherwise.
Start age is the days from the true birth instant to the next (forward) or previous
(backward) jie at three days per year, one day per four months, one double-hour per ten days.
Pillars run through the sexagenary sequence from the natal month pillar, ten years each.

## Reference charts (tests pin these)

Two independent calculators were used on 2026-11-11. buyiju.com (clock time, no solar
correction) and china95.net (which offers 真太阳时). Both agree with Stella on every chart below.

| Chart | Birth | Pillars | Stem Ten Gods | Primary-qi Ten Gods |
|---|---|---|---|---|
| Betsy | 1978-11-20 22:31 New York | 戊午 癸亥 丙戌 己亥 | 食神 正官 日主 傷官 | 劫財 七殺 食神 七殺 |
| Chris | 1986-05-01 14:35 New York | 丙寅 壬辰 乙巳 癸未 | 傷官 正印 日主 偏印 | 劫財 正財 傷官 偏財 |
| y2k | 2000-01-01 00:30 Shanghai | 己卯 丙子 戊午 壬子 | 劫財 偏印 日主 偏財 | 正官 正財 正印 正財 |

| Sydney | 1990-01-15 10:00 Australia/Sydney | 己巳 丁丑 庚辰 辛巳 | | |
| 1960 | 1960-08-08 03:00 Shanghai | 庚子 甲申 戊辰 甲寅 | 食神 七殺 日主 七殺 | 正財 食神 比肩 七殺 |

china95 also confirms the direction of true solar time: 2000-06-01 09:05 Beijing time at 105°E is
the 巳 hour on the clock and the 辰 hour (庚辰) in apparent time. Its luck-pillar start ages (2 for
the y2k chart, 10 for the 1960 chart, in nominal years) match Stella's day counts. It shows 立夏
2000 at 13:19 Beijing where the Swiss Ephemeris gives 12:50 (Sun at exactly 45°); Stella uses the
ephemeris instant, so near a jie the two can differ by that half hour.

Published anchors: 1900-01-01 甲戌 day; Mao Zedong 1893-12-26 辰時 癸巳 甲子 丁酉 甲辰.

Caveat: buyiju.com is a calendar-date tool. Asked for 2024-02-04 at 15:00 and 17:00 Beijing
time, one hour either side of Lichun (16:27), it returned 癸卯 丙寅 for both, an old year stem
with the new year's month stem. Stella changes both pillars at the instant (癸卯 乙丑 before,
甲辰 丙寅 after), so that site cannot validate boundary behaviour.

## Sources

淵海子平 (Yuanhai Ziping), 三命通會 (Sanming Tonghui), 滴天髓 (Di Tian Sui, Ren Tieqiao commentary),
子平真詮 (Ziping Zhenquan), 窮通寶鑑 (Qiongtong Baojian), with Xu Leu's annotations as the modern
reading of them. The full 調候 table of Qiongtong Baojian is not in the code; the tools give the
season and climate facts and the reader applies it.
