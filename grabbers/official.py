"""Fallback for carriers whose public tracking page requires interaction or CAPTCHA."""

import webbrowser

from core import carriers
from .base import BaseGrabber


class OfficialGrabber(BaseGrabber):
    """Open the carrier's official tracker without inventing unverifiable tracking data."""

    NAME = 'official'

    def __init__(self, container_no: str, grabber_name: str, carrier_name: str | None = None):
        super().__init__(container_no)
        self.grabber_name = grabber_name
        self.carrier_name = carrier_name

    async def fetch(self) -> dict:
        url = carriers.get_tracking_url(self.container_no, self.grabber_name)
        if not url:
            raise ValueError('未找到该承运商的官方追踪页面。')
        if self.on_status:
            self.on_status('⟳ 正在打开承运商官网追踪页...')
        webbrowser.open(url)
        data = self._empty_result()
        data.update({
            'carrier': self.carrier_name or carriers.get_carrier_name(self.container_no),
            'status': '官网追踪页已打开；如页面要求，请输入箱号或完成验证码。',
            'updated': '此承运商暂由官网完成交互式查询',
            '_skip_cache': True,
        })
        return data
