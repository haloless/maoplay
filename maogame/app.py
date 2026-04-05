from __future__ import annotations

import argparse
import os
from typing import Optional, Sequence

from maogame.config import AppConfig
from maogame.core.registry import find_game, load_games
from maogame.core.runtime import Runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MaoGame mini-game launcher.")
    parser.add_argument("--list-games", action="store_true", help="Print the available game IDs.")
    parser.add_argument("--start-game", help="Start the given game directly.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Use pygame's dummy video driver for smoke tests or CI.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        help="Exit after the given number of frames. Useful for headless smoke tests.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    games = load_games()

    if args.list_games:
        for game in games:
            print(f"{game.game_id}: {game.title}")
        return 0

    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    try:
        import pygame
    except ModuleNotFoundError as exc:
        if exc.name == "pygame":
            raise SystemExit(
                "pygame is not installed in .venv. Run `.venv/bin/python -m pip install -e .` first."
            ) from exc
        raise

    from maogame.core.assets import AssetManager
    from maogame.core.game_loop import GameLoop
    from maogame.launcher import LauncherScene

    pygame.init()
    pygame.font.init()
    config = AppConfig()

    try:
        screen = pygame.display.set_mode((config.window_width, config.window_height))
        pygame.display.set_caption(config.title)
        clock = pygame.time.Clock()
        runtime = Runtime(config=config, assets=AssetManager(), registry=games)
        runtime.launcher_factory = LauncherScene

        if args.start_game:
            initial_scene = find_game(args.start_game, games).scene_factory()
        else:
            initial_scene = runtime.launcher_scene()

        loop = GameLoop(screen=screen, clock=clock, runtime=runtime)
        return loop.run(initial_scene, max_frames=args.max_frames)
    finally:
        pygame.quit()
