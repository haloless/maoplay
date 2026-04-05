from __future__ import annotations

from dataclasses import dataclass
from random import Random


UPPERCASE_LETTERS = tuple("ABCDEFGHJKLMNPQRSTUVWXYZ")


@dataclass(frozen=True)
class MatchingQuestion:
    uppercase_letter: str
    choices: tuple[str, str, str]
    answer_index: int


def build_question(rng: Random) -> MatchingQuestion:
    uppercase_letter = rng.choice(UPPERCASE_LETTERS)
    correct_choice = uppercase_letter.lower()

    distractors = {correct_choice}
    lowercase_bank = tuple(letter.lower() for letter in UPPERCASE_LETTERS)
    while len(distractors) < 3:
        distractors.add(rng.choice(lowercase_bank))

    choices = list(distractors)
    rng.shuffle(choices)
    return MatchingQuestion(
        uppercase_letter=uppercase_letter,
        choices=(choices[0], choices[1], choices[2]),
        answer_index=choices.index(correct_choice),
    )
