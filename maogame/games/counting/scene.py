from __future__ import annotations

from typing import Sequence

import pygame

from maogame.core.quiz import QuizScene
from maogame.core.runtime import Runtime

from .logic import CountingQuestion, build_question


class CountingScene(QuizScene):
    def __init__(self) -> None:
        super().__init__(
            title="Counting Stars",
            instruction="Count the stars, then choose the matching number.",
            rounds=5,
        )

    def build_prompt(self, runtime: Runtime) -> CountingQuestion:
        return build_question(runtime.rng)

    def prompt_lines(self, prompt: CountingQuestion) -> Sequence[str]:
        return ("How many stars can you see?",)

    def choice_labels(self, prompt: CountingQuestion) -> Sequence[str]:
        return tuple(str(choice) for choice in prompt.choices)

    def correct_choice_index(self, prompt: CountingQuestion) -> int:
        return prompt.answer_index

    def draw_prompt_extra(self, surface: pygame.Surface, prompt: CountingQuestion, runtime: Runtime) -> None:
        palette = runtime.config.palette
        start_x = 280
        step = 44
        y = 250
        for index in range(prompt.count):
            center = (start_x + index * step, y)
            pygame.draw.circle(surface, palette.accent_soft, center, 16)
            pygame.draw.circle(surface, palette.accent, center, 16, width=3)

