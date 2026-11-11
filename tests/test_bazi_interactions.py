"""BaZi interactions (combinations, clashes, harms, punishments, destructions) and core stars.

Run: .venv/bin/python -m pytest tests/test_bazi_interactions.py
"""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bazi import interactions, pillars_from_civil, sexagenary, sexagenary_index, stars  # noqa: E402
from bazi_tables import CLASHES, DESTRUCTIONS, HARMS  # noqa: E402

NY = ZoneInfo("America/New_York")
BETSY = pillars_from_civil(datetime(1978, 11, 20, 22, 31, tzinfo=NY))   # 戊午 癸亥 丙戌 己亥
CHRIS = pillars_from_civil(datetime(1986, 5, 1, 14, 35, tzinfo=NY))     # 丙寅 壬辰 乙巳 癸未
ORDER = ("year", "month", "day", "hour")


def pillars(*sb):
    return {k: sexagenary(sexagenary_index(*p)) for k, p in zip(ORDER, sb)}


def kinds(p):
    return {(i["type"], tuple(m[0] for m in i["members"])) for i in interactions(p)}


def test_betsy_interactions():
    k = kinds(BETSY)
    assert ("stem_combination", ("year", "month")) in k          # 戊癸 → fire
    assert ("half_trine", ("year", "day")) in k                  # 午戌 → fire
    assert ("self_punishment", ("month", "hour")) in k           # 亥亥, once
    assert sum(1 for t, _ in k if t == "self_punishment") == 1
    combo = next(i for i in interactions(BETSY) if i["type"] == "stem_combination")
    assert combo["element"] == "fire" and combo["transforms"] is False   # 亥 month is water, not fire


def test_chris_interactions():
    k = kinds(CHRIS)
    assert ("punishment", ("year", "day")) in k                  # 寅巳
    assert ("harm", ("year", "day")) in k                        # 寅巳 is also a harm
    assert not any(set(m) == {"month", "day"} for _, m in k)     # 辰巳: nothing
    assert not any(set(m) == {"day", "hour"} for _, m in k)      # 巳未: nothing


def test_full_trine_and_directional():
    k = kinds(pillars((0, 2), (2, 6), (4, 10), (0, 2)))          # 寅午戌 across year/month/day
    assert ("trine", ("year", "month", "day")) in k
    assert not any(t == "half_trine" for t, _ in k)             # a full trine is not also three halves
    k = kinds(pillars((1, 11), (0, 0), (5, 1), (1, 11)))         # 亥子丑
    assert ("directional", ("year", "month", "day")) in k


def test_clash_harm_destruction_tables_complete():
    for table in (CLASHES, HARMS, DESTRUCTIONS):
        assert len(table) == 6
        assert len({frozenset(p) for p in table}) == 6
    k = kinds(pillars((0, 0), (2, 6), (0, 0), (2, 6)))           # 子午 twice over
    assert ("clash", ("year", "month")) in k and ("clash", ("day", "hour")) in k


def test_six_combination_and_transform_flag():
    i = [x for x in interactions(pillars((0, 2), (9, 11), (0, 2), (0, 2))) if x["type"] == "six_combination"]
    assert i and i[0]["element"] == "wood"                       # 寅亥 → wood


def test_stars_name_cast_pillar():
    s = stars(BETSY)
    hits = {(h["star_cn"], h["found_in"], h["cast_from"]) for h in s["hits"]}
    assert ("天乙貴人", "month", "day") in hits and ("天乙貴人", "hour", "day") in hits   # 丙 → 亥酉
    assert ("羊刃", "year", "day") in hits                                             # 丙 → 午
    assert ("孤辰", "month", "day") in hits                                            # day 戌 → 亥
    assert not any(h["star_cn"] in ("桃花", "驛馬", "文昌", "祿神") for h in s["hits"])
    assert all(h["star_en"] for h in s["hits"])


def test_stars_chris():
    # 丙寅 壬辰 乙巳 癸未: 乙 → 天乙 子申, 文昌 午, 祿 卯, no 羊刃; 寅 → 桃花 卯, 驛馬 申; 巳 → 桃花 午, 驛馬 亥
    hits = {(h["star_cn"], h["found_in"], h["cast_from"]) for h in stars(CHRIS)["hits"]}
    assert hits == {("孤辰", "day", "year"), ("寡宿", "month", "day")}   # 寅卯辰 → 孤辰 巳; 巳午未 → 寡宿 辰


def test_tianyi_footnote_present_once():
    s = stars(pillars((6, 8), (6, 8), (6, 8), (6, 8)))           # 庚 everywhere
    assert len(s["footnotes"]) == 1 and "協紀辨方書" in s["footnotes"][0]
    assert stars(BETSY)["footnotes"] == []
