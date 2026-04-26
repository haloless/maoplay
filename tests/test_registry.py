import unittest

from maogame.core.registry import load_games


class RegistryTests(unittest.TestCase):
    def test_registered_games_have_expected_ids(self) -> None:
        games = load_games()

        self.assertEqual(
            [game.game_id for game in games],
            ["counting", "letters", "shapes", "matching", "pick-cards", "key-sprout", "hanzi-pinyin-path"],
        )
        self.assertTrue(all(callable(game.scene_factory) for game in games))
