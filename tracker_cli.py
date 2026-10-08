"""JSON-only bridge from the PHP app to the existing browser grabbers."""

import asyncio
import contextlib
import json
import os
import sys

from grabbers import get_grabber

EVENT_NAMES = {
    'Gate out Empty': '空箱出闸', 'Gate in': '进闸', 'Load on': '装船',
    'Vessel departure': '船舶离港', 'Vessel arrival': '船舶抵港',
    'Discharge': '卸船', 'Loaded': '已装船', 'Arrived': '已到达',
    'Departed': '已离港', 'Container available': '可提箱',
    'Latest move': '最新动态', 'Estimated Time of Arrival': '预计到港',
    'Full Intended Transshipment': '计划中转',
    'Full Transshipment Loaded': '中转装船',
    'Full Transshipment Discharged': '中转卸船',
    'Export Loaded on Vessel': '出口装船', 'Export received at CY': '出口堆场收箱',
    'Empty to Shipper': '空箱交付货主', 'Discharged at T/S Port': '中转港卸船',
}
LOCATIONS = {
    'NANSHA NEW PORT': '南沙新港', 'NANSHA NEW PORT,': '南沙新港',
    'ABIDJAN': '阿比让', 'ABIDJAN,': '阿比让',
    'GZ OCEANGATE CONTAINER TERMINAL': '广州南沙海港码头',
    'COTE D IVOIRE TERMINAL': '科特迪瓦码头',
    'Trieste, IT': '意大利的里雅斯特', 'Jebel Ali, AE': '阿联酋杰贝阿里',
    'Gioia Tauro, IT': '意大利焦亚陶罗', 'Ad Dammam, SA': '沙特达曼',
    'King Abdullah Port, SA': '沙特阿卜杜拉国王港',
    'GIOIA TAURO, IT': '意大利焦亚陶罗',
    'Adani Cma Mundra Container Terminal': '印度蒙德拉集装箱码头',
}
QUERY_TIMEOUT = int(os.environ.get('TRACKER_TIMEOUT_SECONDS', '50'))

def translate_event(value: str) -> str:
    value = value.replace(' Latest event', ' 最新动态')
    for source, target in EVENT_NAMES.items():
        if value == source or value.startswith(source + ' '):
            return target + value[len(source):]
    return value


def translate_result(result: dict) -> dict:
    for event in result.get('events', []):
        name, *when = event.get('milestone', '').split('\n', 1)
        event['milestone'] = translate_event(name) + (f'\n{when[0]}' if when else '')
        event['loc'] = '\n'.join(LOCATIONS.get(part.strip(), part.strip()) for part in event.get('loc', '').split('\n') if part.strip())
    result['status'] = translate_event(result.get('status', ''))
    for source, target in LOCATIONS.items():
        result['status'] = result['status'].replace(source, target)
    result['from_port'] = '\n'.join(LOCATIONS.get(part.strip(), part.strip()) for part in result.get('from_port', '').split('\n') if part.strip())
    result['to_port'] = '\n'.join(LOCATIONS.get(part.strip(), part.strip()) for part in result.get('to_port', '').split('\n') if part.strip())
    updated = result.get('updated', '')
    result['updated'] = updated.replace('Last updated: ', '最后更新：').replace(' hours ago', ' 小时前').replace(' hour ago', ' 小时前').replace(' days ago', ' 天前').replace(' day ago', ' 天前').replace(' minutes ago', ' 分钟前').replace(' minute ago', ' 分钟前')
    return result


async def track(container_no: str, carrier: str) -> dict:
    grabber = get_grabber(carrier, container_no)
    if carrier not in {'maersk', 'msc', 'cosco', 'oocl'} or getattr(grabber, 'NAME', None) != carrier:
        raise ValueError('该承运商尚未接入站内实时查询。')
    with contextlib.redirect_stdout(sys.stderr):
        return translate_result(await grabber.fetch())


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--self-test']:
            assert translate_event('Vessel departure (TEST) Latest event') == '船舶离港 (TEST) 最新动态'
            assert translate_event('Discharged at T/S Port') == '中转港卸船'
            assert translate_result({'updated': 'Last updated: 2 hours ago'})['updated'] == '最后更新：2 小时前'
            assert translate_result({'status': 'Latest move · GIOIA TAURO, IT'})['status'] == '最新动态 · 意大利焦亚陶罗'
            payload = {'ok': True, 'result': {'self_test': True}}
        elif len(sys.argv) != 3:
            raise ValueError('用法：tracker_cli.py 箱号 承运商')
        else:
            result = asyncio.run(asyncio.wait_for(track(sys.argv[1], sys.argv[2]), timeout=QUERY_TIMEOUT))
            payload = {'ok': True, 'result': result}
    except Exception:
        payload = {'ok': False, 'error': '实时查询失败，请稍后重试。'}
    print('TRACKER_JSON=' + json.dumps(payload, ensure_ascii=False))
