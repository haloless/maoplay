from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
import string


@dataclass(frozen=True)
class Difficulty:
    level_id: str
    title: str
    charset: str
    prompt_timeout_sec: float
    round_duration_sec: float
    hearts: int
    base_points: int
    streak_bonus_start: int
    streak_bonus_step: int
    streak_bonus_cap: int


DIFFICULTIES = (
    Difficulty(
        level_id="easy",
        title="Easy",
        charset=string.ascii_lowercase,
        prompt_timeout_sec=3.5,
        round_duration_sec=90.0,
        hearts=5,
        base_points=10,
        streak_bonus_start=3,
        streak_bonus_step=2,
        streak_bonus_cap=10,
    ),
    Difficulty(
        level_id="medium",
        title="Medium",
        charset=string.ascii_uppercase + string.ascii_lowercase,
        prompt_timeout_sec=2.6,
        round_duration_sec=90.0,
        hearts=4,
        base_points=12,
        streak_bonus_start=3,
        streak_bonus_step=3,
        streak_bonus_cap=15,
    ),
    Difficulty(
        level_id="hard",
        title="Hard",
        charset=string.ascii_uppercase + string.ascii_lowercase + string.digits,
        prompt_timeout_sec=1.9,
        round_duration_sec=90.0,
        hearts=3,
        base_points=15,
        streak_bonus_start=2,
        streak_bonus_step=4,
        streak_bonus_cap=20,
    ),
)


WORD_LIST_PATH = Path(__file__).with_name("words_1000.txt")


def load_word_candidates() -> tuple[str, ...]:
    words: list[str] = []
    for line in WORD_LIST_PATH.read_text(encoding="utf-8").splitlines():
        word = line.strip().lower()
        if not word:
            continue
        words.append(word)
    return tuple(words)


WORD_CANDIDATES = load_word_candidates()
ALPHA_WORD_CANDIDATES = tuple(
    word for word in WORD_CANDIDATES if word.isalpha() and 2 <= len(word) <= 10
)


@dataclass(frozen=True)
class RoundState:
    score: int
    streak: int
    best_streak: int
    hearts: int
    remaining_time_ms: int
    correct_count: int
    miss_count: int


def initial_round_state(difficulty: Difficulty) -> RoundState:
    return RoundState(
        score=0,
        streak=0,
        best_streak=0,
        hearts=difficulty.hearts,
        remaining_time_ms=int(difficulty.round_duration_sec * 1000),
        correct_count=0,
        miss_count=0,
    )


def choose_next_target(
    rng: Random,
    difficulty: Difficulty,
    previous_target: str | None = None,
    repeat_count: int = 0,
) -> str:
    if not difficulty.charset:
        raise ValueError("Difficulty charset must not be empty.")

    choices = difficulty.charset
    if previous_target and repeat_count >= 2 and previous_target in choices and len(choices) > 1:
        choices = "".join(char for char in choices if char != previous_target)
    return rng.choice(choices)


def choose_word_target(
    rng: Random,
    *,
    min_len: int,
    max_len: int,
    previous_word: str | None = None,
) -> str:
    pool = [word for word in ALPHA_WORD_CANDIDATES if min_len <= len(word) <= max_len]
    if not pool:
        raise ValueError("No word candidates available for the requested range.")

    if previous_word and len(pool) > 1:
        non_repeating = [word for word in pool if word != previous_word]
        if non_repeating:
            pool = non_repeating
    return rng.choice(pool)


def score_for_hit(streak_before_hit: int, difficulty: Difficulty) -> int:
    new_streak = streak_before_hit + 1
    bonus_steps = max(0, new_streak - difficulty.streak_bonus_start)
    streak_bonus = min(difficulty.streak_bonus_cap, bonus_steps * difficulty.streak_bonus_step)
    return difficulty.base_points + streak_bonus


def register_hit(state: RoundState, difficulty: Difficulty) -> RoundState:
    points = score_for_hit(state.streak, difficulty)
    new_streak = state.streak + 1
    return RoundState(
        score=state.score + points,
        streak=new_streak,
        best_streak=max(state.best_streak, new_streak),
        hearts=state.hearts,
        remaining_time_ms=state.remaining_time_ms,
        correct_count=state.correct_count + 1,
        miss_count=state.miss_count,
    )


def register_miss(state: RoundState) -> RoundState:
    return RoundState(
        score=state.score,
        streak=0,
        best_streak=state.best_streak,
        hearts=max(0, state.hearts - 1),
        remaining_time_ms=state.remaining_time_ms,
        correct_count=state.correct_count,
        miss_count=state.miss_count + 1,
    )


def tick_timer(state: RoundState, dt_ms: int) -> RoundState:
    remaining = max(0, state.remaining_time_ms - max(0, dt_ms))
    return RoundState(
        score=state.score,
        streak=state.streak,
        best_streak=state.best_streak,
        hearts=state.hearts,
        remaining_time_ms=remaining,
        correct_count=state.correct_count,
        miss_count=state.miss_count,
    )


def is_round_over(state: RoundState) -> bool:
    return state.hearts <= 0 or state.remaining_time_ms <= 0


def compute_star_rating(score: int) -> int:
    if score >= 900:
        return 3
    if score >= 600:
        return 2
    if score >= 300:
        return 1
    return 0


def accuracy_percent(correct_count: int, miss_count: int) -> int:
    total = correct_count + miss_count
    if total <= 0:
        return 0
    return int(round((correct_count / total) * 100))
