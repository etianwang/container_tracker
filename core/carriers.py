"""
承运商前缀映射表
key   : 4位BIC前缀
value : (承运商全称, 抓取器名称)
        抓取器名称对应 grabbers/ 目录下的模块名
"""

CARRIER_MAP = {
    # ── Maersk Group ──
    "MSKU": ("Maersk Line",          "maersk"),
    "MRKU": ("Maersk Line",          "maersk"),
    "MRSU": ("Maersk Line",          "maersk"),
    "SUDU": ("Hamburg Sud (Maersk)", "maersk"),
    "SEAU": ("Sealand (Maersk)",     "maersk"),
    "TEMU": ("Textainer / Maersk",   "maersk"),

    # ── MSC ──
    "MSCU": ("MSC",                  "msc"),
    "MEDU": ("MSC",                  "msc"),

    # ── CMA CGM ──
    "CMDU": ("CMA CGM",              "cmacgm"),
    "APZU": ("APL (CMA CGM)",        "cmacgm"),

    # ── COSCO ──
    "COSU": ("COSCO Shipping",       "cosco"),
    "CCLU": ("COSCO (CCL)",          "cosco"),
    "CSNU": ("COSCO / Sealand",      "cosco"),

    # ── HMM ──
    "HDMU": ("HMM",                  "hmm"),

    # ── Evergreen ──
    "EGLV": ("Evergreen",            "evergreen"),
    "UETU": ("Evergreen",            "evergreen"),

    # ── Yang Ming ──
    "YMLU": ("Yang Ming",            "yangming"),

    # ── OOCL ──
    "OOLU": ("OOCL",                 "oocl"),
    "OOCU": ("OOCL",                 "oocl"),

    # ── Hapag-Lloyd ──
    "HLCU": ("Hapag-Lloyd",          "hapag"),

    # ── ZIM ──
    "ZIMU": ("ZIM",                  "zim"),

    # ── PIL ──
    "PCIU": ("PIL",                  "pil"),

    # ── Wan Hai ──
    "WHLU": ("Wan Hai Lines",        "wanhai"),

    # ── 租箱公司（走 Maersk 查）──
    "TGHU": ("Triton International", "maersk"),
    "TGBU": ("Triton International", "maersk"),
    "TCKU": ("Triton International", "maersk"),
    "TIIU": ("Triton International", "maersk"),
    "TRHU": ("Triton International", "maersk"),
    "CAAU": ("Triton International", "maersk"),
    "DFSU": ("Triton International", "maersk"),
    "BANQ": ("Beacon Intermodal",    "maersk"),
    "FFAU": ("Florens Container",    "maersk"),
    "CXDU": ("China Shipping",       "cosco"),
    "SEKU": ("Seaco",                "maersk"),
}


def get_carrier_name(container_no: str) -> str:
    """根据箱号返回承运商名称"""
    prefix = container_no[:4].upper() if len(container_no) >= 4 else ''
    info = CARRIER_MAP.get(prefix)
    return info[0] if info else '未知承运商'


def get_grabber_name(container_no: str) -> str:
    """根据箱号返回对应抓取器模块名"""
    prefix = container_no[:4].upper() if len(container_no) >= 4 else ''
    info = CARRIER_MAP.get(prefix)
    return info[1] if info else None