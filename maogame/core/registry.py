from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .scene import Scene


@dataclass(frozen=True)
class GameSpec:
    game_id: str
    title: str
    summary: str
    age_band: str
    scene_factory: Callable[[], "Scene"]


def load_games() -> tuple[GameSpec, ...]:
    from maogame.games import REGISTERED_GAMES

    return REGISTERED_GAMES


def find_game(game_id: str, games: Sequence[GameSpec]) -> GameSpec:
    for game in games:
        if game.game_id == game_id:
            return game
    available = ", ".join(game.game_id for game in games)
    raise ValueError(f"Unknown game '{game_id}'. Available games: {available}")

