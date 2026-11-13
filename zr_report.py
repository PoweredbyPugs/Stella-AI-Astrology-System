"""
Zodiacal Releasing Report Module
Comprehensive ZR analysis using Chris Brennan's worksheet framework.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from zr import zr_for_chart, ZRSnapshot, SIGN_YEARS, opposite_sign

SIGN_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

MODALITIES = {
    "Cardinal": ["Aries", "Cancer", "Libra", "Capricorn"],
    "Fixed": ["Taurus", "Leo", "Scorpio", "Aquarius"],
    "Mutable": ["Gemini", "Virgo", "Sagittarius", "Pisces"],
}

RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}


def get_sign_index(sign: str) -> int:
    return SIGN_ORDER.index(sign)


def get_sign_at_offset(start_sign: str, offset: int) -> str:
    start_idx = get_sign_index(start_sign)
    return SIGN_ORDER[(start_idx + offset) % 12]


def get_modality(sign: str) -> str:
    for mod, signs in MODALITIES.items():
        if sign in signs:
            return mod
    return "Unknown"


def get_angular_signs_from_fortune(fortune_sign: str) -> Dict[str, Dict]:
    """
    Calculate peak periods from Lot of Fortune.
    Returns the 4 angular signs with their peak type.
    """
    fortune_idx = get_sign_index(fortune_sign)
    
    return {
        "fortune": {
            "sign": fortune_sign,
            "type": "Major Peak",
            "position": "Fortune itself",
            "emoji": "💕"
        },
        "4th": {
            "sign": get_sign_at_offset(fortune_sign, 3),  # 4th sign
            "type": "Minor Peak",
            "position": "4th from Fortune (first square)",
            "emoji": "💕"
        },
        "7th": {
            "sign": get_sign_at_offset(fortune_sign, 6),  # 7th sign (opposition)
            "type": "Moderate Peak", 
            "position": "7th from Fortune (opposition)",
            "emoji": "❤️"
        },
        "10th": {
            "sign": get_sign_at_offset(fortune_sign, 9),  # 10th sign
            "type": "Major Peak",
            "position": "10th from Fortune",
            "emoji": "💕💕"
        }
    }


def get_angular_triads(fortune_sign: str) -> List[Dict]:
    """
    Generate the 4 angular triads based on Fortune's modality.
    Each triad: Preparatory (fixed) -> Peak (mutable) -> Completion (cardinal)
    """
    modality = get_modality(fortune_sign)
    
    # Determine which modality is which phase based on Fortune's modality
    if modality == "Mutable":
        prep_mod = "Fixed"
        peak_mod = "Mutable"
        comp_mod = "Cardinal"
    elif modality == "Fixed":
        prep_mod = "Cardinal"
        peak_mod = "Fixed"
        comp_mod = "Mutable"
    else:  # Cardinal
        prep_mod = "Mutable"
        peak_mod = "Cardinal"
        comp_mod = "Fixed"
    
    triads = []
    
    # Build 4 triads starting from each element
    element_starts = {
        "Earth": "Taurus" if prep_mod == "Fixed" else ("Capricorn" if prep_mod == "Cardinal" else "Virgo"),
        "Fire": "Leo" if prep_mod == "Fixed" else ("Aries" if prep_mod == "Cardinal" else "Sagittarius"),
        "Water": "Scorpio" if prep_mod == "Fixed" else ("Cancer" if prep_mod == "Cardinal" else "Pisces"),
        "Air": "Aquarius" if prep_mod == "Fixed" else ("Libra" if prep_mod == "Cardinal" else "Gemini"),
    }
    
    # Reorder based on Fortune's modality for proper sequence
    for element, prep_sign in element_starts.items():
        prep_idx = get_sign_index(prep_sign)
        peak_sign = SIGN_ORDER[(prep_idx + 1) % 12]
        comp_sign = SIGN_ORDER[(prep_idx + 2) % 12]
        
        triads.append({
            "name": f"{element} Phase",
            "preparatory": {"sign": prep_sign, "modality": prep_mod},
            "peak": {"sign": peak_sign, "modality": peak_mod},
            "completion": {"sign": comp_sign, "modality": comp_mod},
        })
    
    return triads


def get_sect_planets(chart_data: Dict) -> Dict[str, Dict]:
    """Extract sect-based planet rankings from chart data."""
    sect = chart_data.get("sect", {})
    planets = chart_data.get("planets", [])
    
    # Build planet lookup
    planet_signs = {}
    planet_dignities = {}
    for p in planets:
        planet_signs[p["name"]] = p.get("sign", "")
        planet_dignities[p["name"]] = p.get("dignities", {})
    
    is_day = sect.get("isDaySect", True)
    
    result = {
        "sect": "Day" if is_day else "Night",
        "most_positive": {
            "planet": "Jupiter" if is_day else "Venus",
            "sign": planet_signs.get("Jupiter" if is_day else "Venus", ""),
            "role": "In-sect benefic"
        },
        "most_negative": {
            "planet": "Mars" if is_day else "Saturn",
            "sign": planet_signs.get("Mars" if is_day else "Saturn", ""),
            "role": "Contrary-sect malefic"
        },
        "moderate_benefic": {
            "planet": "Venus" if is_day else "Jupiter",
            "sign": planet_signs.get("Venus" if is_day else "Jupiter", ""),
            "role": "Contrary-sect benefic"
        },
        "moderate_malefic": {
            "planet": "Saturn" if is_day else "Mars",
            "sign": planet_signs.get("Saturn" if is_day else "Mars", ""),
            "role": "In-sect malefic"
        }
    }
    
    # Add dignity info
    for key in ["most_positive", "most_negative", "moderate_benefic", "moderate_malefic"]:
        planet = result[key]["planet"]
        dig = planet_dignities.get(planet, {})
        if dig:
            condition = dig.get("condition", "neutral")
            result[key]["condition"] = condition
            if dig.get("domicile"):
                result[key]["dignity"] = "Domicile"
            elif dig.get("exaltation"):
                result[key]["dignity"] = "Exalted"
            elif dig.get("detriment"):
                result[key]["dignity"] = "Detriment"
            elif dig.get("fall"):
                result[key]["dignity"] = "Fall"
    
    return result


def get_planets_by_modality(chart_data: Dict) -> Dict[str, List[Dict]]:
    """Group planets by the modality of their sign."""
    planets = chart_data.get("planets", [])
    
    result = {"Fixed": [], "Mutable": [], "Cardinal": []}
    
    for p in planets:
        name = p.get("name", "")
        sign = p.get("sign", "")
        if not sign or not name:
            continue
        # Skip outer planets and nodes for this analysis
        if name in ["Uranus", "Neptune", "Pluto", "North Node", "Chiron"]:
            continue
        mod = get_modality(sign)
        if mod in result:
            result[mod].append({
                "planet": name,
                "sign": sign,
            })
    
    return result


def is_peak_period(sign: str, fortune_sign: str) -> bool:
    """Check if a sign is angular from Fortune."""
    peaks = get_angular_signs_from_fortune(fortune_sign)
    peak_signs = [p["sign"] for p in peaks.values()]
    return sign in peak_signs


def get_peak_type(sign: str, fortune_sign: str) -> Optional[str]:
    """Get the peak type for a sign if it's angular from Fortune."""
    peaks = get_angular_signs_from_fortune(fortune_sign)
    for p in peaks.values():
        if p["sign"] == sign:
            return p["type"]
    return None


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _duration_str(duration: float) -> str:
    if duration >= 365:
        return f"{duration/365.25:.1f} years"
    if duration >= 30:
        return f"{duration/30:.1f} months"
    if duration >= 1:
        return f"{duration:.1f} days"
    return f"{duration*24:.1f} hours"


def build_zr_report_data(
    chart_data: Dict[str, Any],
    target_dt: datetime,
    lot: str = "spirit",
) -> Dict[str, Any]:
    """
    Structured ZR worksheet (Brennan framework) for one lot at one instant.
    Peaks, triads and phases are always from Fortune; the released lot only
    chooses the period sequence.
    """
    lots = chart_data.get("lots", {})
    fortune_data = lots.get("fortune", {})
    spirit_data = lots.get("spirit", {})
    fortune_sign = fortune_data.get("sign")
    spirit_sign = spirit_data.get("sign")

    snapshot = zr_for_chart(chart_data, target_dt, lot)

    sect_planets = get_sect_planets(chart_data)
    planets_by_mod = get_planets_by_modality(chart_data)
    fortune_modality = get_modality(fortune_sign)
    if fortune_modality == "Mutable":
        prep_mod, peak_mod, comp_mod = "Fixed", "Mutable", "Cardinal"
    elif fortune_modality == "Fixed":
        prep_mod, peak_mod, comp_mod = "Cardinal", "Fixed", "Mutable"
    else:
        prep_mod, peak_mod, comp_mod = "Mutable", "Cardinal", "Fixed"

    planets = chart_data.get("planets", [])
    periods = {}
    for p in snapshot.levels:
        d = p.to_dict()
        d["planets_in_sign"] = [pl["name"] for pl in planets if pl.get("sign") == p.sign]
        periods[f"L{p.level}"] = d

    l1, l2 = snapshot.L1, snapshot.L2
    loosing = {
        "L1_loosing_at": l1.loosing_at.isoformat() if l1.loosing_at else None,
        "L1_looses_to": opposite_sign(l1.sign) if l1.loosing_at else None,
        "L2_is_loosed": l2.is_loosing_of_bond,
        "L2_is_pre_loosing": l2.is_pre_loosing,
        "loosed_levels": [f"L{p.level}" for p in snapshot.levels if p.is_loosing_of_bond],
        "details": snapshot.loosing_details,
    }

    return {
        "generated": target_dt.isoformat(),
        "lot": lot,
        "release_sign": snapshot.release_sign,
        "lots": {
            "fortune": {"sign": fortune_sign, "degree": float(fortune_data.get("degreeInSign", 0)),
                        "ruler": RULERS.get(fortune_sign, "")},
            "spirit": {"sign": spirit_sign, "degree": float(spirit_data.get("degreeInSign", 0)),
                       "ruler": RULERS.get(spirit_sign, "")},
        },
        "fortune_modality": fortune_modality,
        "phase_modalities": {"preparatory": prep_mod, "peak": peak_mod, "completion": comp_mod},
        "peaks": get_angular_signs_from_fortune(fortune_sign),
        "triads": get_angular_triads(fortune_sign),
        "sect": sect_planets,
        "planets_by_phase": {"preparatory": planets_by_mod.get(prep_mod, []),
                             "peak": planets_by_mod.get(peak_mod, []),
                             "completion": planets_by_mod.get(comp_mod, [])},
        "periods": periods,
        "loosing": loosing,
        "active_peaks": [f"L{p.level} {p.sign} ({p.peak_type})" for p in snapshot.levels[:4] if p.is_peak],
    }


def render_zr_report_markdown(data: Dict[str, Any]) -> str:
    """Render the worksheet data as markdown."""
    lines = []
    f = data["lots"]["fortune"]
    s = data["lots"]["spirit"]
    pm = data["phase_modalities"]

    lines.append("# Zodiacal Releasing Report")
    lines.append(f"**Generated:** {datetime.fromisoformat(data['generated']).strftime('%Y-%m-%d %H:%M')}")
    release_note = ""
    if data["release_sign"] != data["lots"][data["lot"]]["sign"]:
        release_note = f" (Spirit shares Fortune's sign, so it releases from {data['release_sign']})"
    lines.append(f"Releasing from: **{data['lot'].title()}**{release_note}")
    lines.append("")

    lines.append("## 1. Lot Positions")
    lines.append(f"- **Lot of Fortune:** {f['sign']} {f['degree']:.0f}° (ruler: {f['ruler']})")
    lines.append(f"- **Lot of Spirit:** {s['sign']} {s['degree']:.0f}° (ruler: {s['ruler']})")
    lines.append("")

    lines.append("## 2. Peak Periods (from Lot of Fortune)")
    lines.append(f"Fortune is in **{f['sign']}** ({data['fortune_modality']}), so peak periods = **{pm['peak']}** signs")
    lines.append("")
    lines.append("| Position | Sign | Peak Type |")
    lines.append("|----------|------|-----------|")
    for key, pk in data["peaks"].items():
        lines.append(f"| {pk['position']} | **{pk['sign']}** | {pk['type']} {pk['emoji']} |")
    lines.append("")

    sect = data["sect"]
    lines.append("## 3. Sect Analysis")
    lines.append(f"**Chart Sect:** {sect['sect']}")
    lines.append("")
    lines.append("| Role | Planet | Sign | Notes |")
    lines.append("|------|--------|------|-------|")
    for key, d in sect.items():
        if key == "sect":
            continue
        dignity = d.get("dignity", "")
        dignity_note = f" ({dignity})" if dignity else ""
        lines.append(f"| {d['role']} | **{d['planet']}** | {d['sign']}{dignity_note} | {key.replace('_', ' ').title()} |")
    lines.append("")

    lines.append("## 4. Angular Triads")
    lines.append("")
    lines.append("| Phase | Preparatory | Peak | Completion |")
    lines.append("|-------|-------------|------|------------|")
    for triad in data["triads"]:
        peak = triad["peak"]["sign"]
        peak_marker = " ⭐" if get_peak_type(peak, f["sign"]) else ""
        lines.append(f"| **{triad['name']}** | {triad['preparatory']['sign']} | {peak}{peak_marker} | {triad['completion']['sign']} |")
    lines.append("")

    lines.append("## 5. Planets by Phase")
    lines.append("")
    lines.append("| Phase | Modality | Planets | Experience |")
    lines.append("|-------|----------|---------|------------|")
    for phase in ("preparatory", "peak", "completion"):
        plist = data["planets_by_phase"][phase]
        planet_str = ", ".join(f"{p['planet']} ({p['sign']})" for p in plist[:4]) or "None"
        lines.append(f"| {phase.title()} | {pm[phase]} | {planet_str} | |")
    lines.append("")

    lines.append(f"## 6. Current Periods (releasing from {data['lot'].title()})")
    lines.append("")
    for level in ("L1", "L2", "L3", "L4", "L5", "L6"):
        p = data["periods"][level]
        peak_marker = f" ⭐ ({p['peak_type']})" if p["peak_type"] else ""
        marks = ""
        if p["is_loosing_of_bond"]:
            marks += " ⚡ LB"
        if p["is_pre_loosing"]:
            marks += " ⏳ pre-LB"
        start = datetime.fromisoformat(p["start"])
        end = datetime.fromisoformat(p["end"])
        lines.append(f"**{level}: {p['sign']}** ({p['ruler']}){peak_marker}{marks}")
        lines.append(f"- {start:%Y-%m-%d} → {end:%Y-%m-%d} ({_duration_str(p['duration_days'])})")
        lines.append(f"- {_ordinal(p['house_from_fortune'])} from Fortune, {p['angularity']}: **{p['phase']}** phase")
        if p["loosing_at"]:
            lines.append(f"- sub-periods loose the bond {datetime.fromisoformat(p['loosing_at']):%Y-%m-%d} (to {opposite_sign(p['sign'])})")
        lines.append("")

    lo = data["loosing"]
    lines.append("## 7. Loosing of the Bond")
    if lo["details"]:
        lines.append(f"⚡ {lo['details']}")
    elif lo["L1_loosing_at"]:
        lines.append(f"L1 {data['periods']['L1']['sign']} looses the bond on "
                     f"{datetime.fromisoformat(lo['L1_loosing_at']):%Y-%m-%d}, when L2 jumps to {lo['L1_looses_to']}.")
    else:
        lines.append(f"L1 {data['periods']['L1']['sign']} is too short for its sub-periods to complete a cycle; no loosing at L2.")
    if lo["loosed_levels"]:
        lines.append(f"Levels currently in a loosed portion of their parent: {', '.join(lo['loosed_levels'])}")
    lines.append("")

    lines.append("## 8. Key Observations")
    lines.append("")
    if data["active_peaks"]:
        lines.append(f"**Active Peak Periods:** {', '.join(data['active_peaks'])}")
    else:
        lines.append("**Active Peak Periods:** None at major levels")
    lines.append("")
    lines.append("**Planets in Current Signs:**")
    for level in ("L2", "L3"):
        p = data["periods"][level]
        if p["planets_in_sign"]:
            lines.append(f"- {level} {p['sign']}: {', '.join(p['planets_in_sign'])}")

    return "\n".join(lines)


def generate_zr_report(
    chart_data: Dict[str, Any],
    target_dt: datetime,
    lot: str = "spirit",
    format: str = "markdown",
):
    """
    Comprehensive ZR report using Brennan's worksheet framework.
    lot: "spirit" or "fortune". format: "markdown" (str) or "json" (dict).
    """
    data = build_zr_report_data(chart_data, target_dt, lot)
    if format == "json":
        return data
    return render_zr_report_markdown(data)


def zr_report_for_chart(chart_data: Dict[str, Any], target_dt: datetime, lot: str = "spirit") -> str:
    """Convenience wrapper for Stella integration."""
    return generate_zr_report(chart_data, target_dt, lot)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("usage: python zr_report.py charts/<name>.json [YYYY-MM-DD] [spirit|fortune]")
        sys.exit(1)
    with open(sys.argv[1], "r") as fh:
        chart = json.load(fh)
    target = datetime.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now()
    print(generate_zr_report(chart, target, sys.argv[3] if len(sys.argv) > 3 else "spirit"))
