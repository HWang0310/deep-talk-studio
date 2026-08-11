"""Renderer adapter factory for Production 0.6."""

from .base import RendererError
from .hyperframes import HyperFramesRenderer
from .remotion import RemotionRenderer


def get_renderer(name: str):
    if name == "remotion":
        return RemotionRenderer()
    if name == "hyperframes":
        return HyperFramesRenderer()
    raise RendererError(f"不支持的 Production renderer：{name}")


__all__ = ["get_renderer", "RendererError", "RemotionRenderer", "HyperFramesRenderer"]
