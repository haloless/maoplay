from __future__ import annotations

from typing import Sequence

from maogame.core.quiz import QuizScene
from maogame.core.runtime import Runtime

from .logic import LetterQuestion, build_question


class LettersScene(QuizScene):
    def __init__(self) -> None:
        super().__init__(
            title="First Letter Fun",
            instruction="Choose the letter that starts the word.",
            rounds=5,
        )

    def build_prompt(self, runtime: Runtime) -> LetterQuestion:
        return build_question(runtime.rng)

    def prompt_lines(self, prompt: LetterQuestion) -> Sequence[str]:
        return ("Which letter makes this word?", prompt.display_word)

    def choice_labels(self, prompt: LetterQuestion) -> Sequence[str]:
        return prompt.choices

    def correct_choice_index(self, prompt: LetterQuestion) -> int:
        return prompt.answer_index

