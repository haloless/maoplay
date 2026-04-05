from __future__ import annotations

from abc import abstractmethod
from typing import Any, Sequence

import pygame

from .input import digit_choice, is_back_key, is_confirm_key, move_selection
from .runtime import Runtime
from .scene import Scene, SceneTransition


class QuizScene(Scene):
    feedback_duration = 0.9

    def __init__(self, *, title: str, instruction: str, rounds: int) -> None:
        self.title = title
        self.instruction = instruction
        self.rounds = rounds
        self.score = 0
        self.round_index = 0
        self.selected_index = 0
        self.feedback_message = ""
        self.feedback_timer = 0.0
        self.completed = False
        self.current_prompt: Any = None

    def on_enter(self, runtime: Runtime) -> None:
        if self.current_prompt is None and not self.completed:
            self.current_prompt = self.build_prompt(runtime)
            self.selected_index = 0

    def handle_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.type != pygame.KEYDOWN:
            return None
        if is_back_key(event):
            return SceneTransition(next_scene=runtime.launcher_scene())

        if self.completed:
            if is_confirm_key(event):
                return SceneTransition(next_scene=runtime.launcher_scene())
            return None

        if self.feedback_timer > 0 or self.current_prompt is None:
            return None

        total_choices = len(self.choice_labels(self.current_prompt))
        direct_choice = digit_choice(event, total_choices)
        if direct_choice is not None:
            self.selected_index = direct_choice
            return None

        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self.selected_index = move_selection(self.selected_index, -1, total_choices)
            return None
        if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.selected_index = move_selection(self.selected_index, 1, total_choices)
            return None
        if is_confirm_key(event):
            self.submit_choice()
        return None

    def update(self, dt: float, runtime: Runtime) -> SceneTransition | None:
        if self.feedback_timer <= 0:
            return None

        self.feedback_timer = max(0.0, self.feedback_timer - dt)
        if self.feedback_timer > 0:
            return None

        if self.round_index >= self.rounds:
            self.completed = True
            return None

        self.current_prompt = self.build_prompt(runtime)
        self.selected_index = 0
        return None

    def render(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        width = config.window_width

        self._draw_text(
            surface,
            self.title,
            46,
            (width // 2, 52),
            palette.text,
            bold=True,
            center=True,
        )
        self._draw_text(
            surface,
            self.instruction,
            24,
            (width // 2, 96),
            palette.text,
            center=True,
        )
        self._draw_text(
            surface,
            f"Round {min(self.round_index + 1, self.rounds)} of {self.rounds}",
            22,
            (100, 144),
            palette.text,
        )
        self._draw_text(
            surface,
            f"Score: {self.score}",
            22,
            (width - 170, 144),
            palette.text,
        )

        if self.completed:
            self._draw_completion(surface, runtime)
            return

        prompt = self.current_prompt
        if prompt is None:
            return

        self.draw_prompt(surface, prompt, runtime)
        choice_labels = self.choice_labels(prompt)
        start_y = 315
        for index, label in enumerate(choice_labels):
            rect = pygame.Rect(130, start_y + index * 92, width - 260, 72)
            self.draw_choice(surface, rect, prompt, index, label, runtime)

        if self.feedback_message:
            feedback_color = palette.success if "Great" in self.feedback_message else palette.error
            self._draw_text(
                surface,
                self.feedback_message,
                28,
                (width // 2, config.window_height - 52),
                feedback_color,
                bold=True,
                center=True,
            )

    def submit_choice(self) -> None:
        prompt = self.current_prompt
        if prompt is None:
            return

        self.round_index += 1
        if self.is_correct_choice(prompt, self.selected_index):
            self.score += 1
            self.feedback_message = "Great job!"
        else:
            answer = self.choice_labels(prompt)[self.correct_choice_index(prompt)]
            self.feedback_message = f"Nice try! The answer is {answer}."
        self.feedback_timer = self.feedback_duration

    def draw_prompt(self, surface: pygame.Surface, prompt: Any, runtime: Runtime) -> None:
        lines = self.prompt_lines(prompt)
        for index, line in enumerate(lines):
            self._draw_text(
                surface,
                line,
                34 if index == 0 else 26,
                (runtime.config.window_width // 2, 180 + index * 34),
                runtime.config.palette.text,
                bold=index == 0,
                center=True,
            )
        self.draw_prompt_extra(surface, prompt, runtime)

    def draw_prompt_extra(self, surface: pygame.Surface, prompt: Any, runtime: Runtime) -> None:
        return None

    def draw_choice(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        prompt: Any,
        index: int,
        label: str,
        runtime: Runtime,
    ) -> None:
        palette = runtime.config.palette
        fill = palette.card_selected if index == self.selected_index and self.feedback_timer == 0 else palette.card
        border = palette.card_border

        if self.feedback_timer > 0:
            if index == self.correct_choice_index(prompt):
                fill = palette.success
            elif index == self.selected_index:
                fill = palette.error

        pygame.draw.rect(surface, fill, rect, border_radius=18)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=18)
        self._draw_text(surface, label, 30, rect.center, palette.text, bold=True, center=True)

    def _draw_completion(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        card = pygame.Rect(160, 220, config.window_width - 320, 220)
        pygame.draw.rect(surface, palette.card, card, border_radius=24)
        pygame.draw.rect(surface, palette.card_border, card, width=2, border_radius=24)
        self._draw_text(
            surface,
            "All done!",
            42,
            (card.centerx, card.top + 52),
            palette.text,
            bold=True,
            center=True,
        )
        self._draw_text(
            surface,
            f"You scored {self.score} out of {self.rounds}.",
            30,
            (card.centerx, card.centery - 12),
            palette.text,
            center=True,
        )
        self._draw_text(
            surface,
            "Press Enter or Space to return to the game menu.",
            24,
            (card.centerx, card.bottom - 54),
            palette.accent,
            center=True,
        )

    def _draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        size: int,
        position: tuple[int, int],
        color: tuple[int, int, int],
        *,
        bold: bool = False,
        center: bool = False,
    ) -> None:
        font = pygame.font.SysFont("arial", size, bold=bold)
        text_surface = font.render(text, True, color)
        rect = text_surface.get_rect()
        if center:
            rect.center = position
        else:
            rect.topleft = position
        surface.blit(text_surface, rect)

    @abstractmethod
    def build_prompt(self, runtime: Runtime) -> Any:
        raise NotImplementedError

    @abstractmethod
    def prompt_lines(self, prompt: Any) -> Sequence[str]:
        raise NotImplementedError

    @abstractmethod
    def choice_labels(self, prompt: Any) -> Sequence[str]:
        raise NotImplementedError

    @abstractmethod
    def correct_choice_index(self, prompt: Any) -> int:
        raise NotImplementedError

    def is_correct_choice(self, prompt: Any, selected_index: int) -> bool:
        return selected_index == self.correct_choice_index(prompt)

