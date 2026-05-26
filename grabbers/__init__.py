"""
抓取器注册表
根据承运商名称动态加载对应的抓取器
"""

import importlib
from .base import BaseGrabber

REGISTRY = {
    'maersk':    'grabbers.maersk',
    'msc':       'grabbers.msc',
    'cosco':     'grabbers.cosco',
    'cmacgm':    'grabbers.cmacgm',
    'evergreen': 'grabbers.evergreen',
    'hapag':     'grabbers.hapag',
    'hmm':       'grabbers.hmm',
    'oocl':      'grabbers.oocl',
    'yangming':  'grabbers.yangming',
    'zim':       'grabbers.zim',
    'pil':       'grabbers.pil',
    'wanhai':    'grabbers.wanhai',
}


def get_grabber(grabber_name: str, container_no: str) -> BaseGrabber | None:
    if grabber_name not in REGISTRY:
        return None
    try:
        module = importlib.import_module(REGISTRY[grabber_name])
        for attr in dir(module):
            cls = getattr(module, attr)
            if (isinstance(cls, type)
                    and issubclass(cls, BaseGrabber)
                    and cls is not BaseGrabber
                    and cls.NAME == grabber_name):
                return cls(container_no)
    except Exception:
        pass
    return None