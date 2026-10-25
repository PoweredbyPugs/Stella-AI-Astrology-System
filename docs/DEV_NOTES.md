# Dev notes

Internal working notes. Not features, not promises; things to revisit.

## Later

- **Specific Ki numbers per body in `get_natal_gates`.** The tool gives each body's 15° gate and
  the family of three numbers that gate can carry; it does not say which of the three was live at
  birth, because that depends on the count at that level at the birth instant. Adding it means
  choosing a level per body (Sun → natal month Ki, Moon → lunar-gate count at birth, ascendant →
  hour-level gate count) and that is a doctrinal choice before it is a code one. Note the Sun
  already disagrees across lattices: 11° Taurus sits in the 0° Taurus gate of the 24-gate lattice
  (2 · 5 · 8) but in the Ki month that opened at 15° Aries (natal month 9). Parked 2026-10-20;
  not worth the effort until a reading needs it.
- **Ki Age and great age anchors** (Lichun 2010 opens great age 8, Ki Age 5, great year 2; set
  2026-10-25). The great age is anchored by precession: 24° of the vernal point past the Lahiri
  zero, gate at the Lichun before the crossing. The one remaining choice is the sidereal zero:
  Krishnamurti gives the same 2010 gate, Fagan-Bradley 1938, Raman 2106. Constants in
  `ki_levels.py`. The octave app's `lib/ki/kimonths.ts` still has the old 2022 = 8 great year.
- **What a 5 in the first position of a natal triple means** (e.g. 5.9.1): a knowledge-graph
  question, not decided in code.
