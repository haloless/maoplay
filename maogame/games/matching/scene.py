from __future__ import annotations

from typing import Sequence

import pygame

from maogame.core.quiz import QuizScene
from maogame.core.runtime import Runtime

from .logic import MatchingQuestion, build_question


class MatchingScene(QuizScene):
    def __init__(self) -> None:
        super().__init__(
            title="Letter Match",
            instruction="Pick the small letter that matches the big letter.",
            rounds=5,
        )

    def build_prompt(self, runtime: Runtime) -> MatchingQuestion:
        return build_question(runtime.rng)

    def prompt_lines(self, prompt: MatchingQuestion) -> Sequence[str]:
        return ("Which small letter matches this one?",)

    def choice_labels(self, prompt: MatchingQuestion) -> Sequence[str]:
        return prompt.choices

    def correct_choice_index(self, prompt: MatchingQuestion) -> int:
        return prompt.answer_index

    def draw_prompt_extra(self, surface: pygame.Surface, prompt: MatchingQuestion, runtime: Runtime) -> None:
        palette = runtime.config.palette
        font = runtime.assets.font(90, bold=True)
        text_surface = font.render(prompt.uppercase_letter, True, palette.accent)
        rect = text_surface.get_rect(center=(runtime.config.window_width // 2, 246))
        surface.blit(text_surface, rect)

    def draw_choice(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        prompt: MatchingQuestion,
        index: int,
        label: str,
        runtime: Runtime,
    ) -> None:
        super().draw_choice(surface, rect, prompt, index, label.upper(), runtime)
