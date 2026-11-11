"""Markdown rendering for the BaZi tools. Every stem, branch and Ten God shows Chinese, pinyin, English."""

from bazi import PILLAR_ORDER
from bazi_tables import ELEMENT_CN, TEN_GODS

LABEL = {"year": "Year", "month": "Month", "day": "Day", "hour": "Hour"}


def stem_str(s: dict) -> str:
    return f"{s['cn']} {s['pinyin']} ({s['polarity']} {s['element']})"


def branch_str(b: dict) -> str:
    return f"{b['cn']} {b['pinyin']} {b['animal']} ({b['polarity']} {b['element']})"


def god_str(name: str) -> str:
    if name == "日主":
        return "日主 ri zhu Day Master"
    g = TEN_GODS[name]
    return f"{name} {g['pinyin']} {g['en']}"


def _settings_line(natal: dict, gender) -> str:
    st = natal["settings"]
    if st["true_solar_time"]:
        s = natal["solar"]
        solar = (f"true solar time: on (apparent {natal['instant_used'][11:16]}, clock {natal['clock_time'][11:16]}, "
                 f"longitude {s['longitude_minutes']:+.1f} min, equation of time {s['equation_minutes']:+.1f} min)")
    else:
        solar = "true solar time: off (clock time)"
    return f"**Settings:** {solar} · day boundary {st['day_boundary']} · gender {gender or 'unknown'}"


def _warnings(ws: list) -> list:
    return [f"> Warning: {w}" for w in ws] + ([""] if ws else [])


def _interaction_line(i: dict) -> str:
    members = " + ".join(f"{m[0]} {m[1]}" for m in i["members"])
    extra = ""
    if "element" in i:
        extra = f" → {i['element']} {ELEMENT_CN[i['element']]}"
        if "transforms" in i:
            extra += " (transforms: in season)" if i["transforms"] else " (does not transform: out of season)"
    if i.get("note"):
        extra += f" — {i['note']}"
    return f"- {i['cn']} {i['type'].replace('_', ' ')}: {members}{extra}"


def render_natal(result: dict) -> str:
    p, a, luck = result["pillars"], result["analysis"], result.get("luck")
    birth = result["birth"]
    lines = _warnings(result["warnings"])
    lines.append(f"# BaZi 八字 — {birth['source']}")
    lines.append(_settings_line(result, birth["gender"]))
    loc = f" ({birth['lat']}, {birth['lon']})" if birth["lon"] is not None else ""
    lines.append(f"**Birth:** {birth['local']} {birth['tz'] or ''}{loc}")
    lines.append("")
    lines.append("## Four Pillars 四柱")
    lines.append("| | " + " | ".join(LABEL[k] for k in PILLAR_ORDER) + " |")
    lines.append("|---|---|---|---|---|")
    lines.append("| Pillar | " + " | ".join(f"**{p[k]['cn']}** {p[k]['pinyin']}" for k in PILLAR_ORDER) + " |")
    lines.append("| Stem | " + " | ".join(stem_str(p[k]["stem"]) + (" **Day Master**" if k == "day" else "") for k in PILLAR_ORDER) + " |")
    lines.append("| Ten God | " + " | ".join(god_str(a["ten_gods_stems"][k]) for k in PILLAR_ORDER) + " |")
    lines.append("| Branch | " + " | ".join(branch_str(p[k]["branch"]) for k in PILLAR_ORDER) + " |")
    lines.append("| Hidden stems 藏干 | " + " | ".join(" ".join(s["cn"] for s in a["hidden"][k]) for k in PILLAR_ORDER) + " |")
    lines.append("| Hidden Ten Gods | " + " | ".join("; ".join(god_str(g) for g in a["ten_gods_hidden"][k]) for k in PILLAR_ORDER) + " |")
    lines.append("| Nayin 納音 | " + " | ".join(f"{p[k]['nayin']} ({p[k]['nayin_element']})" for k in PILLAR_ORDER) + " |")
    lines.append("| Life stage 十二長生 | " + " | ".join(a["life_stages"][k] for k in PILLAR_ORDER) + " |")
    lines.append("| Void 空亡 | " + " | ".join("✓" if k in a["void"]["pillars"] else "" for k in PILLAR_ORDER) + " |")
    lines.append("")
    lines.append(f"Void branches from the day pillar: {' '.join(b['cn'] for b in a['void']['branches'])}. "
                 "Life stages use the classical table (yin stems run backward); they do not feed the strength verdict.")
    lines.append("")

    dm, s = a["day_master"], a["strength"]
    lines.append("## Day Master 日主")
    lines.append(f"**{stem_str(dm)}**. Strength: **{s['verdict']}** — season state {s['season_state']} "
                 f"({dm['element']} in the {p['month']['branch']['cn']} month), rooted: {'yes' if s['rooted'] else 'no'}, "
                 f"supporting stems: {s['support']}.")
    lines.append(f"*Method: {s['method']}.*")
    lines.append("")

    st = a["structure"]
    lines.append("## Structure 格局")
    lines.append(f"**{st['name']}** on {st['qi_used']} ({st['ten_god']}), "
                 f"{'revealed in a stem' if st['revealed'] else 'the unrevealed qi of the month branch'}.")
    lines.append(f"*Basis: {st['basis']}.*")
    if st["special_candidates"]:
        lines.append("Special structures to weigh (not asserted):")
        lines.extend(f"- {c}" for c in st["special_candidates"])
    lines.append("")

    lines.append("## Five Elements 五行")
    lines.append("| | " + " | ".join(f"{e} {ELEMENT_CN[e]}" for e in a["tally_visible"]) + " |")
    lines.append("|---|---|---|---|---|---|")
    lines.append("| Visible (8 characters) | " + " | ".join(str(v) for v in a["tally_visible"].values()) + " |")
    lines.append("| With hidden stems | " + " | ".join(str(v) for v in a["tally_all"].values()) + " |")
    c = a["climate"]
    lines.append(f"Climate: {c['season']}, {c['temperature']}, {c['moisture']}. "
                 f"Tempering elements: {', '.join(c['tempering']) or 'none needed'}. "
                 "(Season facts for 調候; the reader applies the adjustment.)")
    lines.append("")

    lines.append("## Interactions")
    lines.extend(_interaction_line(i) for i in result["interactions"]) if result["interactions"] else lines.append("- none")
    lines.append("")

    lines.append("## Symbolic Stars 神煞 (core set)")
    hits = result["stars"]["hits"]
    lines.extend(f"- {h['star_cn']} {h['star_en']} in the {h['found_in']} pillar ({h['branch']}), cast from the {h['cast_from']} pillar"
                 for h in hits) if hits else lines.append("- none")
    lines.extend(f"*{f}*" for f in result["stars"]["footnotes"])
    lines.append("")

    if luck:
        lines.extend(render_luck(result, heading="## Luck Pillars 大運"))
    else:
        lines.append(f"**Luck pillars omitted:** {result['luck_omitted']}")
    return "\n".join(lines)


def render_luck(result: dict, heading: str = "# Luck Pillars 大運") -> list:
    luck, birth = result["luck"], result["birth"]
    sa = luck["start_age"]
    lines = [heading,
             f"Direction **{luck['direction']}** ({birth['gender']}, {result['pillars']['year']['stem']['polarity']} year). "
             f"Start age {sa['years']}y {sa['months']}m {sa['days']}d ({sa['days_to_jie']} days to the "
             f"{'next' if luck['direction'] == 'forward' else 'previous'} jie), first pillar from {luck['start_date']}.",
             "", "| # | Pillar | From | To | Age | Ten God (stem) | Ten God (branch) | Life stage | With natal |",
             "|---|---|---|---|---|---|---|---|---|"]
    for q in luck["pillars"]:
        inter = "; ".join(f"{i['cn']} with {', '.join(m[0] for m in i['members'] if m[0] != 'luck')}" for i in q["interactions_with_natal"]) or "—"
        mark = " ◀" if luck["current"] and q["index_in_sequence"] == luck["current"]["index_in_sequence"] else ""
        lines.append(f"| {q['index_in_sequence']} | {q['cn']} {q['pinyin']}{mark} | {q['start_date']} | {q['end_date']} | {q['age_from']} | "
                     f"{god_str(q['ten_god_stem'])} | {god_str(q['ten_god_branch'])} | {q['life_stage']} | {inter} |")
    cur = luck["current"]
    lines.append("")
    lines.append(f"Current (as of {luck['as_of']}): **{cur['cn']} {cur['pinyin']}**, pillar {cur['index_in_sequence']}."
                 if cur else f"As of {luck['as_of']}: before the first luck pillar.")
    return lines


def render_time(result: dict) -> str:
    now = result["pillars"]
    lines = [f"# Time Pillars — {result['at']}",
             f"*day boundary {result['settings']['day_boundary']}*", "",
             "| | Pillar | Stem | Branch | Hidden | Nayin |" + (" Ten God (stem) | Ten God (branch) | Life stage |" if result.get("ten_gods") else ""),
             "|---|---|---|---|---|---|" + ("---|---|---|" if result.get("ten_gods") else "")]
    for k in PILLAR_ORDER:
        row = (f"| {LABEL[k]} | **{now[k]['cn']}** {now[k]['pinyin']} | {stem_str(now[k]['stem'])} | {branch_str(now[k]['branch'])} | "
               f"{' '.join(result['hidden'][k])} | {now[k]['nayin']} |")
        if result.get("ten_gods"):
            g = result["ten_gods"][k]
            row += f" {god_str(g['stem'])} | {god_str(g['branch'])} | {g['life_stage']} |"
        lines.append(row)
    if result.get("ten_gods"):
        lines.append("")
        lines.append(f"Against **{result['natal_name']}** (Day Master {result['day_master']}).")
        if result.get("luck"):
            l = result["luck"]
            lines.append(f"Current luck pillar: **{l['cn']} {l['pinyin']}** ({god_str(l['ten_god_stem'])}).")
        elif result.get("luck_omitted"):
            lines.append(f"**Luck pillars omitted:** {result['luck_omitted']}")
        lines.append("")
        lines.append("## Interactions with the natal chart" + (" and luck pillar" if result.get("luck") else ""))
        lines.extend(_interaction_line(i) for i in result["interactions"]) if result["interactions"] else lines.append("- none")
    return "\n".join(lines)
