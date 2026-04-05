from __future__ import annotations

from dataclasses import dataclass
from random import Random


SHAPES = ("circle", "square", "triangle", "star")


@dataclass(frozen=True)
class ShapeQuestion:
    target_shape: str
    choices: tuple[str, str, str]
    answer_index: int


def build_question(rng: Random) -> ShapeQuestion:
    target_shape = rng.choice(SHAPES)
    distractors = {target_shape}
    while len(distractors) < 3:
        distractors.add(rng.choice(SHAPES))
    choices = list(distractors)
    rng.shuffle(choices)
    return ShapeQuestion(
        target_shape=target_shape,
        choices=(choices[0], choices[1], choices[2]),
        answer_index=choices.index(target_shape),
    )

