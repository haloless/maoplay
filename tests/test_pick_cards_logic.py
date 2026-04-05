import random
import unittest

from maogame.games.pick_cards.logic import DIFFICULTIES, build_deck, choose_target, remove_cards, selection_total


class PickCardsLogicTests(unittest.TestCase):
    def test_easy_deck_uses_number_cards_only(self) -> None:
        deck = build_deck(random.Random(4), DIFFICULTIES[0])

        self.assertEqual(len(deck), 6)
        self.assertTrue(all(card.rank not in {"J", "Q", "K"} for card in deck))

    def test_hard_target_is_always_playable(self) -> None:
        rng = random.Random(9)
        difficulty = DIFFICULTIES[2]
        deck = build_deck(rng, difficulty)

        target = choose_target(rng, deck, difficulty)

        self.assertIsNotNone(target)
        self.assertGreaterEqual(target, difficulty.min_target)
        self.assertLessEqual(target, difficulty.max_target)

    def test_remove_cards_updates_remaining_total(self) -> None:
        deck = build_deck(random.Random(3), DIFFICULTIES[1])
        selected_total_before = selection_total(deck, {0, 1})

        updated_deck = remove_cards(deck, {0, 1})

        self.assertEqual(len(updated_deck), len(deck) - 2)
        self.assertGreaterEqual(selected_total_before, 2)