"""
本地缓存管理
缓存路径: ~/.honsen_tracker/cache/{箱号}.json
有效期:   12小时（可配置）
"""

import json
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path.home() / '.honsen_tracker' / 'cache'
CACHE_TTL = 43200  # 12小时（秒）


def _ensure():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get(container_no: str) -> dict | None:
    """读取缓存，过期或不存在返回 None"""
    _ensure()
    f = CACHE_DIR / f'{container_no.upper()}.json'
    if not f.exists():
        return None
    age = datetime.now().timestamp() - f.stat().st_mtime
    if age >= CACHE_TTL:
        return None
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        data['_cached'] = True
        data['_cache_age'] = int(age)
        return data
    except Exception:
        return None


def set(container_no: str, data: dict):
    """写入缓存"""
    _ensure()
    f = CACHE_DIR / f'{container_no.upper()}.json'
    payload = {k: v for k, v in data.items()
               if not k.startswith('_')}
    f.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def delete(container_no: str):
    """删除某个箱号的缓存"""
    f = CACHE_DIR / f'{container_no.upper()}.json'
    if f.exists():
        f.unlink()


def clear_all():
    """清空所有缓存"""
    _ensure()
    for f in CACHE_DIR.glob('*.json'):
        f.unlink()


def cache_info(container_no: str) -> dict:
    """返回缓存信息"""
    f = CACHE_DIR / f'{container_no.upper()}.json'
    if not f.exists():
        return {'exists': False}
    age = int(datetime.now().timestamp() - f.stat().st_mtime)
    return {
        'exists': True,
        'age_seconds': age,
        'age_minutes': age // 60,
        'expired': age >= CACHE_TTL,
        'remaining': max(0, CACHE_TTL - age),
    }