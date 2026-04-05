import random
import unittest

from maogame.games.letters.logic import build_question


class LettersLogicTests(unittest.TestCase):
    def test_letter_question_contains_correct_letter(self) -> None:
        question = build_question(random.Random(3))

        correct_letter = question.word[0].upper()
        self.assertEqual(question.choices[question.answer_index], correct_letter)
        self.assertTrue(question.display_word.startswith("_ "))
        self.assertEqual(len(set(question.choices)), 3)
