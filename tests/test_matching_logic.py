import random
import unittest

from maogame.games.matching.logic import build_question


class MatchingLogicTests(unittest.TestCase):
    def test_matching_question_contains_lowercase_answer(self) -> None:
        question = build_question(random.Random(13))

        self.assertEqual(
            question.choices[question.answer_index],
            question.uppercase_letter.lower(),
        )
        self.assertEqual(len(set(question.choices)), 3)
