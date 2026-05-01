"""Scene layer for 汉字拼音小径 (hanzi_pinyin_path).

State machine:
  setup-grade  → choose grade range
  setup-mode   → choose game mode
  setup-diff   → choose difficulty
  playing      → active MCQ round
  result       → round summary

Currently implements:
  Mode 1 – 汉字选拼音 (show hanzi, pick pinyin)
  Mode 2 – 拼音选汉字 (show pinyin, pick hanzi)
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Literal

import pygame

from maogame.core.assets import resolve_font_name
from maogame.core.input import is_back_key, is_confirm_key, move_selection
from maogame.core.runtime import Runtime
from maogame.core.scene import Scene, SceneTransition

from .logic import (
    ALL_GRADE_LABELS,
    CharacterEntry,
    MatchPair,
    MCQQuestion,
    QUESTION_TIME_LIMITS,
    RoundStats,
    build_match_pairs,
    build_mcq_question,
    compute_round_result,
    filter_entries,
    grades_for_years,
    judge_pinyin_answer,
    load_entries_from_markdown,
    normalize_pinyin_input,
    score_hit,
    score_speed_bonus,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATA_FILE = Path(__file__).parent.parent.parent.parent / "doc" / "chinese_character_elementary_school.md"

_GRADE_OPTIONS: list[tuple[str, list[str]]] = [
    ("一年级",    grades_for_years(1, 1)),
    ("二年级",    grades_for_years(2, 2)),
    ("三年级",    grades_for_years(3, 3)),
    ("四年级",    grades_for_years(4, 4)),
    ("五年级",    grades_for_years(5, 5)),
    ("六年级",    grades_for_years(6, 6)),
    ("一~三年级", grades_for_years(1, 3)),
    ("一~六年级", grades_for_years(1, 6)),
]

_MODE_OPTIONS: list[tuple[str, str, Literal["hz2py", "py2hz", "match", "input"]]] = [
    ("模式一", "看汉字选拼音", "hz2py"),
    ("模式二", "看拼音选汉字", "py2hz"),
    ("模式三", "连线配对",     "match"),
    ("模式四", "拼音输入",     "input"),
]

_MATCH_PAIR_COUNTS: dict[str, int] = {"easy": 4, "medium": 6, "hard": 8}

_DIFF_OPTIONS: list[tuple[str, str]] = [
    ("简单",  "easy"),
    ("中等",  "medium"),
    ("困难",  "hard"),
]

_TOTAL_ROUNDS = 10
_FEEDBACK_DURATION = 1.0   # seconds
_SCENE_FONT_NAME = resolve_font_name()


# ---------------------------------------------------------------------------
# Helper draw utilities
# ---------------------------------------------------------------------------

def _draw_text(
    surface: pygame.Surface,
    text: str,
    size: int,
    position: tuple[int, int],
    color: tuple[int, int, int],
    *,
    bold: bool = False,
    center: bool = False,
) -> pygame.Rect:
    if _SCENE_FONT_NAME is not None:
        font = pygame.font.SysFont(_SCENE_FONT_NAME, size, bold=bold)
    else:
        font = pygame.font.Font(None, size)
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(surf, rect)
    return rect


def _draw_card(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
    radius: int = 18,
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=radius)


# ---------------------------------------------------------------------------
# Main scene
# ---------------------------------------------------------------------------

class HanziPinyinPathScene(Scene):

    def __init__(self) -> None:
        import random as _random
        self._state: str = "setup-grade"
        self._entries: list[CharacterEntry] = []
        self._pool: list[CharacterEntry] = []
        self._rng = _random.Random()

        # Setup selections
        self._grade_index = 0
        self._mode_index = 0
        self._diff_index = 1  # default: medium
        self._cursor = 0      # generic menu cursor

        # Play state
        self._round_index = 0
        self._score = 0
        self._streak = 0
        self._stats = RoundStats()
        self._question: MCQQuestion | None = None
        self._selected = 0
        self._feedback_timer = 0.0
        self._feedback_correct = False
        self._q_start_time = 0.0
        self._time_limit = 12.0   # seconds per question; updated on round start
        self._time_left = 12.0

        # Wrong-answer tracking for "practice wrong" replay
        self._wrong_entries: list[CharacterEntry] = []

        # Match mode state (Mode 3)
        self._match_pairs: list[MatchPair] = []
        self._match_left_rects: list[pygame.Rect] = []
        self._match_right_rects: list[pygame.Rect] = []
        self._match_selected_left: int = -1   # index of highlighted left card (-1 = none)
        self._match_done: list[bool] = []     # which pairs are correctly matched
        self._match_wrong_pair: tuple[int, int] | None = None  # (left_idx, right_idx) for wrong flash
        self._match_wrong_timer: float = 0.0
        self._match_start_time: float = 0.0

        # Input mode state (Mode 4)
        self._input_entry: CharacterEntry | None = None
        self._input_text: str = ""
        self._input_tone: int = -1          # -1 = not yet chosen
        self._input_submitted: bool = False
        self._input_correct: bool = False
        self._input_feedback_timer: float = 0.0
        self._input_round_index: int = 0
        self._input_strict_tone: bool = True
        self._tone_btn_rects: list[pygame.Rect] = []

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def on_enter(self, runtime: Runtime) -> None:
        self._rng = runtime.rng
        if not self._entries:
            try:
                self._entries = load_entries_from_markdown(str(_DATA_FILE))
            except FileNotFoundError:
                self._entries = []
        self._state = "setup-grade"
        self._cursor = self._grade_index

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self.handle_mouse(event, runtime)
        if event.type != pygame.KEYDOWN:
            return None

        # In input mode, Backspace should edit text instead of navigating back.
        if self._state == "input" and event.key == pygame.K_BACKSPACE:
            return self._handle_input_key_event(event, runtime)

        if is_back_key(event):
            return self._handle_back(runtime)

        if self._state == "setup-grade":
            return self._handle_setup_event(event, len(_GRADE_OPTIONS), "_grade_index", "setup-mode")

        if self._state == "setup-mode":
            return self._handle_setup_event(event, len(_MODE_OPTIONS), "_mode_index", "setup-diff")

        if self._state == "setup-diff":
            return self._handle_setup_event(event, len(_DIFF_OPTIONS), "_diff_index", "playing")

        if self._state == "playing":
            return self._handle_play_event(event, runtime)

        if self._state == "match":
            return self._handle_match_key_event(event, runtime)

        if self._state == "input":
            return self._handle_input_key_event(event, runtime)

        if self._state == "result":
            return self._handle_result_event(event, runtime)

        return None

    def _handle_back(self, runtime: Runtime) -> SceneTransition | None:
        transitions = {
            "setup-grade": lambda: SceneTransition(next_scene=runtime.launcher_scene()),
            "setup-mode":  lambda: self._go("setup-grade"),
            "setup-diff":  lambda: self._go("setup-mode"),
            "playing":     lambda: self._go("setup-grade"),
            "match":       lambda: self._go("setup-grade"),
            "input":       lambda: self._go("setup-grade"),
            "result":      lambda: self._go("setup-grade"),
        }
        handler = transitions.get(self._state)
        return handler() if handler else None

    def _handle_setup_event(
        self,
        event: pygame.event.Event,
        option_count: int,
        index_attr: str,
        next_state: str,
    ) -> SceneTransition | None:
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            setattr(self, index_attr, move_selection(getattr(self, index_attr), -1, option_count))
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            setattr(self, index_attr, move_selection(getattr(self, index_attr), 1, option_count))
        elif is_confirm_key(event):
            if next_state == "playing":
                self._start_round()
            else:
                self._go(next_state)
        return None

    def _handle_play_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if self._feedback_timer > 0 or self._question is None:
            return None
        total = 4
        if event.key in (pygame.K_UP, pygame.K_LEFT):
            self._selected = move_selection(self._selected, -1, total)
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self._selected = move_selection(self._selected, 1, total)
        elif event.key in (pygame.K_1, pygame.K_KP1):
            self._selected = 0
        elif event.key in (pygame.K_2, pygame.K_KP2):
            self._selected = 1
        elif event.key in (pygame.K_3, pygame.K_KP3):
            self._selected = 2
        elif event.key in (pygame.K_4, pygame.K_KP4):
            self._selected = 3
        elif is_confirm_key(event):
            self._submit_answer()
        return None

    def _handle_match_key_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        # Esc is handled by _handle_back already; nothing else for keyboard in match mode
        return None

    def _handle_input_key_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if self._input_feedback_timer > 0:
            return None
        key = event.key
        # Tone shortcuts 1-4, 0 for neutral
        if key == pygame.K_0:
            self._input_tone = 0
            self._try_submit_input()
        elif key == pygame.K_1:
            self._input_tone = 1
            self._try_submit_input()
        elif key == pygame.K_2:
            self._input_tone = 2
            self._try_submit_input()
        elif key == pygame.K_3:
            self._input_tone = 3
            self._try_submit_input()
        elif key == pygame.K_4:
            self._input_tone = 4
            self._try_submit_input()
        elif key == pygame.K_BACKSPACE:
            self._input_text = self._input_text[:-1]
        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            if self._input_text and self._input_tone >= 0:
                self._try_submit_input()
        else:
            char = event.unicode.lower()
            if char.isalpha() or char == "v":
                self._input_text += char
        return None

    def _handle_result_event(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        if is_confirm_key(event):
            self._start_round()
        return None

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------

    def handle_mouse(
        self, event: pygame.event.Event, runtime: Runtime
    ) -> SceneTransition | None:
        """Called for MOUSEBUTTONDOWN events from update loop."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        pos = event.pos

        if self._state == "setup-grade":
            for i, rect in enumerate(self._option_rects):
                if rect.collidepoint(pos):
                    self._grade_index = i
                    self._go("setup-mode")
                    return None

        if self._state == "setup-mode":
            for i, rect in enumerate(self._option_rects):
                if rect.collidepoint(pos):
                    self._mode_index = i
                    self._go("setup-diff")
                    return None

        if self._state == "setup-diff":
            for i, rect in enumerate(self._option_rects):
                if rect.collidepoint(pos):
                    self._diff_index = i
                    self._start_round()
                    return None

        if self._state == "playing" and self._feedback_timer <= 0 and self._question:
            for i, rect in enumerate(self._choice_rects):
                if rect.collidepoint(pos):
                    self._selected = i
                    self._submit_answer()
                    return None

        if self._state == "match" and self._match_wrong_timer <= 0:
            self._handle_match_click(pos)
            return None

        if self._state == "input" and self._input_feedback_timer <= 0:
            # Tone buttons
            _TONE_LABELS = ["一声", "二声", "三声", "四声", "轻声", "清除"]
            for i, rect in enumerate(self._tone_btn_rects):
                if rect.collidepoint(pos):
                    if i == 5:  # 清除
                        self._input_text = ""
                        self._input_tone = -1
                    elif i == 4:  # 轻声
                        self._input_tone = 0
                        self._try_submit_input()
                    else:
                        self._input_tone = i + 1
                        self._try_submit_input()
                    return None

        if self._state == "result":
            for label, rect in self._result_buttons:
                if rect.collidepoint(pos):
                    if label == "再来一局":
                        self._start_round()
                    elif label == "练错题":
                        self._start_wrong_round()
                    else:
                        return SceneTransition(next_scene=runtime.launcher_scene())

        return None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float, runtime: Runtime) -> SceneTransition | None:
        if self._state == "match":
            return self._update_match(dt)

        if self._state == "input":
            return self._update_input(dt)

        if self._state != "playing":
            return None

        if self._feedback_timer > 0:
            self._feedback_timer = max(0.0, self._feedback_timer - dt)
            if self._feedback_timer == 0.0:
                if self._round_index >= _TOTAL_ROUNDS:
                    self._go("result")
                else:
                    self._next_question()
            return None

        # Countdown (only ticks when not in feedback phase)
        if self._question is not None:
            self._time_left = max(0.0, self._time_left - dt)
            if self._time_left == 0.0:
                # Time's up: count as wrong, advance
                self._stats.record_wrong()
                self._stats.record_time(int(self._time_limit * 1000))
                self._round_index += 1
                self._feedback_correct = False
                self._streak = 0
                self._feedback_timer = _FEEDBACK_DURATION

        return None

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface, runtime: Runtime) -> None:
        palette = runtime.config.palette
        surface.fill(palette.background)

        if self._state == "setup-grade":
            self._render_setup(surface, runtime, "选择年级范围", _GRADE_OPTIONS, self._grade_index)
        elif self._state == "setup-mode":
            self._render_setup_mode(surface, runtime)
        elif self._state == "setup-diff":
            self._render_setup(surface, runtime, "选择难度", _DIFF_OPTIONS, self._diff_index)
        elif self._state == "playing":
            self._render_play(surface, runtime)
        elif self._state == "match":
            self._render_match(surface, runtime)
        elif self._state == "input":
            self._render_input(surface, runtime)
        elif self._state == "result":
            self._render_result(surface, runtime)

    # ------------------------------------------------------------------
    # Setup screens
    # ------------------------------------------------------------------

    def _render_setup(
        self,
        surface: pygame.Surface,
        runtime: Runtime,
        title: str,
        options: list,
        selected: int,
    ) -> None:
        config = runtime.config
        palette = config.palette
        W, H = config.window_width, config.window_height

        _draw_text(surface, "汉字拼音小径", 38, (W // 2, 52), palette.accent, bold=True, center=True)
        _draw_text(surface, title, 28, (W // 2, 100), palette.text, center=True)

        col_count = min(len(options), 4)
        card_w = min(200, (W - 80) // col_count - 16)
        card_h = 72
        total_w = col_count * (card_w + 16) - 16
        start_x = (W - total_w) // 2
        start_y = 150

        self._option_rects = []
        rows = (len(options) + col_count - 1) // col_count
        for idx, item in enumerate(options):
            label = item[0] if isinstance(item, tuple) else item
            row = idx // col_count
            col = idx % col_count
            x = start_x + col * (card_w + 16)
            y = start_y + row * (card_h + 16)
            rect = pygame.Rect(x, y, card_w, card_h)
            self._option_rects.append(rect)
            fill = palette.card_selected if idx == selected else palette.card
            _draw_card(surface, rect, fill, palette.card_border)
            _draw_text(surface, label, 22, rect.center, palette.text, bold=(idx == selected), center=True)

        hint_y = start_y + rows * (card_h + 16) + 20
        _draw_text(surface, "↑↓ 选择  Enter 确认  Esc 返回", 18, (W // 2, hint_y), palette.accent, center=True)

    def _render_setup_mode(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        W, H = config.window_width, config.window_height

        _draw_text(surface, "汉字拼音小径", 38, (W // 2, 52), palette.accent, bold=True, center=True)
        _draw_text(surface, "选择游戏模式", 28, (W // 2, 100), palette.text, center=True)

        card_w, card_h = 380, 90
        gap = 24
        total_h = len(_MODE_OPTIONS) * (card_h + gap) - gap
        start_y = (H - total_h) // 2

        self._option_rects = []
        for idx, (mode_name, mode_desc, _) in enumerate(_MODE_OPTIONS):
            rect = pygame.Rect((W - card_w) // 2, start_y + idx * (card_h + gap), card_w, card_h)
            self._option_rects.append(rect)
            fill = palette.card_selected if idx == self._mode_index else palette.card
            _draw_card(surface, rect, fill, palette.card_border, radius=20)
            _draw_text(surface, mode_name, 24, (rect.centerx, rect.top + 26), palette.accent, bold=True, center=True)
            _draw_text(surface, mode_desc, 18, (rect.centerx, rect.top + 56), palette.text, center=True)

        _draw_text(surface, "↑↓ 选择  Enter 确认  Esc 返回", 18, (W // 2, H - 40), palette.accent, center=True)

    # ------------------------------------------------------------------
    # Play screen
    # ------------------------------------------------------------------

    def _render_play(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        W, H = config.window_width, config.window_height

        # HUD
        grade_label = _GRADE_OPTIONS[self._grade_index][0]
        mode_name = _MODE_OPTIONS[self._mode_index][0]
        diff_name = _DIFF_OPTIONS[self._diff_index][0]
        _draw_text(surface, f"第 {self._round_index}/{_TOTAL_ROUNDS} 题", 20, (20, 16), palette.text)
        _draw_text(surface, f"分数: {self._score}", 20, (W - 160, 16), palette.text)
        _draw_text(surface, f"连击: {self._streak}", 20, (W - 280, 16), palette.text)
        _draw_text(surface, f"{grade_label}  {mode_name}  {diff_name}", 16, (W // 2, 16), palette.accent, center=True)
        # Countdown timer
        time_color = palette.error if self._time_left <= 3.0 else palette.text
        _draw_text(surface, f"⏱ {self._time_left:.1f}s", 20, (W - 400, 16), time_color)

        if self._question is None:
            return

        q = self._question

        # Prompt card
        prompt_rect = pygame.Rect((W - 300) // 2, 80, 300, 120)
        _draw_card(surface, prompt_rect, palette.card, palette.accent, radius=24)

        if q.direction == "hz2py":
            # Show hanzi large
            if _SCENE_FONT_NAME is not None:
                font = pygame.font.SysFont(_SCENE_FONT_NAME, 72, bold=True)
            else:
                font = pygame.font.Font(None, 72)
            ts = font.render(q.prompt, True, palette.text)
            surface.blit(ts, ts.get_rect(center=prompt_rect.center))
        else:
            # Show pinyin
            _draw_text(surface, q.prompt, 32, prompt_rect.center, palette.text, bold=True, center=True)
            if q.direction == "py2hz":
                _draw_text(surface, "这是什么字？", 18, (W // 2, prompt_rect.bottom + 12), palette.accent, center=True)

        # Choices
        choice_w = (W - 120) // 2 - 10
        choice_h = 72
        gap = 14
        grid_x = [60, 60 + choice_w + 20]
        grid_y = [prompt_rect.bottom + 48, prompt_rect.bottom + 48 + choice_h + gap]

        self._choice_rects = []
        for idx in range(4):
            row = idx // 2
            col = idx % 2
            rect = pygame.Rect(grid_x[col], grid_y[row], choice_w, choice_h)
            self._choice_rects.append(rect)

            # Colors
            if self._feedback_timer > 0:
                if idx == q.answer_index:
                    fill = palette.success
                elif idx == self._selected:
                    fill = palette.error
                else:
                    fill = palette.card
            else:
                fill = palette.card_selected if idx == self._selected else palette.card

            _draw_card(surface, rect, fill, palette.card_border)
            label = q.choices[idx]
            font_size = 28 if q.direction == "hz2py" else 26
            _draw_text(surface, label, font_size, rect.center, palette.text, bold=True, center=True)
            # Key hint
            _draw_text(surface, str(idx + 1), 14, (rect.left + 10, rect.top + 6), palette.accent)

        # Feedback message
        if self._feedback_timer > 0:
            msg = "✓ 正确！" if self._feedback_correct else f"✗ 正确答案: {q.choices[q.answer_index]}"
            color = palette.success if self._feedback_correct else palette.error
            progress = max(0.0, min(1.0, self._feedback_timer / _FEEDBACK_DURATION))
            phase = 1.0 - progress
            x = W // 2
            y = H - 40
            size = 26

            if self._feedback_correct:
                # Gentle pop effect for correct answers.
                pop = abs(math.sin(phase * math.pi * 2.6))
                size = 26 + int(8 * pop * progress)
            else:
                # Short horizontal shake for wrong answers.
                shake = math.sin(phase * math.pi * 12.0)
                x += int(10 * shake * progress)

            _draw_text(surface, msg, size, (x, y), color, bold=True, center=True)

    # ------------------------------------------------------------------
    # Result screen
    # ------------------------------------------------------------------

    def _render_result(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        W, H = config.window_width, config.window_height

        result = compute_round_result(self._stats, self._score)

        _draw_text(surface, "汉字拼音小径", 36, (W // 2, 44), palette.accent, bold=True, center=True)
        _draw_text(surface, "本局结束！", 28, (W // 2, 90), palette.text, center=True)

        card = pygame.Rect((W - 480) // 2, 120, 480, 326)
        _draw_card(surface, card, palette.card, palette.card_border, radius=24)

        avg_ms = result.avg_answer_ms
        avg_display = f"{avg_ms / 1000:.1f} 秒" if avg_ms else "—"
        rows = [
            ("总分",       str(result.score)),
            ("答对",       f"{result.correct_count} 题"),
            ("答错",       f"{result.wrong_count} 题"),
            ("正确率",     f"{result.accuracy_percent}%"),
            ("最高连击",   str(result.best_streak)),
            ("平均用时",   avg_display),
        ]
        for i, (label, value) in enumerate(rows):
            row_y = card.top + 30 + i * 46
            _draw_text(surface, label, 20, (card.left + 60, row_y + 12), palette.text)
            _draw_text(surface, value, 22, (card.right - 60, row_y + 12), palette.accent, bold=True)

        # Buttons: show "练错题" only when there are wrong answers
        has_wrong = len(self._wrong_entries) >= 4
        btn_w, btn_h = 160, 52
        btn_gap = 16
        btn_labels = ["再来一局"]
        if has_wrong:
            btn_labels.append("练错题")
        btn_labels.append("返回菜单")
        total_btn_w = len(btn_labels) * (btn_w + btn_gap) - btn_gap
        btn_y = card.bottom + 36
        self._result_buttons = []
        for i, lbl in enumerate(btn_labels):
            bx = (W - total_btn_w) // 2 + i * (btn_w + btn_gap)
            btn_rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
            self._result_buttons.append((lbl, btn_rect))
            fill = palette.accent if i == 0 else palette.card
            text_color = palette.card if i == 0 else palette.text
            _draw_card(surface, btn_rect, fill, palette.card_border, radius=16)
            _draw_text(surface, lbl, 20, btn_rect.center, text_color, bold=True, center=True)

        _draw_text(surface, "Enter 再来一局  Esc 返回菜单", 16, (W // 2, btn_y + btn_h + 20), palette.accent, center=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _go(self, state: str) -> None:
        self._state = state

    def _start_wrong_round(self) -> None:
        """Start a replay round using only wrong-answered entries as the pool."""
        if not self._wrong_entries:
            return
        self._pool = list(self._wrong_entries)
        self._round_index = 0
        self._score = 0
        self._streak = 0
        self._stats = RoundStats()
        self._wrong_entries = []
        mode = _MODE_OPTIONS[self._mode_index][2]
        if mode == "input":
            self._input_round_index = 0
            self._go("input")
            self._next_input_question()
        elif mode == "match":
            self._go("match")
            self._start_match_round()
        else:
            self._go("playing")
            self._next_question()

    def _start_round(self) -> None:
        grade_labels = _GRADE_OPTIONS[self._grade_index][1]
        self._pool = filter_entries(self._entries, grade_labels)
        difficulty = _DIFF_OPTIONS[self._diff_index][1]
        self._time_limit = QUESTION_TIME_LIMITS.get(difficulty, 12.0)
        self._round_index = 0
        self._score = 0
        self._streak = 0
        self._stats = RoundStats()
        self._wrong_entries = []
        mode = _MODE_OPTIONS[self._mode_index][2]
        if mode == "match":
            self._go("match")
            self._start_match_round()
        elif mode == "input":
            self._input_strict_tone = _DIFF_OPTIONS[self._diff_index][1] != "easy"
            self._input_round_index = 0
            self._go("input")
            self._next_input_question()
        else:
            self._go("playing")
            self._next_question()

    def _start_match_round(self) -> None:
        difficulty = _DIFF_OPTIONS[self._diff_index][1]
        pair_count = _MATCH_PAIR_COUNTS.get(difficulty, 6)
        self._match_pairs = build_match_pairs(self._rng, self._pool, pair_count, difficulty)
        self._match_done = [False] * len(self._match_pairs)
        self._match_selected_left = -1
        self._match_wrong_pair = None
        self._match_wrong_timer = 0.0
        self._match_left_rects = []
        self._match_right_rects = []
        self._match_start_time = time.monotonic()

    def _next_question(self) -> None:
        direction = _MODE_OPTIONS[self._mode_index][2]
        difficulty = _DIFF_OPTIONS[self._diff_index][1]
        d_pool = self._entries if difficulty == "hard" else None
        self._question = build_mcq_question(
            self._rng,
            self._pool,
            direction,
            difficulty,
            distractor_pool=d_pool,
        )
        self._selected = 0
        self._time_left = self._time_limit
        self._q_start_time = time.monotonic()

    def _submit_answer(self) -> None:
        q = self._question
        if q is None:
            return
        elapsed_ms = int((time.monotonic() - self._q_start_time) * 1000)
        self._stats.record_time(elapsed_ms)
        self._round_index += 1
        if self._selected == q.answer_index:
            self._feedback_correct = True
            self._stats.record_correct()
            self._score += score_hit(self._streak)
            self._score += score_speed_bonus(elapsed_ms, self._time_limit)
            self._streak += 1
        else:
            self._feedback_correct = False
            self._stats.record_wrong()
            self._streak = 0
            if q.source_entry is not None:
                self._wrong_entries.append(q.source_entry)
        self._feedback_timer = _FEEDBACK_DURATION

    # ------------------------------------------------------------------
    # Match mode helpers
    # ------------------------------------------------------------------

    def _handle_match_click(self, pos: tuple[int, int]) -> None:
        """Process a mouse click during match mode."""
        # Click on a left (hanzi) card
        for i, rect in enumerate(self._match_left_rects):
            if rect.collidepoint(pos) and not self._match_done[i]:
                self._match_selected_left = i
                return
        # Click on a right (pinyin) card
        if self._match_selected_left >= 0:
            for j, rect in enumerate(self._match_right_rects):
                if rect.collidepoint(pos) and not self._match_done[j]:
                    left_idx = self._match_selected_left
                    # Check correctness: pairs are ordered so index must match
                    if left_idx == j:
                        self._match_done[left_idx] = True
                        self._stats.record_correct()
                        self._score += score_hit(self._streak)
                        self._streak += 1
                    else:
                        self._match_wrong_pair = (left_idx, j)
                        self._match_wrong_timer = 0.5
                        self._stats.record_wrong()
                        self._streak = 0
                    self._match_selected_left = -1
                    return

    def _update_match(self, dt: float) -> SceneTransition | None:
        if self._match_wrong_timer > 0:
            self._match_wrong_timer = max(0.0, self._match_wrong_timer - dt)
            if self._match_wrong_timer == 0.0:
                self._match_wrong_pair = None
        # All matched → go to result
        if self._match_pairs and all(self._match_done):
            elapsed_ms = int((time.monotonic() - self._match_start_time) * 1000)
            self._stats.record_time(elapsed_ms)
            self._go("result")
        return None

    def _render_match(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        W, H = config.window_width, config.window_height

        _draw_text(surface, "连线配对", 36, (W // 2, 28), palette.accent, bold=True, center=True)
        grade_label = _GRADE_OPTIONS[self._grade_index][0]
        diff_name = _DIFF_OPTIONS[self._diff_index][0]
        _draw_text(surface, f"{grade_label}  {diff_name}", 16, (W // 2, 62), palette.accent, center=True)
        _draw_text(surface, f"分数: {self._score}  连击: {self._streak}", 18, (W // 2, 82), palette.text, center=True)

        pairs = self._match_pairs
        n = len(pairs)
        if n == 0:
            return

        card_w, card_h = 140, 56
        gap = 12
        total_h = n * (card_h + gap) - gap
        start_y = max(100, (H - total_h) // 2)
        left_x = W // 2 - 180 - card_w
        right_x = W // 2 + 180

        self._match_left_rects = []
        self._match_right_rects = []

        for i, pair in enumerate(pairs):
            y = start_y + i * (card_h + gap)
            l_rect = pygame.Rect(left_x, y, card_w, card_h)
            r_rect = pygame.Rect(right_x, y, card_w, card_h)
            self._match_left_rects.append(l_rect)
            self._match_right_rects.append(r_rect)

            done = self._match_done[i]
            wrong_l = self._match_wrong_pair and self._match_wrong_pair[0] == i
            wrong_r = self._match_wrong_pair and self._match_wrong_pair[1] == i
            selected = self._match_selected_left == i

            if done:
                l_fill = r_fill = palette.success
            else:
                l_fill = palette.card_selected if selected else palette.card
                l_fill = palette.error if wrong_l else l_fill
                r_fill = palette.error if wrong_r else palette.card

            _draw_card(surface, l_rect, l_fill, palette.card_border)
            _draw_text(surface, pair.left, 28, l_rect.center, palette.text, bold=True, center=True)
            _draw_card(surface, r_rect, r_fill, palette.card_border)
            _draw_text(surface, pair.right, 22, r_rect.center, palette.text, bold=True, center=True)

        done_count = sum(self._match_done)
        _draw_text(surface, f"{done_count}/{n} 配对完成", 18, (W // 2, H - 30), palette.accent, center=True)
        _draw_text(surface, "点击左侧汉字，再点击右侧拼音完成配对  Esc 返回", 15,
                   (W // 2, H - 14), palette.accent, center=True)

    # ------------------------------------------------------------------
    # Input mode helpers (Mode 4)
    # ------------------------------------------------------------------

    def _next_input_question(self) -> None:
        if not self._pool:
            return
        self._input_entry = self._rng.choice(self._pool)
        self._input_text = ""
        self._input_tone = -1
        self._input_submitted = False
        self._time_left = self._time_limit
        self._q_start_time = time.monotonic()

    def _try_submit_input(self) -> None:
        entry = self._input_entry
        if entry is None or not self._input_text:
            return
        if self._input_tone < 0:
            return
        elapsed_ms = int((time.monotonic() - self._q_start_time) * 1000)
        self._stats.record_time(elapsed_ms)
        self._input_round_index += 1
        correct = judge_pinyin_answer(
            entry,
            normalize_pinyin_input(self._input_text),
            self._input_tone,
            strict_tone=self._input_strict_tone,
        )
        self._input_correct = correct
        self._input_submitted = True
        if correct:
            self._stats.record_correct()
            self._score += score_hit(self._streak)
            self._score += score_speed_bonus(elapsed_ms, self._time_limit)
            self._streak += 1
        else:
            self._stats.record_wrong()
            self._streak = 0
            self._wrong_entries.append(entry)
        self._input_feedback_timer = _FEEDBACK_DURATION

    def _update_input(self, dt: float) -> SceneTransition | None:
        if self._input_feedback_timer > 0:
            self._input_feedback_timer = max(0.0, self._input_feedback_timer - dt)
            if self._input_feedback_timer == 0.0:
                if self._input_round_index >= _TOTAL_ROUNDS:
                    self._go("result")
                else:
                    self._next_input_question()
            return None
        # Countdown
        if self._input_entry is not None and not self._input_submitted:
            self._time_left = max(0.0, self._time_left - dt)
            if self._time_left == 0.0:
                self._stats.record_wrong()
                self._stats.record_time(int(self._time_limit * 1000))
                self._input_round_index += 1
                self._input_correct = False
                self._input_submitted = True
                self._streak = 0
                self._input_feedback_timer = _FEEDBACK_DURATION
        return None

    def _render_input(self, surface: pygame.Surface, runtime: Runtime) -> None:
        config = runtime.config
        palette = config.palette
        W, H = config.window_width, config.window_height

        # HUD
        grade_label = _GRADE_OPTIONS[self._grade_index][0]
        diff_name = _DIFF_OPTIONS[self._diff_index][0]
        mode_name = _MODE_OPTIONS[self._mode_index][0]
        _draw_text(surface, f"\u7b2c {self._input_round_index}/{_TOTAL_ROUNDS} \u9898", 20, (20, 16), palette.text)
        _draw_text(surface, f"\u5206\u6570: {self._score}", 20, (W - 160, 16), palette.text)
        _draw_text(surface, f"\u8fde\u51fb: {self._streak}", 20, (W - 280, 16), palette.text)
        _draw_text(surface, f"{grade_label}  {mode_name}  {diff_name}", 16, (W // 2, 16), palette.accent, center=True)
        time_color = palette.error if self._time_left <= 3.0 else palette.text
        _draw_text(surface, f"\u23f1 {self._time_left:.1f}s", 20, (W - 400, 16), time_color)

        entry = self._input_entry
        if entry is None:
            return

        # Prompt card
        prompt_rect = pygame.Rect((W - 220) // 2, 70, 220, 110)
        _draw_card(surface, prompt_rect, palette.card, palette.accent, radius=24)
        if _SCENE_FONT_NAME is not None:
            font = pygame.font.SysFont(_SCENE_FONT_NAME, 72, bold=True)
        else:
            font = pygame.font.Font(None, 72)
        ts = font.render(entry.hanzi, True, palette.text)
        surface.blit(ts, ts.get_rect(center=prompt_rect.center))

        # Input display box
        box_rect = pygame.Rect((W - 320) // 2, 200, 320, 56)
        _draw_card(surface, box_rect, palette.card, palette.accent)
        display_text = self._input_text or "\u8bf7\u8f93\u5165\u62fc\u97f3..."
        text_color = palette.text if self._input_text else palette.accent
        _draw_text(surface, display_text, 26, box_rect.center, text_color, center=True)

        # Feedback banner
        if self._input_submitted:
            if self._input_correct:
                fb_msg = f"\u2713 \u6b63\u786e\uff01{entry.pinyin_display}"
                fb_color = palette.success
            else:
                fb_msg = f"\u2717 \u6b63\u786e\u62fc\u97f3: {entry.pinyin_display}"
                fb_color = palette.error
            _draw_text(surface, fb_msg, 24, (W // 2, 268), fb_color, bold=True, center=True)

        # Tone buttons
        tone_labels = ["\u4e00\u58f0", "\u4e8c\u58f0", "\u4e09\u58f0", "\u56db\u58f0", "\u8f7b\u58f0", "\u6e05\u9664"]
        btn_w, btn_h = 76, 48
        gap = 10
        total_w = len(tone_labels) * (btn_w + gap) - gap
        start_x = (W - total_w) // 2
        btn_y = 300

        self._tone_btn_rects = []
        for i, lbl in enumerate(tone_labels):
            rect = pygame.Rect(start_x + i * (btn_w + gap), btn_y, btn_w, btn_h)
            self._tone_btn_rects.append(rect)
            is_selected = (i < 4 and self._input_tone == i + 1) or (i == 4 and self._input_tone == 0)
            fill = palette.card_selected if is_selected else palette.card
            fill = palette.error if i == 5 else fill
            _draw_card(surface, rect, fill, palette.card_border, radius=12)
            _draw_text(surface, lbl, 18, rect.center, palette.text, bold=is_selected, center=True)
            # Key hint
            hint = str(i + 1) if i < 4 else ("0" if i == 4 else "")
            if hint:
                _draw_text(surface, hint, 12, (rect.left + 6, rect.top + 4), palette.accent)

        strict_label = "\u58f0\u8c03\u4e25\u683c: \u5f00" if self._input_strict_tone else "\u58f0\u8c03\u4e25\u683c: \u5173"
        _draw_text(surface, strict_label, 14, (W // 2, btn_y + btn_h + 14), palette.accent, center=True)
        _draw_text(surface, "\u952e\u76d8\u8f93\u5165\u5b57\u6bcd + \u9f20\u6807\u70b9\u51fb\u58f0\u8c03\u6309\u949f\u63d0\u4ea4  Esc \u8fd4\u56de", 14,
                   (W // 2, H - 16), palette.accent, center=True)
