from __future__ import annotations

from typing import Dict, Tuple

import pygame


class AssetManager:
    """Caches fonts so scenes can render text without recreating them every frame."""

    def __init__(self) -> None:
        self._font_cache: Dict[Tuple[int, bool], pygame.font.Font] = {}

    def font(self, size: int, *, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            self._font_cache[key] = pygame.font.SysFont("arial", size, bold=bold)
        return self._font_cache[key]

