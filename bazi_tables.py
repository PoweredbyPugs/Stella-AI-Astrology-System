"""BaZi lookup tables: stems, branches, hidden stems, Nayin, Ten Gods, interactions, stars.

Sources: the Zi Ping canon (淵海子平, 三命通會, 滴天髓, 子平真詮) as summarised in
docs/BAZI_REFERENCE.md. Nothing here is computed; every table is data.
Indices: stems 0–9 (甲 = 0), branches 0–11 (子 = 0), sexagenary 0–59 (甲子 = 0).
"""

STEMS = [
    {"cn": "甲", "pinyin": "jia", "element": "wood", "polarity": "yang"},
    {"cn": "乙", "pinyin": "yi", "element": "wood", "polarity": "yin"},
    {"cn": "丙", "pinyin": "bing", "element": "fire", "polarity": "yang"},
    {"cn": "丁", "pinyin": "ding", "element": "fire", "polarity": "yin"},
    {"cn": "戊", "pinyin": "wu", "element": "earth", "polarity": "yang"},
    {"cn": "己", "pinyin": "ji", "element": "earth", "polarity": "yin"},
    {"cn": "庚", "pinyin": "geng", "element": "metal", "polarity": "yang"},
    {"cn": "辛", "pinyin": "xin", "element": "metal", "polarity": "yin"},
    {"cn": "壬", "pinyin": "ren", "element": "water", "polarity": "yang"},
    {"cn": "癸", "pinyin": "gui", "element": "water", "polarity": "yin"},
]

BRANCHES = [
    {"cn": "子", "pinyin": "zi", "element": "water", "polarity": "yang", "animal": "Rat"},
    {"cn": "丑", "pinyin": "chou", "element": "earth", "polarity": "yin", "animal": "Ox"},
    {"cn": "寅", "pinyin": "yin", "element": "wood", "polarity": "yang", "animal": "Tiger"},
    {"cn": "卯", "pinyin": "mao", "element": "wood", "polarity": "yin", "animal": "Rabbit"},
    {"cn": "辰", "pinyin": "chen", "element": "earth", "polarity": "yang", "animal": "Dragon"},
    {"cn": "巳", "pinyin": "si", "element": "fire", "polarity": "yin", "animal": "Snake"},
    {"cn": "午", "pinyin": "wu", "element": "fire", "polarity": "yang", "animal": "Horse"},
    {"cn": "未", "pinyin": "wei", "element": "earth", "polarity": "yin", "animal": "Goat"},
    {"cn": "申", "pinyin": "shen", "element": "metal", "polarity": "yang", "animal": "Monkey"},
    {"cn": "酉", "pinyin": "you", "element": "metal", "polarity": "yin", "animal": "Rooster"},
    {"cn": "戌", "pinyin": "xu", "element": "earth", "polarity": "yang", "animal": "Dog"},
    {"cn": "亥", "pinyin": "hai", "element": "water", "polarity": "yin", "animal": "Pig"},
]

ELEMENTS = ("wood", "fire", "earth", "metal", "water")
ELEMENT_CN = {"wood": "木", "fire": "火", "earth": "土", "metal": "金", "water": "水"}

# Hidden stems (藏干), primary qi first, then middle and residual qi.
HIDDEN_STEMS = {
    0: [9],          # 子: 癸
    1: [5, 9, 7],    # 丑: 己 癸 辛
    2: [0, 2, 4],    # 寅: 甲 丙 戊
    3: [1],          # 卯: 乙
    4: [4, 1, 9],    # 辰: 戊 乙 癸
    5: [2, 6, 4],    # 巳: 丙 庚 戊
    6: [3, 5],       # 午: 丁 己
    7: [5, 3, 1],    # 未: 己 丁 乙
    8: [6, 8, 4],    # 申: 庚 壬 戊
    9: [7],          # 酉: 辛
    10: [4, 7, 3],   # 戌: 戊 辛 丁
    11: [8, 0],      # 亥: 壬 甲
}

# Nayin (納音), one name per pair of sexagenary indices (0–1, 2–3, …).
_NAYIN_PAIRS = [
    ("海中金", "metal"), ("爐中火", "fire"), ("大林木", "wood"), ("路旁土", "earth"), ("劍鋒金", "metal"),
    ("山頭火", "fire"), ("澗下水", "water"), ("城頭土", "earth"), ("白蠟金", "metal"), ("楊柳木", "wood"),
    ("泉中水", "water"), ("屋上土", "earth"), ("霹靂火", "fire"), ("松柏木", "wood"), ("長流水", "water"),
    ("沙中金", "metal"), ("山下火", "fire"), ("平地木", "wood"), ("壁上土", "earth"), ("金箔金", "metal"),
    ("佛燈火", "fire"), ("天河水", "water"), ("大驛土", "earth"), ("釵釧金", "metal"), ("桑柘木", "wood"),
    ("大溪水", "water"), ("沙中土", "earth"), ("天上火", "fire"), ("石榴木", "wood"), ("大海水", "water"),
]
NAYIN = [name for name, _ in _NAYIN_PAIRS for _ in (0, 1)]
NAYIN_ELEMENT = [el for _, el in _NAYIN_PAIRS for _ in (0, 1)]

# ── Ten Gods (十神) ─────────────────────────────────────────────────────────
# Keyed by relation to the Day Master, then by same/different polarity.
TEN_GODS = {
    "比肩": {"pinyin": "bi jian", "en": "Friend"},
    "劫財": {"pinyin": "jie cai", "en": "Rob Wealth"},
    "食神": {"pinyin": "shi shen", "en": "Eating God"},
    "傷官": {"pinyin": "shang guan", "en": "Hurting Officer"},
    "偏財": {"pinyin": "pian cai", "en": "Indirect Wealth"},
    "正財": {"pinyin": "zheng cai", "en": "Direct Wealth"},
    "七殺": {"pinyin": "qi sha", "en": "Seven Killings"},
    "正官": {"pinyin": "zheng guan", "en": "Direct Officer"},
    "偏印": {"pinyin": "pian yin", "en": "Indirect Resource"},
    "正印": {"pinyin": "zheng yin", "en": "Direct Resource"},
}
# relation: 0 same, 1 Day Master produces, 2 Day Master controls, 3 controls Day Master, 4 produces Day Master
TEN_GOD_BY_RELATION = {
    (0, True): "比肩", (0, False): "劫財",
    (1, True): "食神", (1, False): "傷官",
    (2, True): "偏財", (2, False): "正財",
    (3, True): "七殺", (3, False): "正官",
    (4, True): "偏印", (4, False): "正印",
}

# ── Twelve life stages (十二長生) ───────────────────────────────────────────
LIFE_STAGES = ["長生", "沐浴", "冠帶", "臨官", "帝旺", "衰", "病", "死", "墓", "絕", "胎", "養"]
# Branch of 長生 for each stem. Yang stems count forward, yin stems backward (陰逆).
LIFE_STAGE_START = {0: 11, 1: 6, 2: 2, 3: 9, 4: 2, 5: 9, 6: 5, 7: 0, 8: 8, 9: 3}

# ── Seasonal states (旺相休囚死) ────────────────────────────────────────────
# Season element by month branch; an element is 旺 in its own season, 相 when the season
# produces it, 休 when it produces the season, 囚 when it controls the season, 死 when the
# season controls it. Earth months (辰戌丑未) belong to earth.
SEASON_OF_BRANCH = {2: "wood", 3: "wood", 5: "fire", 6: "fire", 8: "metal", 9: "metal",
                    11: "water", 0: "water", 1: "earth", 4: "earth", 7: "earth", 10: "earth"}
SEASON_NAME_OF_BRANCH = {2: "spring", 3: "spring", 4: "spring", 5: "summer", 6: "summer", 7: "summer",
                         8: "autumn", 9: "autumn", 10: "autumn", 11: "winter", 0: "winter", 1: "winter"}
SEASON_STATES = ["旺", "相", "死", "囚", "休"]   # indexed by element_relation(season, element)

# ── Void (空亡) by decade of the day pillar ─────────────────────────────────
def void_branches(sexagenary_index: int) -> list:
    d = sexagenary_index // 10
    return [(10 - 2 * d) % 12, (11 - 2 * d) % 12]

# ── Interactions ────────────────────────────────────────────────────────────
# Stem combinations (天干五合) and the element they transform into.
STEM_COMBOS = {frozenset((0, 5)): "earth", frozenset((1, 6)): "metal", frozenset((2, 7)): "water",
               frozenset((3, 8)): "wood", frozenset((4, 9)): "fire"}
# Branch six combinations (六合).
SIX_COMBOS = {frozenset((0, 1)): "earth", frozenset((2, 11)): "wood", frozenset((3, 10)): "fire",
              frozenset((4, 9)): "metal", frozenset((5, 8)): "water", frozenset((6, 7)): "earth"}
# Three combinations (三合): (start, peak, grave) → element. A half trine is any pair that includes the peak.
TRINES = {(8, 0, 4): "water", (11, 3, 7): "wood", (2, 6, 10): "fire", (5, 9, 1): "metal"}
# Directional combinations (三會).
DIRECTIONAL = {(2, 3, 4): "wood", (5, 6, 7): "fire", (8, 9, 10): "metal", (11, 0, 1): "water"}
CLASHES = [(0, 6), (1, 7), (2, 8), (3, 9), (4, 10), (5, 11)]
HARMS = [(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)]
DESTRUCTIONS = [(0, 9), (1, 4), (2, 11), (3, 6), (5, 8), (7, 10)]
# Punishments (刑): the two triads (any pair within one counts), the 子卯 pair, and the four self-punishments.
PUNISHMENT_TRIADS = [((2, 5, 8), "無恩之刑 ungrateful"), ((1, 10, 7), "恃勢之刑 bullying")]
PUNISHMENT_PAIR = ((0, 3), "無禮之刑 rude")
SELF_PUNISHMENT = (4, 6, 9, 11)

# ── Symbolic stars (神煞), the core set ─────────────────────────────────────
# Stem-cast stars: stem index → branches.
TIANYI = {0: (1, 7), 1: (0, 8), 2: (11, 9), 3: (11, 9), 4: (1, 7),       # 天乙貴人, 淵海子平 / 三命通會
          5: (0, 8), 6: (1, 7), 7: (6, 2), 8: (5, 3), 9: (5, 3)}
TIANYI_VARIANT_NOTE = ("天乙貴人 for 庚 follows 淵海子平 / 三命通會 (丑未); the 協紀辨方書 table gives 寅午 instead.")
WENCHANG = {0: 5, 1: 6, 2: 8, 3: 9, 4: 8, 5: 9, 6: 11, 7: 0, 8: 2, 9: 3}  # 文昌
LUSHEN = {0: 2, 1: 3, 2: 5, 3: 6, 4: 5, 5: 6, 6: 8, 7: 9, 8: 11, 9: 0}    # 祿神
YANGREN = {0: 3, 2: 6, 4: 6, 6: 9, 8: 0}                                   # 羊刃, yang stems only
# Branch-cast stars: by the trine group the casting branch belongs to.
TAOHUA = {(8, 0, 4): 9, (11, 3, 7): 0, (2, 6, 10): 3, (5, 9, 1): 6}       # 桃花
YIMA = {(8, 0, 4): 2, (11, 3, 7): 5, (2, 6, 10): 8, (5, 9, 1): 11}        # 驛馬
# 孤辰 / 寡宿 by the directional group of the casting branch: (孤辰, 寡宿).
GUCHEN_GUASU = {(11, 0, 1): (2, 10), (2, 3, 4): (5, 1), (5, 6, 7): (8, 4), (8, 9, 10): (11, 7)}
STAR_EN = {"天乙貴人": "Nobleman", "文昌": "Academic Star", "祿神": "Prosperity", "羊刃": "Goat Blade",
           "桃花": "Peach Blossom", "驛馬": "Travelling Horse", "孤辰": "Solitary", "寡宿": "Widow"}
