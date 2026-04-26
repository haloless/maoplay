from __future__ import annotations

from typing import Dict, Tuple

import pygame


# Try common CJK-capable fonts across macOS/Windows/Linux, then fall back.
_FONT_CANDIDATES: tuple[str, ...] = (
    # macOS
    "PingFang SC",
    "Hiragino Sans GB",
    "Songti SC",
    "STHeiti",
    "Heiti SC",
    # Windows
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    # Linux/common
    "Noto Sans CJK SC",
    "WenQuanYi Zen Hei",
    "Source Han Sans SC",
    # Last resort Latin
    "Arial",
)


def resolve_font_name() -> str | None:
    """Return the first available preferred font name on this system."""
    for candidate in _FONT_CANDIDATES:
        if pygame.font.match_font(candidate):
            return candidate
    return None


class AssetManager:
    """Caches fonts so scenes can render text without recreating them every frame."""

    def __init__(self) -> None:
        self._font_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}
        self._font_name = resolve_font_name()

    def font(self, size: int, *, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            if self._font_name is not None:
                self._font_cache[key] = pygame.font.SysFont(self._font_name, size, bold=bold)
            else:
                self._font_cache[key] = pygame.font.Font(None, size)
        return self._font_cache[key]

