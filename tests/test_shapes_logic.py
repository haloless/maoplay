import random
import unittest

from maogame.games.shapes.logic import SHAPES, build_question


class ShapesLogicTests(unittest.TestCase):
    def test_shape_question_contains_target_shape(self) -> None:
        question = build_question(random.Random(11))

        self.assertIn(question.target_shape, SHAPES)
        self.assertEqual(question.choices[question.answer_index], question.target_shape)
        self.assertEqual(len(set(question.choices)), 3)
