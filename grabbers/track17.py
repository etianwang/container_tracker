"""17TRACK registered-tracking fallback, using only Python's standard library."""

import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from .base import BaseGrabber


API = 'https://api.17track.net/track/v2.4/'
CARRIER_CODES = {
    'MSKU': 100768, 'MRKU': 100768, 'MRSU': 100768,
    'MSCU': 101079, 'MEDU': 101079,
    'CMDU': 100755, 'CMAU': 100755, 'APZU': 100755,
    'COSU': 101512, 'CCLU': 101512, 'CSNU': 101512,
    'HLCU': 101436, 'HLXU': 101436, 'ONEU': 100753, 'ZIMU': 101511,
}


def _token() -> str:
    path = Path(__file__).resolve().parent.parent / 'data' / '17track.key'
    return os.environ.get('TRACK17_TOKEN', '').strip() or (path.read_text(encoding='utf-8').strip() if path.exists() else '')


def _post(endpoint: str, payload: list) -> dict:
    token = _token()
    if not token:
        raise ValueError('未配置 17TRACK 密钥。')
    request = Request(API + endpoint, data=json.dumps(payload).encode(), headers={
        '17token': token, 'Content-Type': 'application/json',
    }, method='POST')
    try:
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
    except URLError as exc:
        raise RuntimeError('17TRACK 网络请求失败。') from exc
    if data.get('code') != 0:
        raise RuntimeError('17TRACK 查询失败。')
    return data['data']


class Track17Grabber(BaseGrabber):
    NAME = '17track'

    @staticmethod
    def parse(container_no: str, accepted: dict) -> dict:
        info = accepted.get('track_info') or {}
        providers = (info.get('tracking') or {}).get('providers') or []
        provider = providers[0] if providers else {}
        events = []
        for event in provider.get('events') or []:
            description = (event.get('description_translation') or {}).get('description') or event.get('description') or '状态更新'
            when = event.get('time_iso') or event.get('time_utc') or (event.get('time_raw') or {}).get('date') or ''
            events.append({'loc': event.get('location') or '', 'milestone': description + (f'\n{when}' if when else '')})
        shipping = info.get('shipping_info') or {}
        origin = shipping.get('shipper_address') or {}
        destination = shipping.get('recipient_address') or {}
        latest = info.get('latest_event') or {}
        status = (info.get('latest_status') or {}).get('sub_status_descr') or (latest.get('description_translation') or {}).get('description') or latest.get('description') or (info.get('latest_status') or {}).get('status') or '等待承运商返回追踪信息'
        return {
            'container': container_no,
            'carrier': (provider.get('provider') or {}).get('name') or '17TRACK',
            'from_port': ', '.join(filter(None, [origin.get('city'), origin.get('country')])),
            'to_port': ', '.join(filter(None, [destination.get('city'), destination.get('country')])),
            'updated': provider.get('latest_sync_time') or '',
            'status': status,
            'events': events,
        }

    async def fetch(self) -> dict:
        item = {'number': self.container_no, 'lang': 'zh-hans'}
        if code := CARRIER_CODES.get(self.container_no[:4]):
            item['carrier'] = code
        registered = _post('register', [item])
        rejected = (registered.get('rejected') or [{}])[0].get('error', {}).get('code')
        if not registered.get('accepted') and rejected != -18019901:
            raise ValueError('17TRACK 未识别该箱号。')
        details = _post('gettrackinfo', [item])
        accepted = (details.get('accepted') or [{}])[0]
        return self.parse(self.container_no, accepted)
