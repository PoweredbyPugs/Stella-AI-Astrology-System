"""Zodiacal releasing: loosing of the bond, angular triads, period windows.

Run: .venv/bin/python -m pytest tests/test_zr.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zr import (
    calculate_zr,
    get_triad_phase,
    get_angularity_from_fortune,
    house_from,
    zr_periods,
    ZRPeriod,
)

BIRTH = datetime(2000, 1, 1, 12, 0)
D = timedelta(days=1)

# Twelve signs of sub-periods: 211 "years" of the level's unit.
L2_CYCLE = 211 * 30          # days
L3_CYCLE = 211 * 30 / 12     # 527.5 days


def l2_at(offset_days, lot="Capricorn", fortune="Aries"):
    return calculate_zr(lot, 0.0, BIRTH, BIRTH + timedelta(days=offset_days),
                        "spirit", fortune_sign=fortune)


# ── Loosing of the bond ────────────────────────────────────────────────────

def test_l2_runs_twelve_signs_from_the_l1_sign_before_the_loosing():
    snap = l2_at(L2_CYCLE - 1)
    assert snap.L1.sign == "Capricorn"
    assert snap.L2.sign == "Sagittarius"            # 12th sign from Capricorn
    assert snap.L2.end == BIRTH + timedelta(days=L2_CYCLE)
    assert snap.L2.is_pre_loosing is True
    assert snap.L2.is_loosing_of_bond is False
    assert snap.is_loosing_of_bond is False


def test_l2_jumps_to_the_opposite_sign_at_the_loosing():
    snap = l2_at(L2_CYCLE + 1)
    assert snap.L2.sign == "Cancer"                  # opposite Capricorn, not Capricorn again
    assert snap.L2.start == BIRTH + timedelta(days=L2_CYCLE)
    assert snap.L2.end == snap.L2.start + timedelta(days=25 * 30)
    assert snap.L2.is_loosing_of_bond is True
    assert snap.L2.is_pre_loosing is False
    assert snap.is_loosing_of_bond is True
    assert "Cancer" in snap.loosing_details and "Capricorn" in snap.loosing_details


def test_l2_continues_in_order_after_the_jump():
    snap = l2_at(L2_CYCLE + 25 * 30 + 1)
    assert snap.L2.sign == "Leo"
    assert snap.L2.is_loosing_of_bond is True        # still in the loosed portion


def test_parent_records_when_its_subperiods_loose():
    snap = l2_at(10)
    assert snap.L1.loosing_at == BIRTH + timedelta(days=L2_CYCLE)
    # L2 Capricorn lasts 810 days, long enough for L3 to complete a cycle
    assert snap.L2.loosing_at == BIRTH + timedelta(days=L3_CYCLE)


def test_short_period_has_no_loosing():
    # L1 Taurus (8 years = 2880 days) is shorter than the 6330-day L2 cycle
    snap = calculate_zr("Taurus", 0.0, BIRTH, BIRTH + 10 * D, "spirit", fortune_sign="Aries")
    assert snap.L1.loosing_at is None
    # L2 Taurus (240 days) is shorter than the 527.5-day L3 cycle
    assert snap.L2.loosing_at is None
    assert snap.L2.is_pre_loosing is False


def test_l3_jumps_to_opposite_sign_within_a_long_l2():
    snap = l2_at(L3_CYCLE + 0.5)
    assert snap.L2.sign == "Capricorn"
    assert snap.L3.sign == "Cancer"
    assert snap.L3.start == BIRTH + timedelta(days=L3_CYCLE)
    assert snap.L3.is_loosing_of_bond is True
    before = l2_at(L3_CYCLE - 0.5)
    assert before.L3.sign == "Sagittarius"
    assert before.L3.is_pre_loosing is True


def test_last_subperiod_is_cut_at_the_parent_end():
    # Capricorn L1 = 9720 days. After the loosing at 6330: Cancer 750, Leo 570,
    # Virgo 600, Libra 240, Scorpio 450, Sagittarius 360 -> 9300; Capricorn would run to 10110.
    snap = l2_at(9500)
    assert snap.L2.sign == "Capricorn"
    assert snap.L2.start == BIRTH + timedelta(days=9300)
    assert snap.L2.end == BIRTH + timedelta(days=9720)
    assert snap.L2.end == snap.L1.end


def test_fortune_cancer_l1_looses_to_capricorn_then_aquarius():
    # Gemini Fortune: L1 Gemini 7200 days, then Cancer. Cancer's L2 cycle ends 6330 days in.
    cancer_start = 7200
    snap = calculate_zr("Gemini", 0.0, BIRTH, BIRTH + timedelta(days=cancer_start + L2_CYCLE + 1),
                        "fortune", fortune_sign="Gemini")
    assert snap.L1.sign == "Cancer"
    assert snap.L2.sign == "Capricorn"
    assert snap.L2.end == BIRTH + timedelta(days=cancer_start + L2_CYCLE + 810)
    later = calculate_zr("Gemini", 0.0, BIRTH, BIRTH + timedelta(days=cancer_start + L2_CYCLE + 811),
                         "fortune", fortune_sign="Gemini")
    assert later.L2.sign == "Aquarius"
    assert later.L2.ruler == "Saturn"


# ── Spirit and Fortune in the same sign ────────────────────────────────────

def test_spirit_in_fortunes_sign_releases_from_the_next_sign():
    snap = calculate_zr("Scorpio", 5.0, BIRTH, BIRTH + 10 * D, "spirit", fortune_sign="Scorpio")
    assert snap.lot_sign == "Scorpio"
    assert snap.release_sign == "Sagittarius"
    assert snap.L1.sign == "Sagittarius"
    assert snap.L1.end == BIRTH + timedelta(days=12 * 360)


def test_fortune_in_its_own_sign_releases_from_itself():
    snap = calculate_zr("Scorpio", 5.0, BIRTH, BIRTH + 10 * D, "fortune", fortune_sign="Scorpio")
    assert snap.release_sign == "Scorpio"
    assert snap.L1.sign == "Scorpio"


# ── Angular triads and classification from Fortune ─────────────────────────

def test_house_angularity_and_phase_from_fortune():
    f = "Gemini"
    assert house_from("Gemini", f) == 1
    assert house_from("Pisces", f) == 10
    assert get_angularity_from_fortune("Gemini", f) == "angular"
    assert get_angularity_from_fortune("Cancer", f) == "succedent"
    assert get_angularity_from_fortune("Taurus", f) == "cadent"
    assert get_triad_phase("Taurus", f) == "preparatory"     # cadent sign before the angle
    assert get_triad_phase("Gemini", f) == "peak"            # Fortune itself
    assert get_triad_phase("Cancer", f) == "completion"      # succedent sign after
    assert get_triad_phase("Leo", f) == "preparatory"        # 3rd, before the 4th
    assert get_triad_phase("Virgo", f) == "peak"             # 4th
    assert get_triad_phase("Libra", f) == "completion"
    assert get_triad_phase("Aquarius", f) == "preparatory"   # 9th, before the 10th
    assert get_triad_phase("Pisces", f) == "peak"            # 10th
    assert get_triad_phase("Aries", f) == "completion"


def test_period_carries_phase_and_classification():
    snap = calculate_zr("Capricorn", 0.0, BIRTH, BIRTH + 10 * D, "spirit", fortune_sign="Gemini")
    p = snap.L1
    assert p.sign == "Capricorn"
    assert p.house_from_fortune == 8
    assert p.angularity == "succedent"
    assert p.phase == "completion"
    assert p.peak_type is None
    d = p.to_dict()
    for key in ("house_from_fortune", "angularity", "phase", "loosing_at",
                "is_loosing_of_bond", "is_pre_loosing"):
        assert key in d
    assert d["loosing_at"] == (BIRTH + timedelta(days=L2_CYCLE)).isoformat()


# ── Periods over a window ──────────────────────────────────────────────────

def test_zr_periods_returns_every_period_overlapping_the_window():
    start = BIRTH + timedelta(days=L2_CYCLE - 100)
    end = BIRTH + timedelta(days=L2_CYCLE + 100)
    result = zr_periods("Capricorn", BIRTH, start, end, levels=(1, 2), lot_name="spirit",
                        fortune_sign="Aries")
    assert [p.sign for p in result["L1"]] == ["Capricorn"]
    l2 = result["L2"]
    assert [p.sign for p in l2] == ["Sagittarius", "Cancer"]
    assert l2[0].is_pre_loosing and l2[1].is_loosing_of_bond
    assert l2[0].end == l2[1].start
    assert all(isinstance(p, ZRPeriod) for p in l2)


def test_zr_periods_descends_through_parents_without_gaps():
    start = BIRTH + 800 * D
    end = BIRTH + 830 * D                     # spans the L2 Capricorn -> Aquarius change at 810
    result = zr_periods("Capricorn", BIRTH, start, end, levels=(2, 3), lot_name="spirit",
                        fortune_sign="Aries")
    assert [p.sign for p in result["L2"]] == ["Capricorn", "Aquarius"]
    l3 = result["L3"]
    assert l3[0].start <= start and l3[-1].end >= end
    for a, b in zip(l3, l3[1:]):
        assert a.end == b.start
    # the first L3 of the new L2 starts in the L2's own sign, at the L2 start
    first_aq = next(p for p in l3 if p.start == BIRTH + 810 * D)
    assert first_aq.sign == "Aquarius"
    # and the last L3 of the old L2 is cut at the L2 end
    last_cap = next(p for p in l3 if p.end == BIRTH + 810 * D)
    assert last_cap.end == BIRTH + 810 * D


# ── Report ─────────────────────────────────────────────────────────────────

def _chart(fortune="Gemini", spirit="Scorpio"):
    return {
        "birthData": {"date": "2000-01-01", "time": "12:00:00"},
        "lots": {"fortune": {"sign": fortune, "degreeInSign": "8.8"},
                 "spirit": {"sign": spirit, "degreeInSign": "22.9"}},
        "sect": {"isDaySect": True},
        "planets": [{"name": "Saturn", "sign": "Capricorn"}],
    }


def test_zr_report_releases_the_requested_lot():
    from zr_report import generate_zr_report
    from zr import zr_for_chart
    chart = _chart()
    target = BIRTH + timedelta(days=7200 + L2_CYCLE + 1)   # Fortune L1 Cancer, just past the loosing
    md = generate_zr_report(chart, target, lot="fortune")
    snap = zr_for_chart(chart, target, "fortune")
    assert snap.L1.sign == "Cancer" and snap.L2.sign == "Capricorn"
    assert "Releasing from: **Fortune**" in md
    assert "**L1: Cancer**" in md and "**L2: Capricorn**" in md
    assert "Loosing of the Bond" in md and "Capricorn" in md
    spirit_md = generate_zr_report(chart, target, lot="spirit")
    assert "Releasing from: **Spirit**" in spirit_md
    assert "**L1: Scorpio**" not in md and "**L1: " in spirit_md


def test_zr_report_marks_peaks_from_fortune_not_from_the_released_lot():
    from zr_report import generate_zr_report
    chart = _chart(fortune="Gemini", spirit="Scorpio")
    md = generate_zr_report(chart, BIRTH + 10 * D, lot="spirit", format="json")
    assert md["periods"]["L1"]["sign"] == "Scorpio"
    assert md["periods"]["L1"]["is_peak"] is False          # Scorpio is 6th from Gemini
    assert md["periods"]["L1"]["phase"] == "preparatory"


def test_zr_report_json_has_the_worksheet_sections():
    from zr_report import generate_zr_report
    data = generate_zr_report(_chart(), BIRTH + 10 * D, lot="fortune", format="json")
    for key in ("lot", "lots", "peaks", "triads", "sect", "planets_by_phase", "periods", "loosing"):
        assert key in data, key
    assert data["lot"] == "fortune"
    assert data["peaks"]["10th"]["sign"] == "Pisces"
    assert data["periods"]["L1"]["sign"] == "Gemini"
    assert data["loosing"]["L1_loosing_at"] == (BIRTH + timedelta(days=L2_CYCLE)).isoformat()


# ── Level 6 ───────────────────────────────────────────────────────────────

L6_CYCLE = 211 * 30 / 20736  # days: 211 units of ~2.08 minutes, ~7.3 hours


def test_l6_unit_is_a_twelfth_of_l5():
    from zr import LEVEL_MULTIPLIERS, MAX_LEVEL
    assert MAX_LEVEL == 6
    assert abs(LEVEL_MULTIPLIERS[6] - LEVEL_MULTIPLIERS[5] / 12) < 1e-15


def test_l6_jumps_to_opposite_sign_within_a_long_l5():
    # Capricorn L5 = 27 units of 25 min = 11.25 h, longer than the L6 cycle.
    snap = l2_at(L6_CYCLE + 0.0005)
    assert snap.L5.sign == "Capricorn"
    assert snap.L6.sign == "Cancer"
    assert snap.L6.start == BIRTH + timedelta(days=L6_CYCLE)
    assert snap.L6.is_loosing_of_bond is True
    assert snap.L5.loosing_at == BIRTH + timedelta(days=L6_CYCLE)
    before = l2_at(L6_CYCLE - 0.0005)
    assert before.L6.sign == "Sagittarius"
    assert before.L6.is_pre_loosing is True
    assert snap.to_dict()["L6"]["level"] == 6
    assert len(snap.levels) == 6


def test_zr_periods_accepts_level_6():
    out = zr_periods("Capricorn", BIRTH, BIRTH, BIRTH + timedelta(hours=3), levels=[6], fortune_sign="Aries")
    assert [p.sign for p in out["L6"][:3]] == ["Capricorn", "Aquarius", "Pisces"]
    assert out["L6"][0].start == BIRTH
    assert out["L6"][0].end == BIRTH + timedelta(days=27 * 30 / 20736)
