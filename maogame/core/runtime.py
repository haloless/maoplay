from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, TYPE_CHECKING

from maogame.config import AppConfig

if TYPE_CHECKING:
    from .assets import AssetManager
    from .registry import GameSpec
    from .scene import Scene


@dataclass
class Runtime:
    config: AppConfig
    assets: "AssetManager"
    registry: Sequence["GameSpec"]
    launcher_factory: Optional[Callable[[], "Scene"]] = None
    rng: random.Random = field(default_factory=random.Random)

    def launcher_scene(self) -> "Scene":
        if self.launcher_factory is None:
            raise RuntimeError("Launcher scene factory has not been configured.")
        return self.launcher_factory()
