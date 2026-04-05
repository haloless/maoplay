from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from .runtime import Runtime


@dataclass(frozen=True)
class SceneTransition:
    next_scene: Optional["Scene"] = None
    quit_requested: bool = False


class Scene(ABC):
    def on_enter(self, runtime: "Runtime") -> None:
        """Hook for scene setup after it becomes active."""

    def handle_event(
        self, event: pygame.event.Event, runtime: "Runtime"
    ) -> Optional[SceneTransition]:
        return None

    def update(self, dt: float, runtime: "Runtime") -> Optional[SceneTransition]:
        return None

    @abstractmethod
    def render(self, surface: pygame.Surface, runtime: "Runtime") -> None:
        """Draw a full frame for the active scene."""

