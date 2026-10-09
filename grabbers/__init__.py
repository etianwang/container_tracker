"""
抓取器注册表
根据承运商名称动态加载对应的抓取器
"""

import importlib
from .base import BaseGrabber
from .official import OfficialGrabber

REGISTRY = {
    'maersk':    'grabbers.maersk',
    'msc':       'grabbers.msc',
    'cosco':     'grabbers.cosco',
    'oocl':      'grabbers.oocl',
    '17track':   'grabbers.track17',
}


def get_grabber(grabber_name: str, container_no: str,
                carrier_name: str | None = None) -> BaseGrabber | None:
    if grabber_name not in REGISTRY:
        return OfficialGrabber(container_no, grabber_name, carrier_name)
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
        # The official tracker remains usable even when a site-specific module
        # is absent or has become incompatible with the carrier website.
        return OfficialGrabber(container_no, grabber_name, carrier_name)
    return OfficialGrabber(container_no, grabber_name, carrier_name)
