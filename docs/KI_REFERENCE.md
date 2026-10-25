# 9 Star Ki Reference

## Overview

9 Star Ki is a Japanese adaptation of Chinese Feng Shui astrology based on the Lo Shu magic square. It calculates three numbers from a birth date that describe personality, relationships, and life cycles.

## The Three Numbers

| # | Name | Meaning |
|---|------|---------|
| **1st (Year Ki)** | Essence | Invisible to self — the iceberg below water. Governs the parts of ourselves we can't see. Works in conjunction with natal chart. |
| **2nd (Month Ki)** | Emotion | Internal processing, the heart, qualities/abilities, strengths/weaknesses, potential trauma triggers. Under stress, we resort to the **shadow qualities** of this number. |
| **3rd Ki** | Life Path | How people see you externally + contextualizes the nodes, career, societal roles, larger lessons, the mirror we must see through on our journey. |

### Psychological Integration
- **Essence** weaves with the natal chart's hidden elements
- **Emotion** connects to Moon themes and attachment patterns  
- **Life Path** connects to nodal story and career arc

## The Lo Shu Square

The magic square where all rows, columns, and diagonals sum to 15:

```
4 | 9 | 2      SE | S  | SW
---------      -----------
3 | 5 | 7  →   E  | ☯  | W  
---------      -----------
8 | 1 | 6      NE | N  | NW
```

Palace numbers are FIXED positions. Ki numbers FLY through them.

## The Nine Stars

| Ki | Trigram | Name | Element | Qualities |
|----|---------|------|---------|-----------|
| 1 | ☵ | Water (Kan) | Water | Adaptable, deep, mysterious, diplomatic |
| 2 | ☷ | Earth (Kun) | Earth | Nurturing, supportive, receptive, devoted |
| 3 | ☳ | Thunder (Zhen) | Wood | Pioneering, enthusiastic, impulsive, direct |
| 4 | ☴ | Wind (Xun) | Wood | Gentle, penetrating, communicative, flexible |
| 5 | ☯ | Center (Tai Chi) | Earth | Powerful, controlling, central, transformative |
| 6 | ☰ | Heaven (Qian) | Metal | Authoritative, leader, father, structured |
| 7 | ☱ | Lake (Dui) | Metal | Joyful, charming, reflective, expressive |
| 8 | ☶ | Mountain (Gen) | Earth | Still, contemplative, stubborn, transitional |
| 9 | ☲ | Fire (Li) | Fire | Illuminating, visible, passionate, clarity |

## Calculating Natal Ki

### Year Ki
- Changes on **February 4** (Lichun/Spring Begins), not January 1
- Cycles: 9 → 8 → 7 → 6 → 5 → 4 → 3 → 2 → 1 → 9...
- Reference: 2026 = Ki year 1

### Month Ki  
- Changes mid-month on specific dates (varies by month)
- Starting month (February) depends on year Ki group:
  - Years 1, 4, 7 → February = 8
  - Years 2, 5, 8 → February = 5
  - Years 3, 6, 9 → February = 2

### Third Ki
- Derived from Year + Month using Flying Star Lo Shu method
- Put Month Ki in center, find which palace Year Ki occupies

## Flying Star Method

When a number is placed in the center, all other numbers shift according to the flying sequence:

```
5 → 6 → 7 → 8 → 9 → 1 → 2 → 3 → 4 → (back to 5)
```

**Example:** Year=5, Month=4, find Third
1. Put 4 in center (palace 5)
2. Everything shifts +1 in sequence
3. 5 moves from palace 5 → palace 6
4. Third = **6**

## Personal Cycles

### Personal Year
Where your **natal Year Ki** lands when the **global Year Ki** is in center.

Example: Natal 5 in global year 1
- Put 1 in center
- Where does 5 land? → Palace **9**
- Personal year = 9 (Fire)

### Personal Month
Where your **natal Year Ki** lands when the **global Month Ki** is in center.

Example: Natal 5 in global month 8
- Put 8 in center  
- Where does 5 land? → Palace **2**
- Personal month = 2 (Earth)

**Note:** Both personal year AND personal month use the natal YEAR Ki.

## Element Relationships

**Productive Cycle (feeds):**
Wood → Fire → Earth → Metal → Water → Wood

**Controlling Cycle (disciplines):**
Wood → Earth → Water → Fire → Metal → Wood

## Stella Tools

```bash
# Get natal Ki
npx mcporter call stella.get_ki birth_date=1986-05-01

# Get global Ki for a date
npx mcporter call stella.get_ki date=2026-02-05

# Get full profile with personal cycle
npx mcporter call stella.get_ki_cycle birth_date=1986-05-01
```

## Integration with I Ching

The 9 Ki trigrams map directly to I Ching trigrams. A reading can combine:
1. Natal Ki profile (who you are)
2. Personal cycle (where you are now)  
3. I Ching hexagram (specific guidance)

The trigrams in a cast hexagram can be interpreted through Ki lens for elemental synthesis.

## Timekeeping Stack and the 5 Rule

Two different uses of 5, kept apart:

- **Reading** (the natal triple; `get_ki`, `get_ki_cycle`, `get_ki_reading`, `get_ki_transition`):
  three numbers, no hierarchy. A 5 in the middle takes on the other numbers' character; the
  doubling rule in `ki_reading.py` stays. What a 5 in the first position means (e.g. 5.9.1) is a
  doctrinal question, not decided in code.
- **Timekeeping** (`get_octave`, `get_ki_changes`, `ki_change_*`, `get_ki_change_schedule`,
  `get_daily_ki`): the chain hour → day → month → year → great year → Ki Age → great age. Ki 5 has
  no trigram and inherits the trigram of the nearest level above it that is not 5
  (`hub_inheritance.py`). A 5 over 5 is the parent's trigram doubled. Every figure names what was
  inherited. Moving lines are always the line-by-line difference between two figures.

Two chains, never mixed: every global level is a Lo Shu number descending 1 per period; every
personal level is the natal year read against the matching global level by
`personal(natal, global) = ki(natal − global + 5)`. A personal 5 inherits up the personal chain only.

| Level | Length | Global anchor (`ki_levels.py`, `ki_solar.py`) |
|---|---|---|
| hour | 5′ of the Sun, 12 per day | opening = 3·day + 8 (day 8 opens hour 5) |
| day | 1° of the Sun, 30 per month | every Lichun opens day 8 |
| month | Sun at 15° of each sign | Feb 2026 = 8, one continuous count |
| year | Lichun to Lichun, 360° of the Sun | 2026 = 1 |
| great year | 12 years | Lichun 2010 opens 2 (2022 opens 1, 2034 opens 9) |
| Ki Age | 144 years | Lichun 2010 opens 5 |
| great age | 1,728 years, 24° of precession | Lichun 2010 opens 8 |

The day and hour are the Sun too, not the clock: a day is one degree past Lichun (23.5 to 25.2
hours, breathing with the Sun's speed) and an hour one twelfth of that. Twelve of anything is its
parent, nine of anything is one cycle of its numbers, so every level opens on an Earth number and
the running count is the lock. The great age is one fifteenth of the 25,920-year precession cycle;
the vernal point reached 24° past the Lahiri sidereal zero (285 CE) in 2010, and the gate is the
Lichun before the crossing. Lichun 2010 therefore opened the great age, the Ki Age and the great
year together and the stack read 8 · 5 · 2 · 8 · 2 · 8 · 5, each level three below the one above.
A level is Earth at its own seam only when its parent turns too. The remaining choice is the
sidereal zero (Krishnamurti also gives 2010; Fagan-Bradley 1938; Raman 2106).
