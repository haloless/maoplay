from __future__ import annotations

import pygame

from maogame.core.input import is_back_key, is_confirm_key, move_selection
from maogame.core.runtime import Runtime
from maogame.core.scene import Scene, SceneTransition


class LauncherScene(Scene):
    def __init__(self) -> None:
        self.selected_index = 0

    def handle_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.type != pygame.KEYDOWN:
            return None
        if is_back_key(event):
            return SceneTransition(quit_requested=True)
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self.selected_index = move_selection(self.selected_index, -1, len(runtime.registry))
            return None
        if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.selected_index = move_selection(self.selected_index, 1, len(runtime.registry))
            return None
        if is_confirm_key(event):
            game = runtime.registry[self.selected_index]
            return SceneTransition(next_scene=game.scene_factory())
        return None

    def render(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        width = config.window_width
        height = config.window_height

        title_font = runtime.assets.font(52, bold=True)
        text_font = runtime.assets.font(28)
        card_title_font = runtime.assets.font(28, bold=True)
        card_text_font = runtime.assets.font(20)

        title = title_font.render("MaoGame", True, palette.text)
        title_rect = title.get_rect(center=(width // 2, 68))
        surface.blit(title, title_rect)

        subtitle = text_font.render(
            "Choose a mini-game. Press Esc to quit.", True, palette.text
        )
        subtitle_rect = subtitle.get_rect(center=(width // 2, 114))
        surface.blit(subtitle, subtitle_rect)

        card_height = 92
        card_gap = 20
        top = 160
        total_height = len(runtime.registry) * card_height + max(len(runtime.registry) - 1, 0) * card_gap
        if top + total_height > height - 24:
            card_height = 80
            card_gap = 14
            total_height = len(runtime.registry) * card_height + max(len(runtime.registry) - 1, 0) * card_gap

        left = 96
        card_width = width - 192

        for index, game in enumerate(runtime.registry):
            rect = pygame.Rect(left, top + index * (card_height + card_gap), card_width, card_height)
            fill = palette.card_selected if index == self.selected_index else palette.card
            pygame.draw.rect(surface, fill, rect, border_radius=22)
            pygame.draw.rect(surface, palette.card_border, rect, width=2, border_radius=22)

            title_surface = card_title_font.render(game.title, True, palette.text)
            surface.blit(title_surface, (rect.left + 24, rect.top + 14))

            summary_surface = card_text_font.render(game.summary, True, palette.text)
            surface.blit(summary_surface, (rect.left + 24, rect.top + 46))

            age_surface = card_text_font.render(game.age_band, True, palette.accent)
            age_rect = age_surface.get_rect(topright=(rect.right - 24, rect.top + 18))
            surface.blit(age_surface, age_rect)
