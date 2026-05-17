"""Scene interaction tests for hanzi_pinyin_path result-screen keyboard flow."""

import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from maogame.core.scene import SceneTransition
from maogame.games.hanzi_pinyin_path.logic import CharacterEntry
from maogame.games.hanzi_pinyin_path.scene import HanziPinyinPathScene


class TestHanziResultKeyboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def _entry(self, hanzi: str = "绿", pinyin_raw: str = "lv", tone: int = 4) -> CharacterEntry:
        return CharacterEntry(hanzi=hanzi, pinyin_raw=pinyin_raw, tone=tone, grade_label="一年级上册")

    def _runtime(self):
        runtime = MagicMock()
        runtime.launcher_scene.return_value = object()
        return runtime

    def _key_event(self, key: int, unicode: str = "") -> pygame.event.Event:
        return pygame.event.Event(pygame.KEYDOWN, {"key": key, "unicode": unicode})

    def test_enter_default_starts_new_round(self) -> None:
        scene = HanziPinyinPathScene()
        runtime = self._runtime()
        scene._state = "result"
        scene._wrong_entries = [self._entry()] * 4
        scene._start_round = MagicMock()
        scene._start_wrong_round = MagicMock()

        transition = scene._handle_result_event(self._key_event(pygame.K_RETURN, "\r"), runtime)

        self.assertIsNone(transition)
        scene._start_round.assert_called_once_with()
        scene._start_wrong_round.assert_not_called()

    def test_keyboard_can_select_practice_wrong(self) -> None:
        scene = HanziPinyinPathScene()
        runtime = self._runtime()
        scene._state = "result"
        scene._wrong_entries = [self._entry()] * 4
        scene._start_round = MagicMock()
        scene._start_wrong_round = MagicMock()

        scene._handle_result_event(self._key_event(pygame.K_RIGHT), runtime)
        transition = scene._handle_result_event(self._key_event(pygame.K_RETURN, "\r"), runtime)

        self.assertIsNone(transition)
        scene._start_wrong_round.assert_called_once_with()
        scene._start_round.assert_not_called()

    def test_keyboard_can_select_return_menu(self) -> None:
        scene = HanziPinyinPathScene()
        runtime = self._runtime()
        sentinel_scene = object()
        runtime.launcher_scene.return_value = sentinel_scene
        scene._state = "result"
        scene._wrong_entries = []

        scene._handle_result_event(self._key_event(pygame.K_RIGHT), runtime)
        transition = scene._handle_result_event(self._key_event(pygame.K_RETURN, "\r"), runtime)

        self.assertIsInstance(transition, SceneTransition)
        self.assertIs(transition.next_scene, sentinel_scene)
