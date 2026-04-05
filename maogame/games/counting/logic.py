from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class CountingQuestion:
    count: int
    choices: tuple[int, int, int]
    answer_index: int


def build_question(rng: Random, *, min_count: int = 1, max_count: int = 9) -> CountingQuestion:
    count = rng.randint(min_count, max_count)
    distractors = {count}
    while len(distractors) < 3:
        distractors.add(rng.randint(min_count, max_count))
    choices = list(distractors)
    rng.shuffle(choices)
    return CountingQuestion(
        count=count,
        choices=(choices[0], choices[1], choices[2]),
        answer_index=choices.index(count),
    )

