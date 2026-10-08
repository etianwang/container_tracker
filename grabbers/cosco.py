"""COSCO Shipping 公共货物追踪页面抓取器。"""

import json

from .base import BaseGrabber

TRACKING_URL = 'https://elines.coscoshipping.com/scct/public/ct/base?lang=en&number={no}&trackingType=CONTAINER'

_JS = '''JSON.stringify(Array.from(document.querySelectorAll('tbody.ant-table-tbody tr')).map(row => {
    const cells = Array.from(row.querySelectorAll('td')).map(cell => cell.innerText.trim());
    return {loc: cells[2] || '', milestone: (cells[0] || '') + '\\n' + (cells[1] || '')};
}))'''


class CoscoGrabber(BaseGrabber):
    NAME = 'cosco'
    CARRIERS = ['COSCO Shipping', 'COSCO', 'China Shipping']

    async def fetch(self) -> dict:
        import nodriver as uc

        browser = await uc.start(headless=False, browser_args=['--window-size=400,300', '--window-position=99999,99999'])
        try:
            tab = await browser.get(TRACKING_URL.format(no=self.container_no))
            await self._wait_for(tab, 'tbody.ant-table-tbody tr')
            events = json.loads(await tab.evaluate(_JS))
            if not events:
                raise ValueError('COSCO 页面未返回有效数据，请检查箱号或稍后重试')
            return {
                'container': self.container_no, 'carrier': 'COSCO Shipping',
                'from_port': '', 'to_port': '', 'updated': '',
                'status': events[0]['milestone'].split('\n', 1)[0], 'events': events,
            }
        finally:
            browser.stop()
