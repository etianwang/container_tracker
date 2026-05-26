"""
历史记录管理
存储路径: ~/.honsen_tracker/history.json
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR  = Path.home() / '.honsen_tracker'
HIST_FILE = DATA_DIR / 'history.json'
MAX_HIST  = 60


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load() -> list:
    _ensure()
    try:
        if HIST_FILE.exists():
            return json.loads(HIST_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return []


def save(arr: list):
    _ensure()
    HIST_FILE.write_text(
        json.dumps(arr[:MAX_HIST], ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def add(container_no: str, carrier: str):
    print(f"history.add called, saving to: {HIST_FILE}")
    arr = [h for h in load() if h['no'] != container_no]
    arr.insert(0, {
        'id':      int(datetime.now().timestamp() * 1000),
        'no':      container_no,
        'carrier': carrier,
        'time':    datetime.now().isoformat(),
        'note':    ''
    })
    save(arr)


def update_note(hid: int, note: str):
    arr = load()
    for h in arr:
        if h['id'] == hid:
            h['note'] = note
    save(arr)


def delete(hid: int):
    save([h for h in load() if h['id'] != hid])


def clear():
    save([])


def fmt_time(iso: str) -> str:
    try:
        dt  = datetime.fromisoformat(iso)
        now = datetime.now()
        if dt.date() == now.date():
            return dt.strftime('%H:%M')
        return dt.strftime('%m/%d %H:%M')
    except Exception:
        return ''