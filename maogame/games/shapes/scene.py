from __future__ import annotations

from math import cos, pi, sin
from typing import Sequence

import pygame

from maogame.core.quiz import QuizScene
from maogame.core.runtime import Runtime

from .logic import ShapeQuestion, build_question


class ShapesScene(QuizScene):
    def __init__(self) -> None:
        super().__init__(
            title="Shape Match",
            instruction="Choose the shape named on the screen.",
            rounds=5,
        )

    def build_prompt(self, runtime: Runtime) -> ShapeQuestion:
        return build_question(runtime.rng)

    def prompt_lines(self, prompt: ShapeQuestion) -> Sequence[str]:
        return (f"Find the {prompt.target_shape}.",)

    def choice_labels(self, prompt: ShapeQuestion) -> Sequence[str]:
        return tuple(shape.title() for shape in prompt.choices)

    def correct_choice_index(self, prompt: ShapeQuestion) -> int:
        return prompt.answer_index

    def draw_choice(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        prompt: ShapeQuestion,
        index: int,
        label: str,
        runtime: Runtime,
    ) -> None:
        super().draw_choice(surface, rect, prompt, index, label, runtime)

        shape_name = prompt.choices[index]
        center = (rect.left + 60, rect.centery)
        self._draw_shape(surface, center, shape_name, runtime)

    def _draw_shape(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        shape_name: str,
        runtime: Runtime,
    ) -> None:
        palette = runtime.config.palette
        if shape_name == "circle":
            pygame.draw.circle(surface, palette.shape_circle, center, 22)
        elif shape_name == "square":
            rect = pygame.Rect(center[0] - 22, center[1] - 22, 44, 44)
            pygame.draw.rect(surface, palette.shape_square, rect, border_radius=8)
        elif shape_name == "triangle":
            points = [
                (center[0], center[1] - 26),
                (center[0] - 26, center[1] + 18),
                (center[0] + 26, center[1] + 18),
            ]
            pygame.draw.polygon(surface, palette.shape_triangle, points)
        elif shape_name == "star":
            points = []
            for index in range(10):
                radius = 24 if index % 2 == 0 else 10
                angle = pi / 2 + index * pi / 5
                points.append((center[0] + radius * cos(angle), center[1] - radius * sin(angle)))
            pygame.draw.polygon(surface, palette.shape_star, points)

