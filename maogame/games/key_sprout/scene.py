from __future__ import annotations

from dataclasses import dataclass
import math
import string

import pygame

from maogame.core.input import is_back_key, is_confirm_key, move_selection
from maogame.core.runtime import Runtime
from maogame.core.scene import Scene, SceneTransition

from .logic import (
    ALPHA_WORD_CANDIDATES,
    DIFFICULTIES,
    Difficulty,
    RoundState,
    accuracy_percent,
    choose_next_target,
    choose_word_target,
    compute_star_rating,
    initial_round_state,
    is_round_over,
    register_hit,
    register_miss,
    tick_timer,
)


VALID_TYPED_CHARS = set(string.ascii_letters + string.digits)
VALID_WORD_CHARS = set(string.ascii_letters + "'")
PLAY_MODES = ("char", "word")


@dataclass
class ScorePop:
    text: str
    x: float
    y: float
    ttl: float


@dataclass
class ConfettiParticle:
    x: float
    y: float
    vx: float
    vy: float
    ttl: float
    color: tuple[int, int, int]


class KeySproutScene(Scene):
    def __init__(self) -> None:
        self.state = "level-select"
        self.level_index = 0
        self.round_state: RoundState | None = None
        self.current_target = ""
        self.previous_target: str | None = None
        self.repeat_count = 0
        self.prompt_time_left = 0.0
        self.target_anim_t = 0.0
        self.miss_anim_t = 0.0
        self.score_pops: list[ScorePop] = []
        self.confetti: list[ConfettiParticle] = []
        self.feedback_text = "Pick a level and start growing your garden."
        self.feedback_color_kind = "info"
        self.best_scores = {difficulty.level_id: 0 for difficulty in DIFFICULTIES}
        self.menu_index = 0
        self.play_mode = "char"
        self.current_input = ""
        self.relaxed_mode = False

    def handle_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            return SceneTransition(next_scene=runtime.launcher_scene())
        if event.key == pygame.K_BACKSPACE and not (
            self.state == "playing" and self.play_mode == "word"
        ):
            return SceneTransition(next_scene=runtime.launcher_scene())

        if self.state == "level-select":
            return self._handle_level_select(event, runtime)
        if self.state == "playing":
            return self._handle_playing(event, runtime)
        if self.state == "results":
            return self._handle_results(event, runtime)
        return None

    def update(self, dt: float, runtime: Runtime) -> SceneTransition | None:
        self._update_particles(dt)

        for pop in self.score_pops:
            pop.ttl -= dt
            pop.y -= dt * 40
        self.score_pops = [pop for pop in self.score_pops if pop.ttl > 0]

        self.target_anim_t = max(0.0, self.target_anim_t - dt)
        self.miss_anim_t = max(0.0, self.miss_anim_t - dt)

        if self.state != "playing" or self.round_state is None:
            return None

        dt_ms = int(dt * 1000)
        if not self.relaxed_mode:
            self.round_state = tick_timer(self.round_state, dt_ms)
            self.prompt_time_left = max(0.0, self.prompt_time_left - dt)

            if self.prompt_time_left <= 0 and not is_round_over(self.round_state):
                self._register_miss(runtime)

        if is_round_over(self.round_state):
            self._finish_round()

        return None

    def render(self, surface: pygame.Surface, runtime: Runtime) -> None:
        self._draw_background(surface)

        if self.state == "level-select":
            self._render_level_select(surface, runtime)
            return

        if self.state == "playing":
            self._render_play(surface, runtime)
            return

        self._render_results(surface, runtime)

    def _handle_level_select(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.key in (pygame.K_LEFT, pygame.K_UP):
            self.level_index = move_selection(self.level_index, -1, len(DIFFICULTIES))
            return None
        if event.key in (pygame.K_RIGHT, pygame.K_DOWN):
            self.level_index = move_selection(self.level_index, 1, len(DIFFICULTIES))
            return None
        if event.key in (pygame.K_TAB, pygame.K_m):
            mode_index = PLAY_MODES.index(self.play_mode)
            self.play_mode = PLAY_MODES[(mode_index + 1) % len(PLAY_MODES)]
            return None
        if event.key == pygame.K_r:
            self.relaxed_mode = not self.relaxed_mode
            return None
        if is_confirm_key(event):
            self._start_round(runtime)
        return None

    def _handle_playing(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if self.round_state is None:
            return None

        if self.play_mode == "word":
            self._handle_word_mode_key(event, runtime)
            if self.round_state and is_round_over(self.round_state):
                self._finish_round()
            return None

        typed = event.unicode if isinstance(event.unicode, str) else ""
        if len(typed) != 1 or typed not in VALID_TYPED_CHARS:
            return None

        if typed == self.current_target:
            self._register_hit(runtime)
        else:
            self._register_miss(runtime)

        if self.round_state and is_round_over(self.round_state):
            self._finish_round()
        return None

    def _handle_word_mode_key(self, event: pygame.event.Event, runtime: Runtime) -> None:
        if event.key == pygame.K_BACKSPACE:
            self.current_input = self.current_input[:-1]
            if self.current_target.startswith(self.current_input):
                self.feedback_text = "Good fix. Keep typing."
                self.feedback_color_kind = "info"
            return

        typed = event.unicode if isinstance(event.unicode, str) else ""
        if len(typed) != 1 or typed not in VALID_WORD_CHARS:
            return

        if len(self.current_input) >= len(self.current_target):
            return

        self.current_input += typed.lower()
        if not self.current_target.startswith(self.current_input):
            self.feedback_text = "Use Backspace to correct this word."
            self.feedback_color_kind = "error"
            return

        self.feedback_text = "Nice. Keep typing the word."
        self.feedback_color_kind = "info"
        if self.current_input == self.current_target:
            self._register_hit(runtime)

    def _handle_results(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            self.menu_index = 1 - self.menu_index
            return None
        if is_confirm_key(event):
            if self.menu_index == 0:
                self.state = "level-select"
                self.feedback_text = "Pick a level and start growing your garden."
                self.feedback_color_kind = "info"
                return None
            return SceneTransition(next_scene=runtime.launcher_scene())
        return None

    @property
    def _difficulty(self) -> Difficulty:
        return DIFFICULTIES[self.level_index]

    def _start_round(self, runtime: Runtime) -> None:
        difficulty = self._difficulty
        self.round_state = initial_round_state(difficulty)
        self.previous_target = None
        self.repeat_count = 0
        self.current_target = ""
        self.current_input = ""
        self.score_pops.clear()
        self.confetti.clear()
        self._advance_target(runtime)
        self.feedback_text = "Type the target."
        self.feedback_color_kind = "info"
        self.state = "playing"

    def _advance_target(self, runtime: Runtime) -> None:
        difficulty = self._difficulty
        if self.play_mode == "word":
            min_len, max_len = self._word_length_range(difficulty)
            self.current_target = choose_word_target(
                runtime.rng,
                min_len=min_len,
                max_len=max_len,
                previous_word=self.previous_target,
            )
        else:
            self.current_target = choose_next_target(
                runtime.rng, difficulty, self.previous_target, self.repeat_count
            )

        if self.current_target == self.previous_target:
            self.repeat_count += 1
        else:
            self.repeat_count = 1
        self.previous_target = self.current_target
        self.current_input = ""
        self.prompt_time_left = difficulty.prompt_timeout_sec
        self.target_anim_t = 0.25

    def _register_hit(self, runtime: Runtime) -> None:
        if self.round_state is None:
            return
        difficulty = self._difficulty
        points_before = self.round_state.score
        self.round_state = register_hit(self.round_state, difficulty)
        gained = self.round_state.score - points_before

        self.feedback_text = "Great typing!"
        self.feedback_color_kind = "success"
        self.score_pops.append(ScorePop(text=f"+{gained}", x=470, y=250, ttl=0.9))
        self._spawn_confetti(460, 260)
        if not is_round_over(self.round_state):
            self._advance_target(runtime)

    def _register_miss(self, runtime: Runtime) -> None:
        if self.round_state is None:
            return
        self.round_state = register_miss(self.round_state)
        self.feedback_text = "Oops, try the next one."
        self.feedback_color_kind = "error"
        self.miss_anim_t = 0.2
        self.current_input = ""
        if self.round_state.hearts > 0:
            self._advance_target(runtime)

    def _word_length_range(self, difficulty: Difficulty) -> tuple[int, int]:
        if difficulty.level_id == "easy":
            return (3, 4)
        if difficulty.level_id == "medium":
            return (4, 6)
        return (5, 8)

    def _finish_round(self) -> None:
        if self.round_state is None:
            return
        difficulty = self._difficulty
        self.best_scores[difficulty.level_id] = max(
            self.best_scores[difficulty.level_id], self.round_state.score
        )
        self.menu_index = 0
        self.state = "results"

    def _update_particles(self, dt: float) -> None:
        for particle in self.confetti:
            particle.ttl -= dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 260 * dt
        self.confetti = [particle for particle in self.confetti if particle.ttl > 0]

    def _spawn_confetti(self, x: float, y: float) -> None:
        colors = ((253, 143, 143), (255, 210, 117), (141, 204, 151), (123, 184, 255), (186, 164, 255))
        for index in range(16):
            angle = (math.pi * 2 * index) / 16
            speed = 90 + (index % 4) * 20
            self.confetti.append(
                ConfettiParticle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 120,
                    ttl=0.7,
                    color=colors[index % len(colors)],
                )
            )

    def _render_level_select(self, surface: pygame.Surface, runtime: Runtime) -> None:
        palette = runtime.config.palette
        width = runtime.config.window_width

        title_font = runtime.assets.font(52, bold=True)
        body_font = runtime.assets.font(24)
        card_title = runtime.assets.font(30, bold=True)
        card_text = runtime.assets.font(20)

        title = title_font.render("Key Sprout", True, (51, 77, 57))
        surface.blit(title, title.get_rect(center=(width // 2, 72)))

        subtitle = body_font.render("Grow your garden by typing the right keys.", True, palette.text)
        surface.blit(subtitle, subtitle.get_rect(center=(width // 2, 114)))

        mode_color = (82, 142, 95) if self.play_mode == "word" else (70, 102, 194)
        mode_label = "Word Mode" if self.play_mode == "word" else "Character Mode"
        mode_hint = body_font.render(f"Mode: {mode_label}", True, mode_color)
        surface.blit(mode_hint, mode_hint.get_rect(center=(width // 2, 148)))

        relaxed_color = (194, 105, 50) if self.relaxed_mode else (140, 140, 140)
        relaxed_label = "Relaxed: ON  (no timer)" if self.relaxed_mode else "Relaxed: OFF"
        relaxed_hint = body_font.render(relaxed_label, True, relaxed_color)
        surface.blit(relaxed_hint, relaxed_hint.get_rect(center=(width // 2, 174)))

        specs = (
            "a-z only",
            "A-Z plus a-z",
            "A-Z, a-z, 0-9",
        )
        for index, difficulty in enumerate(DIFFICULTIES):
            rect = pygame.Rect(96 + index * 255, 204, 220, 250)
            fill = (255, 249, 232) if index == self.level_index else palette.card
            pygame.draw.rect(surface, fill, rect, border_radius=24)
            pygame.draw.rect(surface, palette.card_border, rect, width=2, border_radius=24)

            title_surface = card_title.render(difficulty.title, True, (52, 85, 60))
            surface.blit(title_surface, (rect.left + 22, rect.top + 24))

            lines = (
                specs[index],
                f"Time/key: {difficulty.prompt_timeout_sec:.1f}s",
                f"Hearts: {difficulty.hearts}",
                f"Base score: {difficulty.base_points}",
            )
            for line_index, line in enumerate(lines):
                line_surface = card_text.render(line, True, palette.text)
                surface.blit(line_surface, (rect.left + 22, rect.top + 76 + line_index * 34))

        help_text = body_font.render(
            "Arrows: level   M/Tab: mode   R: relaxed   Enter: start   Esc: exit",
            True,
            palette.text,
        )
        surface.blit(help_text, help_text.get_rect(center=(width // 2, 500)))

        if self.play_mode == "word":
            word_count = len(ALPHA_WORD_CANDIDATES)
            prompt_line = f"Word Mode uses {word_count} candidate words from words_1000.txt"
        else:
            prompt_line = self.feedback_text

        prompt_text = body_font.render(prompt_line, True, (82, 142, 95))
        surface.blit(prompt_text, prompt_text.get_rect(center=(width // 2, 544)))

    def _render_play(self, surface: pygame.Surface, runtime: Runtime) -> None:
        if self.round_state is None:
            return

        palette = runtime.config.palette
        width = runtime.config.window_width

        title_font = runtime.assets.font(46, bold=True)
        stat_font = runtime.assets.font(24)
        target_font = runtime.assets.font(110 if self.play_mode == "word" else 128, bold=True)
        feedback_font = runtime.assets.font(28, bold=True)
        streak_font = runtime.assets.font(26)

        title = title_font.render("Key Sprout", True, (51, 77, 57))
        surface.blit(title, (48, 30))

        score_text = stat_font.render(f"Score: {self.round_state.score}", True, palette.text)
        hearts_text = stat_font.render(f"Hearts: {self.round_state.hearts}", True, palette.text)
        mode_text = stat_font.render(
            f"Mode: {'Word' if self.play_mode == 'word' else 'Character'}",
            True,
            palette.text,
        )
        streak_text = streak_font.render(f"Streak: {self.round_state.streak}", True, (82, 142, 95))
        best_text = streak_font.render(f"Best: {self.round_state.best_streak}", True, (82, 142, 95))
        surface.blit(score_text, (52, 92))
        surface.blit(hearts_text, (250, 92))
        surface.blit(mode_text, (52, 160))
        surface.blit(streak_text, (52, 126))
        surface.blit(best_text, (200, 126))

        remaining_sec = self.round_state.remaining_time_ms / 1000
        if self.relaxed_mode:
            timer_label = "Time: ∞"
        else:
            timer_label = f"Time: {remaining_sec:04.1f}s"
        timer_text = stat_font.render(timer_label, True, palette.text)
        surface.blit(timer_text, (740, 92))

        if not self.relaxed_mode:
            pygame.draw.rect(surface, (223, 239, 221), pygame.Rect(540, 132, 340, 16), border_radius=8)
            ratio = max(0.0, min(1.0, self.prompt_time_left / self._difficulty.prompt_timeout_sec))
            pygame.draw.rect(
                surface,
                (120, 194, 124),
                pygame.Rect(540, 132, int(340 * ratio), 16),
                border_radius=8,
            )

        target_scale = 1.0 + (math.sin((0.25 - self.target_anim_t) * 22) * 0.12 if self.target_anim_t > 0 else 0)
        target_surface = target_font.render(self.current_target, True, (70, 102, 194))
        target_surface = pygame.transform.smoothscale(
            target_surface,
            (
                max(1, int(target_surface.get_width() * target_scale)),
                max(1, int(target_surface.get_height() * target_scale)),
            ),
        )

        wiggle_x = int(math.sin(self.miss_anim_t * 90) * 14) if self.miss_anim_t > 0 else 0
        target_rect = target_surface.get_rect(center=(width // 2 + wiggle_x, 290))

        guide_rect = target_rect.inflate(180 if self.play_mode == "word" else 120, 90)
        pygame.draw.rect(surface, (255, 255, 255), guide_rect, border_radius=22)
        pygame.draw.rect(surface, (189, 209, 246), guide_rect, width=3, border_radius=22)
        top_line_y = guide_rect.top + 24
        mid_line_y = guide_rect.centery
        base_line_y = guide_rect.bottom - 22
        pygame.draw.line(surface, (219, 229, 245), (guide_rect.left + 16, top_line_y), (guide_rect.right - 16, top_line_y), 2)
        pygame.draw.line(surface, (206, 221, 242), (guide_rect.left + 16, mid_line_y), (guide_rect.right - 16, mid_line_y), 2)
        pygame.draw.line(surface, (180, 203, 238), (guide_rect.left + 16, base_line_y), (guide_rect.right - 16, base_line_y), 3)

        surface.blit(target_surface, target_rect)

        if self.play_mode == "char" and self.current_target.isalpha():
            case_label = "UPPERCASE" if self.current_target.isupper() else "lowercase"
            case_surface = streak_font.render(case_label, True, (94, 117, 172))
            surface.blit(case_surface, case_surface.get_rect(center=(guide_rect.centerx, guide_rect.bottom + 26)))

        if self.play_mode == "word":
            typed_font = runtime.assets.font(40, bold=True)
            typed_ok = self.current_target.startswith(self.current_input)
            typed_color = (82, 142, 95) if typed_ok else palette.error
            typed_display = self.current_input + "_" * max(0, len(self.current_target) - len(self.current_input))
            typed_surface = typed_font.render(typed_display, True, typed_color)
            surface.blit(typed_surface, typed_surface.get_rect(center=(guide_rect.centerx, guide_rect.bottom + 30)))

        for particle in self.confetti:
            alpha = int(255 * min(1.0, max(0.0, particle.ttl / 0.7)))
            particle_surface = pygame.Surface((8, 8), pygame.SRCALPHA)
            particle_surface.fill((*particle.color, alpha))
            surface.blit(particle_surface, (particle.x, particle.y))

        for pop in self.score_pops:
            alpha = int(255 * min(1.0, max(0.0, pop.ttl / 0.9)))
            pop_surface = feedback_font.render(pop.text, True, (92, 168, 109))
            pop_surface.set_alpha(alpha)
            surface.blit(pop_surface, (pop.x, pop.y))

        feedback_color = palette.text
        if self.feedback_color_kind == "success":
            feedback_color = (88, 164, 108)
        elif self.feedback_color_kind == "error":
            feedback_color = palette.error

        feedback = feedback_font.render(self.feedback_text, True, feedback_color)
        surface.blit(feedback, feedback.get_rect(center=(width // 2, 414)))

        if self.play_mode == "word":
            helper_line = "Type the whole word. Backspace fixes mistakes."
        else:
            helper_line = "Type the exact character you see. Other keys are ignored."

        helper = stat_font.render(helper_line, True, palette.text)
        surface.blit(helper, helper.get_rect(center=(width // 2, 560)))

    def _render_results(self, surface: pygame.Surface, runtime: Runtime) -> None:
        if self.round_state is None:
            return

        palette = runtime.config.palette
        width = runtime.config.window_width
        height = runtime.config.window_height

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 120))
        surface.blit(overlay, (0, 0))

        card = pygame.Rect(190, 130, width - 380, 360)
        pygame.draw.rect(surface, (255, 252, 241), card, border_radius=30)
        pygame.draw.rect(surface, palette.card_border, card, width=2, border_radius=30)

        title_font = runtime.assets.font(44, bold=True)
        body_font = runtime.assets.font(26)
        mini_font = runtime.assets.font(22)

        title = title_font.render("Garden Report", True, (51, 77, 57))
        surface.blit(title, title.get_rect(center=(card.centerx, card.top + 54)))

        stars = compute_star_rating(self.round_state.score)
        star_text = body_font.render("Stars: " + "★" * stars + "☆" * (3 - stars), True, (233, 170, 65))
        surface.blit(star_text, star_text.get_rect(center=(card.centerx, card.top + 104)))

        accuracy = accuracy_percent(self.round_state.correct_count, self.round_state.miss_count)
        rows = (
            f"Score: {self.round_state.score}",
            f"Best streak: {self.round_state.best_streak}",
            f"Accuracy: {accuracy}%",
            f"Best this level: {self.best_scores[self._difficulty.level_id]}",
        )
        for row_index, row in enumerate(rows):
            row_surface = body_font.render(row, True, palette.text)
            surface.blit(row_surface, row_surface.get_rect(center=(card.centerx, card.top + 156 + row_index * 42)))

        labels = ("Level Menu", "Launcher")
        for index, label in enumerate(labels):
            rect = pygame.Rect(card.left + 76 + index * 220, card.bottom - 84, 180, 52)
            fill = (230, 244, 224) if index == self.menu_index else palette.accent_soft
            pygame.draw.rect(surface, fill, rect, border_radius=20)
            pygame.draw.rect(surface, palette.card_border, rect, width=2, border_radius=20)
            label_surface = mini_font.render(label, True, palette.text)
            surface.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.fill((242, 250, 255))

        pygame.draw.circle(surface, (255, 233, 210), (120, 80), 130)
        pygame.draw.circle(surface, (214, 241, 255), (width - 120, 110), 150)
        pygame.draw.circle(surface, (219, 247, 221), (width - 170, height - 80), 170)
        pygame.draw.circle(surface, (236, 228, 255), (130, height - 90), 150)

        hill_points = [(0, height), (0, height - 120), (180, height - 150), (420, height - 108), (700, height - 165), (width, height - 130), (width, height)]
        pygame.draw.polygon(surface, (208, 238, 200), hill_points)

        for index in range(9):
            x = 70 + index * 95
            stem_top = height - 90 - ((index * 17) % 34)
            pygame.draw.line(surface, (93, 158, 98), (x, height - 40), (x, stem_top), 4)
            pygame.draw.circle(surface, (255, 182, 109), (x - 8, stem_top - 8), 11)
            pygame.draw.circle(surface, (254, 120, 152), (x + 8, stem_top - 8), 11)
            pygame.draw.circle(surface, (247, 229, 122), (x, stem_top + 1), 9)
