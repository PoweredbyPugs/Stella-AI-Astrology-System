"""BaZi analysis: Ten Gods, tallies, life stages, void, strength, structure.

Reference Ten God rows from buyiju.com (2026-11-11):
  Betsy stems 食神 正官 日主 傷官; primary-qi 劫財 七殺 食神 七殺
  Chris stems 傷官 正印 日主 偏印; primary-qi 劫財 正財 傷官 偏財
  y2k   stems 劫財 偏印 日主 偏財; primary-qi 正官 正財 正印 正財

Run: .venv/bin/python -m pytest tests/test_bazi_analysis.py
"""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bazi import analyze, life_stage, pillars_from_civil, sexagenary, sexagenary_index, ten_god  # noqa: E402

NY = ZoneInfo("America/New_York")
SH = ZoneInfo("Asia/Shanghai")
BETSY = pillars_from_civil(datetime(1978, 11, 20, 22, 31, tzinfo=NY))
CHRIS = pillars_from_civil(datetime(1986, 5, 1, 14, 35, tzinfo=NY))
Y2K = pillars_from_civil(datetime(2000, 1, 1, 0, 30, tzinfo=SH))
ORDER = ("year", "month", "day", "hour")


def pillars(year, month, day, hour):
    """Build a pillars dict from four (stem, branch) index pairs."""
    return {k: sexagenary(sexagenary_index(*sb)) for k, sb in zip(ORDER, (year, month, day, hour))}


def test_ten_god_relations():
    assert ten_god(2, 2) == "比肩" and ten_god(2, 3) == "劫財"       # 丙 vs 丙, 丁
    assert ten_god(2, 4) == "食神" and ten_god(2, 5) == "傷官"       # 丙 produces 戊, 己
    assert ten_god(2, 6) == "偏財" and ten_god(2, 7) == "正財"       # 丙 controls 庚, 辛
    assert ten_god(2, 8) == "七殺" and ten_god(2, 9) == "正官"       # 壬, 癸 control 丙
    assert ten_god(2, 0) == "偏印" and ten_god(2, 1) == "正印"       # 甲, 乙 produce 丙


def test_ten_gods_rows_match_reference():
    for p, stems, primaries in (
        (BETSY, ["食神", "正官", "日主", "傷官"], ["劫財", "七殺", "食神", "七殺"]),
        (CHRIS, ["傷官", "正印", "日主", "偏印"], ["劫財", "正財", "傷官", "偏財"]),
        (Y2K, ["劫財", "偏印", "日主", "偏財"], ["正官", "正財", "正印", "正財"]),
    ):
        a = analyze(p)
        assert [a["ten_gods_stems"][k] for k in ORDER] == stems
        assert [a["ten_gods_hidden"][k][0] for k in ORDER] == primaries


def test_ten_gods_carry_pinyin_and_english():
    a = analyze(BETSY)
    assert a["day_master"]["cn"] == "丙" and a["day_master"]["element"] == "fire"
    assert a["ten_gods_detail"]["year"]["pinyin"] == "shi shen"
    assert a["ten_gods_detail"]["year"]["en"] == "Eating God"


def test_hidden_stems_listed_per_pillar():
    a = analyze(BETSY)
    assert [s["cn"] for s in a["hidden"]["month"]] == ["壬", "甲"]
    assert [s["cn"] for s in a["hidden"]["day"]] == ["戊", "辛", "丁"]


def test_tallies_betsy():
    a = analyze(BETSY)
    assert a["tally_visible"] == {"metal": 0, "wood": 0, "water": 3, "fire": 2, "earth": 3}
    assert a["tally_all"]["wood"] == 2          # 甲 in both 亥
    assert a["tally_all"]["metal"] == 1         # 辛 in 戌


def test_life_stage_yin_runs_backward():
    assert life_stage(1, 6) == "長生"     # 乙 in 午
    assert life_stage(0, 11) == "長生"    # 甲 in 亥
    assert life_stage(9, 3) == "長生"     # 癸 in 卯
    assert life_stage(0, 3) == "帝旺"     # 甲 in 卯
    assert life_stage(1, 2) == "帝旺"     # 乙 in 寅
    assert [analyze(BETSY)["life_stages"][k] for k in ORDER] == ["帝旺", "絕", "墓", "絕"]   # 丙 in 午 亥 戌 亥


def test_void_from_day_pillar():
    assert [b["cn"] for b in analyze(BETSY)["void"]["branches"]] == ["午", "未"]   # 丙戌 in 甲申 decade
    assert [b["cn"] for b in analyze(CHRIS)["void"]["branches"]] == ["寅", "卯"]   # 乙巳 in 甲辰 decade
    assert analyze(BETSY)["void"]["pillars"] == ["year"]                            # Betsy's 午 is void


def test_strength_components_named():
    s = analyze(BETSY)["strength"]
    assert set(s) >= {"season_state", "rooted", "support", "verdict", "method"}
    assert s["season_state"] == "死"            # 丙 fire in the 亥 month
    assert s["rooted"] is True                  # 丁 inside 午
    assert s["support"] == 0                    # no fire or wood stem among the other three
    assert s["verdict"] == "weak"


def test_strength_strong_case():
    s = analyze(pillars((2, 2), (0, 6), (2, 6), (2, 2)))["strength"]   # 丙 in 午, with 甲 and 丙 stems
    assert s["season_state"] == "旺" and s["verdict"] == "strong"


def test_structure_ziping_zhenquan():
    b = analyze(BETSY)["structure"]
    assert b["name"] == "七殺格" and b["qi_used"] == "壬" and b["revealed"] is False
    assert analyze(Y2K)["structure"]["name"] == "正財格"
    assert analyze(pillars((2, 2), (2, 2), (0, 2), (2, 2)))["structure"]["name"] == "建祿格"   # 甲 in 寅
    assert analyze(pillars((2, 2), (3, 3), (0, 2), (2, 2)))["structure"]["name"] == "月刃格"   # 甲 in 卯
    assert "Ziping Zhenquan" in b["basis"]


def test_structure_prefers_revealed_middle_qi():
    # 甲 day, 壬申 month (申 hides 庚 壬 戊): 庚 not revealed, 壬 revealed → 偏印格 on 壬
    s = analyze(pillars((2, 2), (8, 8), (0, 2), (2, 2)))["structure"]
    assert s["name"] == "偏印格" and s["qi_used"] == "壬" and s["revealed"] is True


def test_special_structure_candidates_flagged_not_asserted():
    a = analyze(pillars((6, 10), (6, 10), (0, 10), (6, 10)))   # 甲戌 among 庚戌: no wood or water anywhere
    assert a["structure"]["special_candidates"]
    assert all("candidate" in c for c in a["structure"]["special_candidates"])
    assert analyze(BETSY)["structure"]["special_candidates"] == []


def test_climate():
    c = analyze(BETSY)["climate"]
    assert c["season"] == "winter" and c["temperature"] == "cold"
    assert "fire" in c["tempering"]


# ── Review fixes: 格局 must follow 祿 / 刃 / 庫 rules; 從格 flag must not fire on a 比肩 stem ──

def test_structure_jianlu_only_when_month_is_the_lu_branch():
    # 甲 in 亥 with 甲 revealed: 甲's 祿 is 寅, so no 建祿; 比劫 skipped → primary 壬 unrevealed → 偏印格
    s = analyze(pillars((0, 0), (1, 11), (0, 2), (0, 0)))["structure"]
    assert s["name"] == "偏印格" and s["qi_used"] == "壬" and s["revealed"] is False
    assert analyze(pillars((2, 2), (9, 5), (4, 6), (8, 0)))["structure"]["name"] == "建祿格"   # 戊 in 巳 (戊祿在巳)


def test_structure_yuere_and_yuejie():
    assert analyze(pillars((2, 2), (0, 6), (4, 6), (8, 0)))["structure"]["name"] == "月刃格"   # 戊 in 午 (yang 刃)
    assert analyze(pillars((2, 2), (4, 2), (1, 3), (2, 0)))["structure"]["name"] == "月劫格"   # 乙 in 寅 (yin: 月劫)


def test_structure_storage_month_uses_zaqi():
    # 戊 in 辰 (戊 乙 癸) with 乙 revealed in the year stem → 雜氣正官格
    s = analyze(pillars((1, 3), (4, 4), (4, 6), (8, 0)))["structure"]
    assert s["name"] == "雜氣正官格" and s["qi_used"] == "乙" and s["revealed"] is True
    # 戊 in 辰 with nothing revealed → middle qi 乙, unrevealed
    s = analyze(pillars((2, 2), (4, 4), (4, 6), (2, 4)))["structure"]
    assert s["name"] == "雜氣正官格" and s["revealed"] is False


def test_follow_structure_not_flagged_when_a_friend_stem_exists():
    a = analyze(pillars((0, 10), (6, 6), (0, 6), (5, 5)))   # 甲戌 庚午 甲午 己巳: year stem 甲 is a 比肩
    assert a["structure"]["special_candidates"] == []
