from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pygame

from maogame.core.input import is_back_key, is_confirm_key, move_selection
from maogame.core.runtime import Runtime
from maogame.core.scene import Scene, SceneTransition

from .logic import DIFFICULTIES, Card, Difficulty, build_deck, choose_target, remove_cards, selection_total


@dataclass(frozen=True)
class SuitStyle:
    color: tuple[int, int, int]


SUIT_STYLES = {
    "hearts": SuitStyle((217, 89, 99)),
    "diamonds": SuitStyle((255, 145, 77)),
    "clubs": SuitStyle((62, 92, 118)),
    "spades": SuitStyle((35, 49, 71)),
}


class PickCardsScene(Scene):
    success_delay = 0.8

    def __init__(self) -> None:
        self.state = "level-select"
        self.level_index = 0
        self.cards: tuple[Card, ...] = ()
        self.target: int | None = None
        self.cursor_index = 0
        self.selected_indices: set[int] = set()
        self.feedback_message = "Choose a level to begin."
        self.feedback_kind = "info"
        self.feedback_timer = 0.0
        self.pending_removal: tuple[int, ...] = ()
        self.rounds_cleared = 0
        self.menu_index = 0

    def handle_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.type != pygame.KEYDOWN:
            return None

        if is_back_key(event):
            return SceneTransition(next_scene=runtime.launcher_scene())

        if self.state == "level-select":
            return self._handle_level_select(event, runtime)
        if self.state == "playing":
            return self._handle_playing(event)
        if self.state == "game-over":
            return self._handle_game_over(event, runtime)
        return None

    def update(self, dt: float, runtime: Runtime) -> SceneTransition | None:
        if self.feedback_timer <= 0:
            return None

        self.feedback_timer = max(0.0, self.feedback_timer - dt)
        if self.feedback_timer > 0 or not self.pending_removal:
            return None

        self.cards = remove_cards(self.cards, self.pending_removal)
        self.pending_removal = ()
        self.rounds_cleared += 1
        self._prepare_round(runtime)
        return None

    def render(self, surface: pygame.Surface, runtime: Runtime) -> None:
        self._draw_background(surface, runtime)

        if self.state == "level-select":
            self._render_level_select(surface, runtime)
            return

        self._render_playfield(surface, runtime)
        if self.state == "game-over":
            self._render_game_over_overlay(surface, runtime)

    def _handle_level_select(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.key in (pygame.K_LEFT, pygame.K_UP):
            self.level_index = move_selection(self.level_index, -1, len(DIFFICULTIES))
            return None
        if event.key in (pygame.K_RIGHT, pygame.K_DOWN):
            self.level_index = move_selection(self.level_index, 1, len(DIFFICULTIES))
            return None
        if is_confirm_key(event):
            self._start_game(runtime)
        return None

    def _handle_playing(self, event: pygame.event.Event) -> SceneTransition | None:
        if self.feedback_timer > 0:
            return None

        if event.key == pygame.K_LEFT:
            self._move_cursor(-1)
            return None
        if event.key == pygame.K_RIGHT:
            self._move_cursor(1)
            return None
        if event.key == pygame.K_UP:
            self._move_cursor(-self._grid_columns())
            return None
        if event.key == pygame.K_DOWN:
            self._move_cursor(self._grid_columns())
            return None
        if is_confirm_key(event):
            self._toggle_selected()
            return None
        if event.key == pygame.K_s:
            self._submit_selection()
            return None
        if event.key == pygame.K_r:
            self.state = "level-select"
            self.feedback_message = "Choose a level to begin."
            self.feedback_kind = "info"
            return None
        return None

    def _handle_game_over(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            self.menu_index = 1 - self.menu_index
            return None
        if event.key == pygame.K_r:
            self._start_game(runtime)
            return None
        if is_confirm_key(event):
            if self.menu_index == 0:
                self._start_game(runtime)
                return None
            return SceneTransition(next_scene=runtime.launcher_scene())
        return None

    def _start_game(self, runtime: Runtime) -> None:
        difficulty = self._difficulty
        self.cards = build_deck(runtime.rng, difficulty)
        self.cursor_index = 0
        self.selected_indices = set()
        self.rounds_cleared = 0
        self.menu_index = 0
        self.pending_removal = ()
        self.feedback_timer = 0.0
        self.state = "playing"
        self._prepare_round(runtime)

    def _prepare_round(self, runtime: Runtime) -> None:
        self.selected_indices.clear()
        if len(self.cards) <= 1:
            self._set_game_over("Only one card remains. Try a fresh deck.")
            return

        target = choose_target(runtime.rng, self.cards, self._difficulty)
        if target is None:
            self._set_game_over("No more matches fit this level. Try a fresh deck.")
            return

        self.target = target
        self.cursor_index = min(self.cursor_index, max(len(self.cards) - 1, 0))
        self.feedback_message = "Pick 2 or more cards, then press S to submit."
        self.feedback_kind = "info"

    def _set_game_over(self, message: str) -> None:
        self.state = "game-over"
        self.target = None
        self.selected_indices.clear()
        self.pending_removal = ()
        self.feedback_message = message
        self.feedback_kind = "info"
        self.menu_index = 0

    def _submit_selection(self) -> None:
        if self.target is None:
            return

        if len(self.selected_indices) < 2:
            self.feedback_message = "Pick at least 2 cards before you submit."
            self.feedback_kind = "error"
            return

        total = selection_total(self.cards, self.selected_indices)
        if total == self.target:
            self.feedback_message = f"Great job! {total} matches the target."
            self.feedback_kind = "success"
            self.feedback_timer = self.success_delay
            self.pending_removal = tuple(sorted(self.selected_indices))
            return

        self.feedback_message = f"That makes {total}. Try a different set."
        self.feedback_kind = "error"

    def _move_cursor(self, delta: int) -> None:
        total = len(self.cards)
        if total <= 0:
            self.cursor_index = 0
            return
        self.cursor_index = (self.cursor_index + delta) % total

    def _toggle_selected(self) -> None:
        if not self.cards:
            return
        if self.cursor_index in self.selected_indices:
            self.selected_indices.remove(self.cursor_index)
        else:
            self.selected_indices.add(self.cursor_index)

    def _grid_columns(self) -> int:
        return 5 if len(self.cards) > 5 else max(len(self.cards), 1)

    @property
    def _difficulty(self) -> Difficulty:
        return DIFFICULTIES[self.level_index]

    def _render_level_select(self, surface: pygame.Surface, runtime: Runtime) -> None:
        palette = runtime.config.palette
        width = runtime.config.window_width

        title_font = runtime.assets.font(48, bold=True)
        body_font = runtime.assets.font(24)
        card_title_font = runtime.assets.font(28, bold=True)
        card_body_font = runtime.assets.font(21)

        title = title_font.render("Pick the Cards", True, palette.text)
        surface.blit(title, title.get_rect(center=(width // 2, 70)))

        subtitle = body_font.render(
            "Choose a difficulty and build the target with 2 or more cards.",
            True,
            palette.text,
        )
        surface.blit(subtitle, subtitle.get_rect(center=(width // 2, 112)))

        specs = (
            "Easy  6 cards  targets 4-10",
            "Medium  8 cards  targets 6-15",
            "Hard  10 cards  targets 8-20  with J Q K",
        )
        for index, difficulty in enumerate(DIFFICULTIES):
            rect = pygame.Rect(98 + index * 255, 185, 220, 240)
            fill = palette.card_selected if index == self.level_index else palette.card
            pygame.draw.rect(surface, fill, rect, border_radius=26)
            pygame.draw.rect(surface, palette.card_border, rect, width=2, border_radius=26)

            title_surface = card_title_font.render(difficulty.title, True, palette.text)
            surface.blit(title_surface, (rect.left + 24, rect.top + 22))

            lines = specs[index].split("  ")
            for line_index, line in enumerate(lines):
                text = card_body_font.render(line, True, palette.text)
                surface.blit(text, (rect.left + 24, rect.top + 82 + line_index * 38))

        help_surface = body_font.render(
            "Arrow keys move. Enter or Space starts. Esc returns to the launcher.",
            True,
            palette.text,
        )
        surface.blit(help_surface, help_surface.get_rect(center=(width // 2, 500)))

        note_surface = body_font.render(
            "A=1, 2-10 face value, J=11, Q=12, K=13.",
            True,
            palette.accent,
        )
        surface.blit(note_surface, note_surface.get_rect(center=(width // 2, 540)))

    def _render_playfield(self, surface: pygame.Surface, runtime: Runtime) -> None:
        palette = runtime.config.palette
        width = runtime.config.window_width
        height = runtime.config.window_height

        title_font = runtime.assets.font(42, bold=True)
        body_font = runtime.assets.font(24)
        info_font = runtime.assets.font(22)
        target_font = runtime.assets.font(64, bold=True)

        title = title_font.render("Pick the Cards", True, palette.text)
        surface.blit(title, (50, 34))

        difficulty_text = body_font.render(f"Level: {self._difficulty.title}", True, palette.accent)
        surface.blit(difficulty_text, (52, 90))

        rounds_text = body_font.render(f"Rounds cleared: {self.rounds_cleared}", True, palette.text)
        surface.blit(rounds_text, (760, 90))

        target_label = body_font.render("Target", True, palette.text)
        surface.blit(target_label, (58, 146))

        target_value = "-" if self.target is None else str(self.target)
        target_surface = target_font.render(target_value, True, palette.accent)
        surface.blit(target_surface, (54, 174))

        selected_total = selection_total(self.cards, self.selected_indices)
        selected_text = info_font.render(f"Selected total: {selected_total}", True, palette.text)
        surface.blit(selected_text, (54, 255))

        instructions = info_font.render(
            "Move with arrows. Space selects. S submits. R picks a new level.",
            True,
            palette.text,
        )
        surface.blit(instructions, (50, height - 46))

        feedback_color = palette.text
        if self.feedback_kind == "success":
            feedback_color = palette.success
        elif self.feedback_kind == "error":
            feedback_color = palette.error

        feedback_surface = info_font.render(self.feedback_message, True, feedback_color)
        surface.blit(feedback_surface, feedback_surface.get_rect(center=(width // 2, 294)))

        self._draw_cards(surface, runtime)

    def _render_game_over_overlay(self, surface: pygame.Surface, runtime: Runtime) -> None:
        palette = runtime.config.palette
        width = runtime.config.window_width
        height = runtime.config.window_height

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 130))
        surface.blit(overlay, (0, 0))

        card = pygame.Rect(220, 150, width - 440, 250)
        pygame.draw.rect(surface, palette.card, card, border_radius=28)
        pygame.draw.rect(surface, palette.card_border, card, width=2, border_radius=28)

        title_font = runtime.assets.font(38, bold=True)
        body_font = runtime.assets.font(24)

        title = title_font.render("Round Complete", True, palette.text)
        surface.blit(title, title.get_rect(center=(card.centerx, card.top + 50)))

        message = body_font.render(self.feedback_message, True, palette.text)
        surface.blit(message, message.get_rect(center=(card.centerx, card.top + 106)))

        summary = body_font.render(
            f"You solved {self.rounds_cleared} target{'s' if self.rounds_cleared != 1 else ''}.",
            True,
            palette.accent,
        )
        surface.blit(summary, summary.get_rect(center=(card.centerx, card.top + 148)))

        labels = ("Play again", "Game menu")
        for index, label in enumerate(labels):
            rect = pygame.Rect(card.left + 70 + index * 180, card.bottom - 86, 150, 48)
            fill = palette.card_selected if index == self.menu_index else palette.accent_soft
            pygame.draw.rect(surface, fill, rect, border_radius=18)
            pygame.draw.rect(surface, palette.card_border, rect, width=2, border_radius=18)
            text = body_font.render(label, True, palette.text)
            surface.blit(text, text.get_rect(center=rect.center))

    def _draw_cards(self, surface: pygame.Surface, runtime: Runtime) -> None:
        if not self.cards:
            return

        columns = self._grid_columns()
        card_width = 120
        card_height = 150
        gap_x = 24
        gap_y = 22
        start_x = 120
        start_y = 340

        for index, card in enumerate(self.cards):
            row = index // columns
            column = index % columns
            rect = pygame.Rect(
                start_x + column * (card_width + gap_x),
                start_y + row * (card_height + gap_y),
                card_width,
                card_height,
            )
            selected = index in self.selected_indices
            focused = index == self.cursor_index and self.state == "playing"
            self._draw_card(surface, rect, card, runtime, selected=selected, focused=focused)

    def _draw_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        card: Card,
        runtime: Runtime,
        *,
        selected: bool,
        focused: bool,
    ) -> None:
        palette = runtime.config.palette
        suit_style = SUIT_STYLES[card.suit]
        card_rect = rect.move(0, -12) if selected else rect

        shadow = card_rect.move(4, 8)
        pygame.draw.rect(surface, (210, 220, 239), shadow, border_radius=18)

        fill = palette.card_selected if selected else palette.card
        border = palette.accent if focused else palette.card_border
        pygame.draw.rect(surface, fill, card_rect, border_radius=18)
        pygame.draw.rect(surface, border, card_rect, width=3 if focused else 2, border_radius=18)

        rank_font = runtime.assets.font(28, bold=True)
        small_font = runtime.assets.font(18, bold=True)
        value_font = runtime.assets.font(21)

        rank = rank_font.render(card.rank, True, suit_style.color)
        surface.blit(rank, (card_rect.left + 12, card_rect.top + 10))

        corner = small_font.render(card.rank, True, suit_style.color)
        corner_rect = corner.get_rect(bottomright=(card_rect.right - 12, card_rect.bottom - 10))
        surface.blit(corner, corner_rect)

        self._draw_suit_icon(surface, card.suit, card_rect.center, suit_style.color)

        value_text = value_font.render(str(card.value), True, palette.text)
        surface.blit(value_text, value_text.get_rect(center=(card_rect.centerx, card_rect.bottom - 24)))

    def _draw_suit_icon(
        self,
        surface: pygame.Surface,
        suit: str,
        center: tuple[int, int],
        color: tuple[int, int, int],
    ) -> None:
        cx, cy = center
        if suit == "hearts":
            pygame.draw.circle(surface, color, (cx - 12, cy - 6), 14)
            pygame.draw.circle(surface, color, (cx + 12, cy - 6), 14)
            pygame.draw.polygon(surface, color, [(cx - 28, cy - 2), (cx + 28, cy - 2), (cx, cy + 34)])
            return
        if suit == "diamonds":
            pygame.draw.polygon(surface, color, [(cx, cy - 30), (cx + 24, cy), (cx, cy + 30), (cx - 24, cy)])
            return
        if suit == "clubs":
            pygame.draw.circle(surface, color, (cx, cy - 18), 13)
            pygame.draw.circle(surface, color, (cx - 15, cy + 2), 13)
            pygame.draw.circle(surface, color, (cx + 15, cy + 2), 13)
            pygame.draw.rect(surface, color, pygame.Rect(cx - 7, cy + 4, 14, 26), border_radius=6)
            pygame.draw.polygon(surface, color, [(cx - 16, cy + 28), (cx + 16, cy + 28), (cx, cy + 42)])
            return
        pygame.draw.polygon(surface, color, [(cx, cy - 34), (cx + 18, cy - 4), (cx + 28, cy + 10), (cx, cy + 4), (cx - 28, cy + 10), (cx - 18, cy - 4)])
        pygame.draw.rect(surface, color, pygame.Rect(cx - 7, cy + 4, 14, 26), border_radius=6)
        pygame.draw.polygon(surface, color, [(cx - 16, cy + 28), (cx + 16, cy + 28), (cx, cy + 42)])

    def _draw_background(self, surface: pygame.Surface, runtime: Runtime) -> None:
        palette = runtime.config.palette
        surface.fill(palette.background)

        pygame.draw.circle(surface, (226, 236, 255), (110, 90), 120)
        pygame.draw.circle(surface, (255, 234, 214), (840, 140), 110)
        pygame.draw.circle(surface, (224, 246, 232), (830, 540), 150)
        pygame.draw.circle(surface, (235, 228, 255), (150, 520), 130)
        pygame.draw.rect(surface, (255, 255, 255), pygame.Rect(34, 24, 892, 592), border_radius=32)
        pygame.draw.rect(surface, (219, 229, 246), pygame.Rect(34, 24, 892, 592), width=2, border_radius=32)