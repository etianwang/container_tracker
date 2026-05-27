"""
抓取器基类
所有抓取器继承此类，实现 fetch() 方法

返回数据格式（标准化）:
{
    "container":  "MRSU6845613",
    "carrier":    "Maersk Line",
    "from_port":  "HAIPHONG - LACH HUYEN",
    "to_port":    "CHICAGO",
    "status":     "Empty container return • CHICAGO, UNITED STATES • 30 Apr 2026",
    "updated":    "Last updated: 26 days ago",
    "events": [
        {
            "loc":       "Haiphong\nMatran Depot",
            "milestone": "Gate out Empty\n14 Mar 2026 20:18"
        },
        ...
    ]
}
"""

from abc import ABC, abstractmethod


class BaseGrabber(ABC):
    """所有抓取器的基类"""

    NAME = 'base'          # 抓取器标识符，子类必须覆盖
    CARRIERS = []          # 支持的承运商名称列表

    def __init__(self, container_no: str):
        self.container_no = container_no.upper().strip()
        self.on_status = None  # 进度回调，由 FetchWorker 注入
        
    @abstractmethod
    async def fetch(self) -> dict:
        """
        抓取并返回标准格式的追踪数据。
        抛出异常表示失败，调用方捕获处理。
        """
        raise NotImplementedError

    def _empty_result(self) -> dict:
        """返回空结果骨架"""
        return {
            'container': self.container_no,
            'carrier':   '',
            'from_port': '',
            'to_port':   '',
            'status':    '',
            'updated':   '',
            'events':    []
        }

    @staticmethod
    def _parse_nodriver(raw: list) -> dict:
        """
        解析 nodriver evaluate() 返回的嵌套格式
        raw 是 list of [key, {type, value}] 对
        """
        result = {}
        for item in raw:
            key = item[0]
            val = item[1]
            if key == 'events':
                events = []
                for ev in val.get('value', []):
                    obj = {}
                    for kv in ev.get('value', []):
                        obj[kv[0]] = (
                            kv[1].get('value', '')
                            if isinstance(kv[1], dict) else kv[1]
                        )
                    events.append(obj)
                result['events'] = events
            else:
                result[key] = (
                    val.get('value', '')
                    if isinstance(val, dict) else val
                )
        return result