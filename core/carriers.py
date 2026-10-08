"""
承运商前缀映射表
key   : 4位BIC前缀
value : (承运商全称, 抓取器名称)
        抓取器名称对应 grabbers/ 目录下的模块名
"""

import re


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
    "HLXU": ("Hapag-Lloyd",          "hapag"),

    # ── ONE ──
    "ONEU": ("ONE",                  "one"),

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

TRACKING_URLS = {
    'maersk':   'https://www.maersk.com/tracking/{no}',
    'msc':      'https://www.msc.com/en/track-a-shipment?agencyPath=civ&trackingNumber={no}',
    'cmacgm':   'https://www.cma-cgm.com/ebusiness/tracking/search?SearchViewModel.Reference={no}',
    'cosco':    'https://elines.coscoshipping.com/ebusiness/cargoTracking?trackingType=CONTAINER&number={no}',
    'hmm':      'https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do',
    'evergreen':'https://ct.shipmentlink.com/servlet/TDB1_CargoTracking.do',
    'yangming': 'https://www.yangming.com/en/esolution/tracking/cargo_tracking',
    'oocl':     'https://www.oocl.com/eng/ourservices/eservices/cargotracking/Pages/cargotracking.aspx',
    'hapag':    'https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html?container={no}',
    'one':      'https://ecomm.one-line.com/one-ecom/manage-shipment/cargo-tracking?searchType=CONTAINER&searchValue={no}',
    'zim':      'https://www.zim.com/tools/track-a-shipment',
    'pil':      'https://www.pilship.com/en-our-track-and-trace-pil-pacific-international-lines/',
    'wanhai':   'https://www.wanhai.com/views/cargoTrack/CargoTrack.xhtml',
}

CONTAINER_RE = re.compile(r'^[A-Z]{4}\d{7}$')


def normalize_container_no(value: str) -> str:
    """Normalize and validate an ISO container number's basic format."""
    no = re.sub(r'\s+', '', value).upper()
    if not CONTAINER_RE.fullmatch(no):
        raise ValueError('箱号格式应为 4 个字母加 7 个数字，例如 MRSU6845613。')
    return no


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


def get_carrier_options() -> list[tuple[str, str]]:
    """Return selectable carrier names and their grabber identifiers."""
    seen = set()
    return [info for info in CARRIER_MAP.values()
            if not (info in seen or seen.add(info))]


def get_tracking_url(container_no: str, grabber_name: str | None = None) -> str | None:
    """Return the carrier's official tracking URL for a recognized container."""
    name = grabber_name or get_grabber_name(container_no)
    template = TRACKING_URLS.get(name)
    return template.format(no=container_no.upper()) if template else None
