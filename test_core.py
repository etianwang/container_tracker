import asyncio

from core import carriers
from grabbers import get_grabber
from grabbers.msc import MscGrabber
from grabbers.official import OfficialGrabber


def test_container_helpers():
    assert carriers.normalize_container_no(' mrsu 6845613 ') == 'MRSU6845613'
    assert carriers.get_grabber_name('MRSU6845613') == 'maersk'
    assert carriers.get_tracking_url('MSCU1234567').endswith('MSCU1234567')
    assert carriers.get_grabber_name('HLXU1234567') == 'hapag'
    assert carriers.get_grabber_name('ONEU1234567') == 'one'
    assert carriers.get_grabber_name('CMAU1234567') == 'cmacgm'
    assert carriers.get_tracking_url('ZIMU1234567').startswith('https://www.zim.com/')
    assert ('MSC', 'msc') in carriers.get_carrier_options()
    assert carriers.get_tracking_url('ABCD1234567', 'msc').endswith('ABCD1234567')
    assert isinstance(get_grabber('msc', 'MSCU1234567'), MscGrabber)
    try:
        carriers.normalize_container_no('MRSU123')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid container number was accepted')


def test_official_fallback():
    grabber = get_grabber('cmacgm', 'CMDU1234567', 'CMA CGM')
    import grabbers.official
    original = grabbers.official.webbrowser.open
    grabbers.official.webbrowser.open = lambda url: url
    try:
        data = asyncio.run(grabber.fetch())
    finally:
        grabbers.official.webbrowser.open = original
    assert data['_skip_cache'] and data['carrier'] == 'CMA CGM'


if __name__ == '__main__':
    test_container_helpers()
    test_official_fallback()
    print('ok')
