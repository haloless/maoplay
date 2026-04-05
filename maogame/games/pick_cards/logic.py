from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from random import Random
from typing import Iterable, Sequence


RANK_VALUES = {
    "A": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
}
NUMBER_RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10")
FACE_RANKS = ("J", "Q", "K")
SUITS = ("hearts", "diamonds", "clubs", "spades")


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str
    value: int


@dataclass(frozen=True)
class Difficulty:
    level_id: str
    title: str
    deck_size: int
    min_target: int
    max_target: int
    include_face_cards: bool = False


DIFFICULTIES = (
    Difficulty("easy", "Easy", deck_size=6, min_target=4, max_target=10),
    Difficulty("medium", "Medium", deck_size=8, min_target=6, max_target=15),
    Difficulty(
        "hard",
        "Hard",
        deck_size=10,
        min_target=8,
        max_target=20,
        include_face_cards=True,
    ),
)


def build_deck(rng: Random, difficulty: Difficulty) -> tuple[Card, ...]:
    ranks = NUMBER_RANKS + FACE_RANKS if difficulty.include_face_cards else NUMBER_RANKS
    deck = [Card(rank=rank, suit=suit, value=RANK_VALUES[rank]) for suit in SUITS for rank in ranks]
    return tuple(rng.sample(deck, difficulty.deck_size))


def playable_targets(cards: Sequence[Card], difficulty: Difficulty) -> tuple[int, ...]:
    targets = {
        total
        for combo in all_combinations(cards)
        for total in [sum(card.value for card in combo)]
        if difficulty.min_target <= total <= difficulty.max_target
    }
    return tuple(sorted(targets))


def choose_target(rng: Random, cards: Sequence[Card], difficulty: Difficulty) -> int | None:
    targets = playable_targets(cards, difficulty)
    if not targets:
        return None
    return rng.choice(targets)


def selection_total(cards: Sequence[Card], selected_indices: Iterable[int]) -> int:
    unique_indices = sorted(set(selected_indices))
    return sum(cards[index].value for index in unique_indices)


def is_valid_selection(cards: Sequence[Card], selected_indices: Iterable[int], target: int) -> bool:
    unique_indices = set(selected_indices)
    if len(unique_indices) < 2:
        return False
    return selection_total(cards, unique_indices) == target


def remove_cards(cards: Sequence[Card], selected_indices: Iterable[int]) -> tuple[Card, ...]:
    removed = set(selected_indices)
    return tuple(card for index, card in enumerate(cards) if index not in removed)


def all_combinations(cards: Sequence[Card]) -> tuple[tuple[Card, ...], ...]:
    combos = []
    for size in range(2, len(cards) + 1):
        combos.extend(combinations(cards, size))
    return tuple(combos)