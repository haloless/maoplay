from __future__ import annotations

import pygame

from maogame.core.input import is_back_key, is_confirm_key, move_selection
from maogame.core.runtime import Runtime
from maogame.core.scene import Scene, SceneTransition


class LauncherScene(Scene):
    def __init__(self) -> None:
        self.selected_index = 0
        self.scroll_offset = 0.0

    def handle_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * 36
            self._clamp_scroll(runtime)
            return None

        if event.type != pygame.KEYDOWN:
            return None
        if is_back_key(event):
            return SceneTransition(quit_requested=True)
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self.selected_index = move_selection(self.selected_index, -1, len(runtime.registry))
            self._ensure_selected_visible(runtime)
            return None
        if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.selected_index = move_selection(self.selected_index, 1, len(runtime.registry))
            self._ensure_selected_visible(runtime)
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
        bottom = height - 24
        viewport_height = bottom - top
        total_height = len(runtime.registry) * card_height + max(len(runtime.registry) - 1, 0) * card_gap
        max_scroll = max(0.0, float(total_height - viewport_height))
        self._clamp_scroll(runtime)

        left = 96
        card_width = width - 192
        clip_rect = pygame.Rect(left - 8, top - 8, card_width + 16, viewport_height + 16)

        previous_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        for index, game in enumerate(runtime.registry):
            y = top + index * (card_height + card_gap) - int(self.scroll_offset)
            rect = pygame.Rect(left, y, card_width, card_height)
            if rect.bottom < top or rect.top > bottom:
                continue
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

        surface.set_clip(previous_clip)

        if max_scroll > 0:
            track_rect = pygame.Rect(width - 34, top, 10, viewport_height)
            pygame.draw.rect(surface, palette.accent_soft, track_rect, border_radius=5)
            thumb_height = max(40, int((viewport_height / total_height) * viewport_height))
            thumb_y = top + int((self.scroll_offset / max_scroll) * (viewport_height - thumb_height))
            thumb_rect = pygame.Rect(track_rect.left, thumb_y, track_rect.width, thumb_height)
            pygame.draw.rect(surface, palette.accent, thumb_rect, border_radius=5)

    def _content_height(self, total_games: int) -> int:
        if total_games <= 0:
            return 0
        return total_games * 92 + (total_games - 1) * 20

    def _max_scroll(self, runtime: Runtime) -> float:
        top = 160
        bottom = runtime.config.window_height - 24
        viewport_height = bottom - top
        return max(0.0, float(self._content_height(len(runtime.registry)) - viewport_height))

    def _clamp_scroll(self, runtime: Runtime) -> None:
        self.scroll_offset = max(0.0, min(self.scroll_offset, self._max_scroll(runtime)))

    def _ensure_selected_visible(self, runtime: Runtime) -> None:
        top = 160
        bottom = runtime.config.window_height - 24
        viewport_height = bottom - top

        selected_top = self.selected_index * (92 + 20)
        selected_bottom = selected_top + 92

        if selected_top < self.scroll_offset:
            self.scroll_offset = float(selected_top)
        elif selected_bottom > self.scroll_offset + viewport_height:
            self.scroll_offset = float(selected_bottom - viewport_height)

        self._clamp_scroll(runtime)
