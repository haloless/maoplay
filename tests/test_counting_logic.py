import random
import unittest

from maogame.games.counting.logic import build_question


class CountingLogicTests(unittest.TestCase):
    def test_counting_question_contains_correct_answer(self) -> None:
        question = build_question(random.Random(7))

        self.assertIn(question.count, question.choices)
        self.assertEqual(question.choices[question.answer_index], question.count)
        self.assertEqual(len(set(question.choices)), 3)
