"""
OOCL 抓取器
适用前缀: OOLU OOCU

流程：
1. 打开 OOCL 追踪页，轮询等待页面加载
2. 关闭 Cookie 弹窗
3. 拦截 window.open，让结果在当前 tab 内加载
4. 选择 Container # 类型，填入箱号，点击 Search
5. 等待结果页加载（同一 tab）
6. 如有滑块验证码，提示用户手动完成
7. 提取追踪数据并翻译成中文
"""

import asyncio
from .base import BaseGrabber

TRACKING_URL  = 'https://www.oocl.com/eng/ourservices/eservices/cargotracking/Pages/cargotracking.aspx'
MAX_WAIT      = 120
POLL_INTERVAL = 2

EVENT_MAP = {
    'Container Returned to Carrier':  '空箱已还',
    'Arrived':                        '到达',
    'Departed':                       '离开',
    'Carrier Released':               '承运人放货',
    'Freight Charges Settled':        '运费结清',
    'Freight\xa0Charges\xa0Settled':  '运费结清',
    'Discharged':                     '卸货',
    'Vessel Arrived':                 '船舶抵港',
    'Loaded':                         '装船',
    'Gate In':                        '进闸',
    'Gate Out':                       '出闸',
    'Gate Out Empty':                 '空箱出闸',
    'Empty to Shipper':               '空箱交货方',
    'Stuffed':                        '装箱',
    'Vessel Departed':                '船舶离港',
    'Transshipment Loaded':           '转船装船',
    'Transshipment Discharged':       '转船卸货',
    'Rail Departed':                  '铁路出发',
    'Rail Arrived':                   '铁路到达',
    'On Rail':                        '铁路运输中',
    'Customs Released':               '海关放行',
    'Container Available':            '箱可提取',
    'Delivery Order Issued':          '提货单已出',
    'Full Container Picked Up':       '重箱提取',
    'Empty Container Returned':       '空箱归还',
}

def translate_event(name: str) -> str:
    return EVENT_MAP.get(name.strip(), name.strip())


class OoclGrabber(BaseGrabber):
    NAME     = 'oocl'
    CARRIERS = ['OOCL']

    async def fetch(self) -> dict:
        import nodriver as uc
        import os

        def s(msg):
            if self.on_status:
                self.on_status(msg)

        async def wait_until(tab, js_condition, timeout=60, interval=POLL_INTERVAL, msg=None):
            elapsed = 0
            while elapsed < timeout:
                try:
                    result = await tab.evaluate(js_condition)
                    val = result
                    if isinstance(result, list):
                        val = result[0][1].get('value') if result else False
                    if val:
                        return True
                except Exception:
                    pass
                await tab.sleep(interval)
                elapsed += interval
                if msg:
                    s(f'{msg}（{timeout - elapsed}秒后超时）')
            return False

        s('⟳ 正在启动浏览器...')
        browser = await uc.start(
            headless=False,
            browser_args=['--window-size=900,650', '--window-position=100,100']
        )
        try:
            s('⟳ 正在打开 OOCL 追踪页...')
            tab = await browser.get(TRACKING_URL)

            s('⟳ 正在等待页面加载...')
            await wait_until(tab, 'document.querySelector("#SEARCH_NUMBER") !== null',
                             timeout=30, msg='⟳ 等待页面加载')

            s('⟳ 正在关闭 Cookie 弹窗...')
            try:
                btn = await tab.find('Accept All', timeout=15)
                await btn.click()
                await wait_until(tab,
                    'document.querySelector(".cookie-notice, #cookieModal, [class*=cookie]") === null '
                    '|| document.querySelector(".cookie-notice, #cookieModal, [class*=cookie]").offsetParent === null',
                    timeout=10)
                print('Cookie: closed')
            except Exception as e:
                print(f'Cookie: skipped ({e})')

            # 拦截 window.open，让结果在当前 tab 内加载
            await tab.evaluate('''(() => {
                window.open = function(url, name, features) {
                    window.location.href = url;
                    return window;
                };
            })()''')
            print('window.open: intercepted')

            s('⟳ 正在选择查询类型...')
            no = self.container_no
            await tab.evaluate('''(() => {
                var sel = document.getElementById('ooclCargoSelector');
                if (sel) {
                    sel.value = 'cont';
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                }
                var st = document.getElementById('searchType');
                if (st) st.value = 'cont';
            })()''')

            s('⟳ 正在填写箱号...')
            await tab.evaluate('''(() => {
                var input = document.getElementById('SEARCH_NUMBER');
                if (input) {
                    input.value = "''' + no + '''";
                    input.dispatchEvent(new Event('input',  {bubbles: true}));
                    input.dispatchEvent(new Event('change', {bubbles: true}));
                }
            })()''')

            s('⟳ 正在提交查询...')
            await tab.evaluate('ListeningCargoTrackingBtn()')

            s('⟳ 正在等待结果页加载...')
            await wait_until(tab,
                'window.location.href.includes("pbservice.moc.oocl.com") || '
                'window.location.href.includes("ct_result") || '
                'window.location.href.includes("ct_no_record")',
                timeout=30, msg='⟳ 等待结果页跳转')
            await wait_until(tab, 'document.readyState === "complete"',
                             timeout=30, msg='⟳ 等待结果页加载')

            # 检查滑块验证码
            has_captcha = await tab.evaluate('''(() => {
                var c = document.querySelector('#cs_captcha');
                return (c && c.offsetParent !== null) ? 'yes' : 'no';
            })()''')

            if 'yes' in str(has_captcha):
                s('⚠ 请在浏览器窗口中完成滑块验证，完成后自动继续...')
                passed = await wait_until(tab, '''(() => {
                    var c = document.querySelector('#cs_captcha');
                    return (!c || c.offsetParent === null) ? true : false;
                })()''', timeout=MAX_WAIT, interval=3, msg='⚠ 请完成滑块验证')
                if not passed:
                    raise TimeoutError('等待验证超时（120秒），请重试')
                s('✔ 验证通过，正在提取数据...')

            s('⟳ 正在等待追踪数据...')
            await wait_until(tab, 'document.querySelector("#summaryTable") !== null',
                             timeout=30, msg='⟳ 等待追踪数据')

            # 切换到 Equipment Activities 标签
            await tab.evaluate('''(() => {
                if (typeof showContainerTab === "function") showContainerTab("Tab2", 2);
            })()''')

            # 等待事件列表出现
            await wait_until(tab,
                'document.querySelector(\'[id$="eventLocationDetail0"]\') !== null',
                timeout=15, msg='⟳ 等待运踪事件')

            debug = await tab.evaluate('''(() => {
                const q = s => document.querySelector(s);
                const el0 = q('[id$="eventLocationDetail0"]');
                const dt0 = q('[id$="eventDateDetail0"]');
                const tab2 = document.getElementById('Tab2');
                return {
                    el0_exists:  el0 !== null,
                    el0_text:    el0 ? el0.innerText : 'null',
                    dt0_exists:  dt0 !== null,
                    dt0_text:    dt0 ? dt0.innerText : 'null',
                    tab2_display: tab2 ? tab2.style.display : 'null'
                };
            })()''')
            print('DEBUG:', debug)

            s('⟳ 正在提取运踪数据...')
            js = '''(() => {
                const q = s => document.querySelector(s);
                const qa = s => Array.from(document.querySelectorAll(s));

                const pol          = q('[id$="POLLocation0"]');
                const dest         = q('[id$="finalDestination0"]');
                const latestEvDate = q('[id$="eventDate0"]');
                const latestEvLoc  = q('[id$="eventLocation0"]');

                // 直接取 Tab2 里的所有 tr
                const tab2 = document.getElementById('Tab2');
                const events = [];
                if (tab2) {
                    const rows = tab2.querySelectorAll('table tr');
                    rows.forEach(tr => {
                        const tds = tr.querySelectorAll('td');
                        if (tds.length < 3) return;
                        const evName = Array.from(tds[0].childNodes)
                            .filter(n => n.nodeType === 3)
                            .map(n => n.textContent.trim())
                            .join('').trim();
                        const loc  = tds[2] ? tds[2].innerText.trim() : '';
                        const time = tds[4] ? tds[4].innerText.trim() : '';
                        if (evName || loc || time) {
                            events.push({
                                loc:       loc,
                                milestone: evName + (time ? '\\n' + time : '')
                            });
                        }
                    });
                }

                return {
                    container: "''' + no + '''",
                    carrier:   'OOCL',
                    from_port: pol  ? pol.innerText.trim()  : '',
                    to_port:   dest ? dest.innerText.trim() : '',
                    status:    (latestEvDate ? latestEvDate.innerText.trim() : '') +
                            (latestEvLoc  ? ' • ' + latestEvLoc.innerText.trim() : ''),
                    updated:   '',
                    events:    events
                };
            })()'''
            raw = await tab.evaluate(js)

            # 解析 nodriver 返回格式
            if isinstance(raw, dict):
                data = raw
            elif isinstance(raw, list):
                data = {}
                for item in raw:
                    if isinstance(item, list) and len(item) == 2:
                        k, v = item[0], item[1]
                        if k == 'events':
                            evs = []
                            for ev in (v.get('value') if isinstance(v, dict) else v or []):
                                if isinstance(ev, dict):
                                    evs.append(ev)
                                elif isinstance(ev, list):
                                    obj = {}
                                    for kv in ev:
                                        obj[kv[0]] = kv[1].get('value','') if isinstance(kv[1],dict) else kv[1]
                                    evs.append(obj)
                            data['events'] = evs
                        else:
                            data[k] = v.get('value','') if isinstance(v, dict) else v
            else:
                data = {'container': no, 'carrier': 'OOCL',
                        'from_port': '', 'to_port': '',
                        'status': '', 'updated': '', 'events': []}

            # 事件名称翻译成中文
            translated = []
            for ev in data.get('events', []):
                ms    = ev.get('milestone', '')
                parts = ms.split('\n', 1)
                zh    = translate_event(parts[0])
                time  = parts[1] if len(parts) > 1 else ''
                translated.append({
                    'loc':       ev.get('loc', ''),
                    'milestone': zh + ('\n' + time if time else '')
                })
            data['events']    = translated
            data['container'] = no
            data['carrier']   = 'OOCL'
            return data

        finally:
            browser.stop()


# ── 独立运行测试 ──────────────────────────────────
if __name__ == '__main__':
    import sys, json, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    no = sys.argv[1] if len(sys.argv) > 1 else 'OOCU9418353'

    async def _test():
        g = OoclGrabber(no)
        g.on_status = lambda m: print(m)
        result = await g.fetch()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(_test())