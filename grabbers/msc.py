"""MSC Mediterranean Shipping 官网查询抓取器。"""

import asyncio
import json
import os
from .base import BaseGrabber

TRACKING_URL = 'https://www.msc.com/en/track-a-shipment?agencyPath=civ'

_JS = r'''JSON.stringify((() => {
    const clean = value => (value || '').trim();
    const lines = value => clean(value).split('\\n').map(clean).filter(Boolean);
    const detail = lines(document.querySelector('.msc-flow-tracking__details')?.innerText);
    const field = name => detail[detail.indexOf(name) + 1] || '';
    const cells = Array.from(document.querySelectorAll('.msc-flow-tracking__tracking .msc-flow-tracking__cell')).map(row => clean(row.innerText)).filter(Boolean);
    const events = [];
    for (let i = 0; i + 2 < cells.length; i++) if (/^\d{2}\/\d{2}\/\d{4}$/.test(cells[i])) events.push({loc: cells[i + 1], milestone: cells[i + 2] + '\\n' + cells[i]});
    const summary = lines(document.querySelector('.msc-flow-tracking__container')?.innerText);
    const latest = summary[summary.indexOf('Latest move') + 1] || '';
    return {container: field('Container Number'), carrier: 'MSC', from_port: field('Shipped From'), to_port: field('Shipped To'), status: latest ? 'Latest move · ' + latest : '', updated: '', events};
})())'''


class MscGrabber(BaseGrabber):
    NAME = 'msc'
    CARRIERS = ['MSC']

    async def fetch(self) -> dict:
        import nodriver as uc
        browser = await uc.start(headless=os.environ.get('TRACKER_HEADLESS') == '1', browser_args=['--window-size=400,300', '--window-position=99999,99999'])
        try:
            tab = await browser.get(TRACKING_URL)
            await self._wait_for(tab, '#trackingNumber')
            # MSC 的查询表单由 Alpine 驱动，原生 input 事件会同步其状态。
            await tab.evaluate(f'''(() => {{
                const input = document.querySelector('#trackingNumber');
                if (!input) throw new Error('MSC tracking form not found');
                Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, '{self.container_no}');
                input.dispatchEvent(new Event('input', {{bubbles: true}}));
                document.querySelector('form.js-form').requestSubmit();
            }})()''')
            await self._wait_for(tab, '.msc-flow-tracking__details')
            data = json.loads(await tab.evaluate(_JS))
            if data.get('container') != self.container_no:
                raise ValueError('MSC 页面未返回有效数据，请检查箱号或稍后重试')
            return data
        finally:
            browser.stop()


if __name__ == '__main__':
    import sys, json
    no = sys.argv[1] if len(sys.argv) > 1 else 'MSCU1234567'

    async def _test():
        grabber = MscGrabber(no)
        result  = await grabber.fetch()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(_test())
