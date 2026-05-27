"""
Maersk Line 抓取器
适用前缀: MSKU MRKU SUDU SEAU TEMU TGHU TGBU TCKU TIIU TRHU CAAU DFSU BANQ FFAU SEKU

使用 nodriver 打开 Maersk 官网追踪页，等待渲染后提取数据。
依赖: pip install nodriver
"""

import asyncio
from .base import BaseGrabber

TRACKING_URL = 'https://www.maersk.com/tracking/{no}'
WAIT_SECONDS = 10   # 等待页面渲染秒数，可根据网速调整

_JS = '''(() => {
    const q  = s => document.querySelector(s);
    const qa = s => Array.from(document.querySelectorAll(s));

    const events = qa('[data-test^="transport-plan-item"]').map(el => ({
        loc:       el.querySelector('[data-test="location-name"]')?.innerText.trim() || "",
        milestone: el.querySelector('[data-test="milestone"]')?.innerText.trim() || ""
    }));

    return {
        container: q('[data-test="transport-doc-value"]')?.innerText.trim() || "",
        from_port: q('[data-test="track-from-value"]')?.innerText.trim() || "",
        to_port:   q('[data-test="track-to-value"]')?.innerText.trim() || "",
        updated:   q('[data-test="last-updated"]')?.innerText.trim() || "",
        status:    q('[data-test="container-location"]')?.innerText.trim() || "",
        events
    };
})()'''


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
            s('⟳ 等待页面渲染（约10秒）...')
            await tab.sleep(WAIT_SECONDS)
            s('⟳ 正在提取运踪数据...')
            raw  = await tab.evaluate(_JS)
            data = self._parse_nodriver(raw)

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