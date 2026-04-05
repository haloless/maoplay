from __future__ import annotations

from dataclasses import dataclass
from random import Random


WORD_BANK = (
    ("cat", "C"),
    ("dog", "D"),
    ("sun", "S"),
    ("bee", "B"),
    ("hat", "H"),
    ("fish", "F"),
)


@dataclass(frozen=True)
class LetterQuestion:
    word: str
    display_word: str
    choices: tuple[str, str, str]
    answer_index: int


def build_question(rng: Random) -> LetterQuestion:
    word, letter = rng.choice(WORD_BANK)
    distractors = {letter}
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    while len(distractors) < 3:
        distractors.add(rng.choice(alphabet))
    choices = list(distractors)
    rng.shuffle(choices)
    return LetterQuestion(
        word=word,
        display_word=f"_ {word[1:].upper()}",
        choices=(choices[0], choices[1], choices[2]),
        answer_index=choices.index(letter),
    )

