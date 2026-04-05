import random
import string
import unittest

from maogame.games.key_sprout.logic import (
    ALPHA_WORD_CANDIDATES,
    DIFFICULTIES,
    WORD_CANDIDATES,
    accuracy_percent,
    choose_next_target,
    choose_word_target,
    compute_star_rating,
    initial_round_state,
    is_round_over,
    register_hit,
    register_miss,
    score_for_hit,
)


class KeySproutLogicTests(unittest.TestCase):
    def test_word_candidate_file_loaded(self) -> None:
        self.assertEqual(len(WORD_CANDIDATES), 1000)
        self.assertGreaterEqual(len(ALPHA_WORD_CANDIDATES), 900)

    def test_difficulties_have_expected_charsets(self) -> None:
        easy, medium, hard = DIFFICULTIES

        self.assertEqual(easy.charset, string.ascii_lowercase)
        self.assertEqual(medium.charset, string.ascii_uppercase + string.ascii_lowercase)
        self.assertEqual(hard.charset, string.ascii_uppercase + string.ascii_lowercase + string.digits)

    def test_choose_target_uses_charset(self) -> None:
        rng = random.Random(7)
        difficulty = DIFFICULTIES[2]

        for _ in range(100):
            target = choose_next_target(rng, difficulty)
            self.assertIn(target, difficulty.charset)

    def test_choose_target_avoids_third_repeat(self) -> None:
        rng = random.Random(11)
        difficulty = DIFFICULTIES[0]

        next_target = choose_next_target(
            rng,
            difficulty,
            previous_target="m",
            repeat_count=2,
        )

        self.assertNotEqual(next_target, "m")

    def test_choose_word_target_honors_length_range(self) -> None:
        rng = random.Random(9)

        for _ in range(40):
            word = choose_word_target(rng, min_len=3, max_len=4)
            self.assertGreaterEqual(len(word), 3)
            self.assertLessEqual(len(word), 4)
            self.assertTrue(word.isalpha())

    def test_choose_word_target_avoids_previous_when_possible(self) -> None:
        rng = random.Random(11)
        word = choose_word_target(rng, min_len=4, max_len=4, previous_word="they")
        self.assertNotEqual(word, "they")

    def test_scoring_applies_bonus_and_cap(self) -> None:
        easy = DIFFICULTIES[0]
        hard = DIFFICULTIES[2]

        self.assertEqual(score_for_hit(0, easy), 10)
        self.assertEqual(score_for_hit(3, easy), 12)
        self.assertEqual(score_for_hit(20, easy), 20)

        self.assertEqual(score_for_hit(2, hard), 19)
        self.assertEqual(score_for_hit(100, hard), 35)

    def test_hit_and_miss_update_state(self) -> None:
        difficulty = DIFFICULTIES[1]
        state = initial_round_state(difficulty)

        state = register_hit(state, difficulty)
        self.assertEqual(state.streak, 1)
        self.assertEqual(state.best_streak, 1)
        self.assertEqual(state.correct_count, 1)
        self.assertEqual(state.hearts, difficulty.hearts)

        state = register_miss(state)
        self.assertEqual(state.streak, 0)
        self.assertEqual(state.best_streak, 1)
        self.assertEqual(state.miss_count, 1)
        self.assertEqual(state.hearts, difficulty.hearts - 1)

    def test_round_over_when_hearts_depleted(self) -> None:
        state = initial_round_state(DIFFICULTIES[0])
        for _ in range(DIFFICULTIES[0].hearts):
            state = register_miss(state)

        self.assertTrue(is_round_over(state))

    def test_star_rating_thresholds(self) -> None:
        self.assertEqual(compute_star_rating(0), 0)
        self.assertEqual(compute_star_rating(300), 1)
        self.assertEqual(compute_star_rating(600), 2)
        self.assertEqual(compute_star_rating(900), 3)

    def test_accuracy_handles_zero_and_rounding(self) -> None:
        self.assertEqual(accuracy_percent(0, 0), 0)
        self.assertEqual(accuracy_percent(3, 1), 75)
        self.assertEqual(accuracy_percent(2, 1), 67)

    def test_deterministic_sequence_for_same_seed(self) -> None:
        difficulty = DIFFICULTIES[1]

        seq_a = self._generate_sequence(random.Random(42), difficulty, 20)
        seq_b = self._generate_sequence(random.Random(42), difficulty, 20)

        self.assertEqual(seq_a, seq_b)

    def _generate_sequence(self, rng: random.Random, difficulty, count: int) -> list[str]:
        sequence: list[str] = []
        previous = None
        repeat_count = 0

        for _ in range(count):
            char = choose_next_target(rng, difficulty, previous, repeat_count)
            sequence.append(char)
            if char == previous:
                repeat_count += 1
            else:
                previous = char
                repeat_count = 1

        return sequence
