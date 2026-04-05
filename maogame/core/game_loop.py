from __future__ import annotations

from typing import Optional

import pygame

from .runtime import Runtime
from .scene import Scene, SceneTransition


class GameLoop:
    def __init__(
        self,
        *,
        screen: pygame.Surface,
        clock: pygame.time.Clock,
        runtime: Runtime,
    ) -> None:
        self._screen = screen
        self._clock = clock
        self._runtime = runtime

    def run(self, initial_scene: Scene, *, max_frames: Optional[int] = None) -> int:
        scene = initial_scene
        scene.on_enter(self._runtime)
        frame_count = 0

        while True:
            dt = self._clock.tick(self._runtime.config.fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 0
                transition = scene.handle_event(event, self._runtime)
                scene, should_quit = self._apply_transition(scene, transition)
                if should_quit:
                    return 0

            transition = scene.update(dt, self._runtime)
            scene, should_quit = self._apply_transition(scene, transition)
            if should_quit:
                return 0

            self._screen.fill(self._runtime.config.palette.background)
            scene.render(self._screen, self._runtime)
            pygame.display.flip()

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                return 0

    def _apply_transition(
        self, current_scene: Scene, transition: Optional[SceneTransition]
    ) -> tuple[Scene, bool]:
        if transition is None:
            return current_scene, False
        if transition.quit_requested:
            return current_scene, True
        if transition.next_scene is None:
            return current_scene, False
        next_scene = transition.next_scene
        next_scene.on_enter(self._runtime)
        return next_scene, False

