"""
MSC Mediterranean Shipping 抓取器
适用前缀: MSCU MEDU

TODO: 实现抓取逻辑
MSC 官网有 CSRF 保护，需分析实际请求。
临时方案：返回提示信息，引导用户跳转官网。
"""

import asyncio
from .base import BaseGrabber

TRACKING_URL = 'https://www.msc.com/en/track-a-shipment?agencyPath=civ&trackingNumber={no}'


class MscGrabber(BaseGrabber):
    NAME     = 'msc'
    CARRIERS = ['MSC']

    async def fetch(self) -> dict:
        # TODO: 实现 MSC 页面抓取
        # MSC 有较强的反爬，需要分析其追踪 API
        # 暂时抛出异常，由主程序处理（显示"请前往官网"）
        raise NotImplementedError(
            f'MSC 抓取器尚未实现\n'
            f'请手动前往官网查询：\n{TRACKING_URL.format(no=self.container_no)}'
        )


if __name__ == '__main__':
    import sys, json
    no = sys.argv[1] if len(sys.argv) > 1 else 'MSCU1234567'

    async def _test():
        grabber = MscGrabber(no)
        result  = await grabber.fetch()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(_test())