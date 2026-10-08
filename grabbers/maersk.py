"""
Maersk Line 抓取器
适用前缀: MSKU MRKU SUDU SEAU TEMU TGHU TGBU TCKU TIIU TRHU CAAU DFSU BANQ FFAU SEKU

使用 nodriver 打开 Maersk 官网追踪页，等待渲染后提取数据。
依赖: pip install nodriver
"""

import asyncio
import json
from .base import BaseGrabber

TRACKING_URL = 'https://www.maersk.com/tracking/{no}'

_JS = '''JSON.stringify((() => {
    const q  = s => document.querySelector(s);
    const qa = s => Array.from(document.querySelectorAll(s));
    const text = (root, selector) => root?.querySelector(selector)?.innerText.trim() || '';

    const events = qa('[data-test="container-event-row"]').map(row => ({
        loc: '', milestone: text(row, '[data-test="event-name"]') + "\\n" + text(row, '[data-test="event-date"]')
    }));
    const current = q('[data-test="container-event-current"]');
    if (current) events.push({
        loc: text(current, '[data-test="event-location-city"]'),
        milestone: text(current, '[data-test="event-name"]') + "\\n" + text(current, '[data-test="event-date"]')
    });

    return {
        container: text(document, '[data-test="ocean-design-bl-value"]'),
        from_port: text(document, '[data-test="accordion-departure-city"]'),
        to_port:   text(document, '[data-test="accordion-arrival-city"]'),
        updated:   text(document, '[data-test="container-last-updated"]'),
        status:    text(q('[data-test="container-event-current"]'), '[data-test="event-name"]'),
        events
    };
})())'''


class MaerskGrabber(BaseGrabber):
    NAME     = 'maersk'
    CARRIERS = ['Maersk Line', 'Hamburg Sud', 'Sealand', 'Textainer', 'Triton International']

    async def fetch(self) -> dict:
        import nodriver as uc
            # 本地快捷函数，避免每次都写 if self.on_status
        def s(msg):
            if self.on_status:
                self.on_status(msg)

        url     = TRACKING_URL.format(no=self.container_no)
        s('⟳ 正在启动浏览器...')
        browser = await uc.start(
            headless=False,
            browser_args=[
                '--window-size=400,300',
                '--window-position=99999,99999',  # 移到屏幕外不可见处
            ]
        )
        try:
            s('⟳ 正在打开 Maersk 追踪页...')
            tab = await browser.get(url)
            s('⟳ 等待页面渲染...')
            await self._wait_for(tab, '[data-test="ocean-design-bl-value"]')
            await tab.evaluate('document.querySelector("[data-test=completed-events-toggle]")?.click()')
            s('⟳ 正在提取运踪数据...')
            data = json.loads(await tab.evaluate(_JS))

            if not data.get('container'):
                raise ValueError('页面未返回有效数据，请检查箱号或稍后重试')

            data['carrier'] = 'Maersk Line'
            return data
        finally:
            browser.stop()


# ── 独立运行测试 ──────────────────────────────────
if __name__ == '__main__':
    import sys, json, warnings
    warnings.filterwarnings('ignore')  # 屏蔽 Windows asyncio 关闭警告

    no = sys.argv[1] if len(sys.argv) > 1 else 'MRSU6845613'

    async def _test():
        grabber = MaerskGrabber(no)
        result  = await grabber.fetch()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(_test())
