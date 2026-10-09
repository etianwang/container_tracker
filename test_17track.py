import asyncio
from unittest.mock import patch

from grabbers.track17 import Track17Grabber


def test_parse():
    result = Track17Grabber.parse('CMDU1234567', {
        'track_info': {
            'latest_status': {'status': 'InTransit', 'sub_status_descr': '运输中'},
            'shipping_info': {'shipper_address': {'city': 'Shanghai', 'country': 'CN'}, 'recipient_address': {'city': 'Abidjan', 'country': 'CI'}},
            'tracking': {'providers': [{'provider': {'name': 'CMA CGM'}, 'latest_sync_time': '2026-10-09T10:00:00Z', 'events': [
                {'description_translation': {'description': '已装船'}, 'time_iso': '2026-10-09T09:00:00Z', 'location': '上海'},
            ]}]},
        },
    })
    assert result['carrier'] == 'CMA CGM' and result['events'][0]['milestone'].startswith('已装船')
    assert result['from_port'] == 'Shanghai, CN' and result['status'] == '运输中'


def test_already_registered_is_not_an_error():
    responses = [
        {'accepted': [], 'rejected': [{'error': {'code': -18019901}}]},
        {'accepted': [{'track_info': {'latest_status': {'status': 'NotFound'}, 'tracking': {'providers': []}}}]},
    ]
    with patch('grabbers.track17._post', side_effect=responses):
        result = asyncio.run(Track17Grabber('CMAU3453875').fetch())
    assert result['status'] == 'NotFound'


if __name__ == '__main__':
    test_parse()
    test_already_registered_is_not_an_error()
    print('ok')
