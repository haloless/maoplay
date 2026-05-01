"""Unit tests for maogame.games.hanzi_pinyin_path.logic."""

import random
import unittest
from pathlib import Path

from maogame.games.hanzi_pinyin_path.logic import (
    ALL_GRADE_LABELS,
    CharacterEntry,
    RoundStats,
    _pick_distractors_pinyin,
    build_match_pairs,
    build_mcq_question,
    checkpoint_reward,
    compute_round_result,
    decide_feedback_tier,
    filter_entries,
    grades_for_years,
    judge_pinyin_answer,
    load_entries_from_markdown,
    normalize_pinyin_input,
    score_hit,
    summarize_highlights,
)

_DATA_FILE = Path(__file__).parent.parent / "doc" / "chinese_character_elementary_school.md"


class TestParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = load_entries_from_markdown(str(_DATA_FILE))

    def test_entries_not_empty(self) -> None:
        self.assertGreater(len(self.entries), 0)

    def test_all_six_grades_present(self) -> None:
        grade_labels_found = {e.grade_label for e in self.entries}
        year_names = ["一", "二", "三", "四", "五", "六"]
        for name in year_names:
            with self.subTest(name=name):
                self.assertTrue(
                    any(f"{name}年级" in label for label in grade_labels_found),
                    f"{name}年级 not found in parsed entries",
                )

    def test_each_entry_has_hanzi_and_pinyin(self) -> None:
        for entry in self.entries[:50]:
            with self.subTest(entry=entry):
                self.assertTrue(entry.hanzi, "Empty hanzi")
                self.assertTrue(entry.pinyin_raw, "Empty pinyin_raw")
                self.assertIn(entry.tone, range(5), "Tone out of range 0-4")

    def test_grade_labels_subset_of_known(self) -> None:
        found = {e.grade_label for e in self.entries}
        for label in found:
            self.assertIn(label, ALL_GRADE_LABELS, f"Unknown grade label: {label}")

    def test_first_grade_entries_detected(self) -> None:
        first = [e for e in self.entries if "一年级" in e.grade_label]
        self.assertGreater(len(first), 0)


class TestFiltering(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = load_entries_from_markdown(str(_DATA_FILE))

    def test_filter_single_grade(self) -> None:
        result = filter_entries(self.entries, ["一年级上册"])
        self.assertTrue(all(e.grade_label == "一年级上册" for e in result))

    def test_filter_multi_grade(self) -> None:
        grades = grades_for_years(1, 2)
        result = filter_entries(self.entries, grades)
        for e in result:
            self.assertIn(e.grade_label, grades)

    def test_filter_empty_range(self) -> None:
        result = filter_entries(self.entries, [])
        self.assertEqual(result, [])

    def test_grades_for_years(self) -> None:
        labels = grades_for_years(1, 3)
        self.assertEqual(len(labels), 6)
        self.assertIn("一年级上册", labels)
        self.assertIn("三年级下册", labels)


class TestMCQGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        entries = load_entries_from_markdown(str(_DATA_FILE))
        cls.pool = filter_entries(entries, grades_for_years(1, 3))
        cls.rng = random.Random(42)

    def test_hz2py_has_unique_correct_answer(self) -> None:
        for _ in range(20):
            q = build_mcq_question(self.rng, self.pool, "hz2py", "medium")
            self.assertIsNotNone(q)
            self.assertEqual(len(set(q.choices)), len(q.choices), "Duplicate choices")
            self.assertIn(q.answer_index, range(4))

    def test_py2hz_has_unique_correct_answer(self) -> None:
        for _ in range(20):
            q = build_mcq_question(self.rng, self.pool, "py2hz", "medium")
            self.assertIsNotNone(q)
            self.assertEqual(len(set(q.choices)), len(q.choices))

    def test_four_choices_always(self) -> None:
        for direction in ("hz2py", "py2hz"):
            q = build_mcq_question(self.rng, self.pool, direction, "easy")
            self.assertIsNotNone(q)
            self.assertEqual(len(q.choices), 4)

    def test_small_pool_returns_none(self) -> None:
        tiny_pool = self.pool[:2]
        q = build_mcq_question(self.rng, tiny_pool, "hz2py", "easy")
        self.assertIsNone(q)

    def test_correct_answer_in_choices(self) -> None:
        q = build_mcq_question(self.rng, self.pool, "hz2py", "hard")
        self.assertIsNotNone(q)
        self.assertIn(q.choices[q.answer_index], q.choices)


class TestMatchPairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        entries = load_entries_from_markdown(str(_DATA_FILE))
        cls.pool = filter_entries(entries, grades_for_years(1, 2))
        cls.rng = random.Random(0)

    def test_pair_count_easy(self) -> None:
        pairs = build_match_pairs(self.rng, self.pool, 4)
        self.assertEqual(len(pairs), 4)

    def test_pair_count_hard(self) -> None:
        pairs = build_match_pairs(self.rng, self.pool, 8)
        self.assertEqual(len(pairs), 8)

    def test_pairs_unique_hanzi(self) -> None:
        pairs = build_match_pairs(self.rng, self.pool, 6)
        hanzis = [p.left for p in pairs]
        self.assertEqual(len(set(hanzis)), len(hanzis))


class TestJudgePinyin(unittest.TestCase):
    def _entry(self, hanzi: str, pinyin_raw: str, tone: int) -> CharacterEntry:
        return CharacterEntry(hanzi=hanzi, pinyin_raw=pinyin_raw, tone=tone, grade_label="一年级上册")

    def test_correct_strict(self) -> None:
        e = self._entry("小", "xiao", 3)
        self.assertTrue(judge_pinyin_answer(e, "xiao", 3, strict_tone=True))

    def test_wrong_tone_strict(self) -> None:
        e = self._entry("小", "xiao", 3)
        self.assertFalse(judge_pinyin_answer(e, "xiao", 1, strict_tone=True))

    def test_wrong_tone_lenient(self) -> None:
        e = self._entry("小", "xiao", 3)
        self.assertTrue(judge_pinyin_answer(e, "xiao", 1, strict_tone=False))

    def test_wrong_base(self) -> None:
        e = self._entry("小", "xiao", 3)
        self.assertFalse(judge_pinyin_answer(e, "xia", 3, strict_tone=True))

    def test_neutral_tone(self) -> None:
        e = self._entry("的", "de", 0)
        self.assertTrue(judge_pinyin_answer(e, "de", 0, strict_tone=True))

    def test_case_insensitive(self) -> None:
        e = self._entry("小", "xiao", 3)
        self.assertTrue(judge_pinyin_answer(e, "XIAO", 3, strict_tone=True))

    def test_whitespace_stripped(self) -> None:
        e = self._entry("小", "xiao", 3)
        self.assertTrue(judge_pinyin_answer(e, "  xiao  ", 3, strict_tone=True))


class TestNormalizePinyin(unittest.TestCase):
    def test_lowercase(self) -> None:
        self.assertEqual(normalize_pinyin_input("XIAO"), "xiao")

    def test_strip_whitespace(self) -> None:
        self.assertEqual(normalize_pinyin_input("  hao  "), "hao")

    def test_v_preserved(self) -> None:
        self.assertEqual(normalize_pinyin_input("lv"), "lv")


class TestScoring(unittest.TestCase):
    def test_base_score_no_streak(self) -> None:
        self.assertEqual(score_hit(0), 10)

    def test_streak_bonus(self) -> None:
        self.assertEqual(score_hit(1), 12)
        self.assertEqual(score_hit(5), 20)

    def test_streak_bonus_capped(self) -> None:
        # Bonus capped at +20
        self.assertEqual(score_hit(10), 30)
        self.assertEqual(score_hit(100), 30)


class TestFunFeedbackHelpers(unittest.TestCase):
    def test_feedback_tier_wrong(self) -> None:
        tier = decide_feedback_tier(False, streak=10, elapsed_ms=100, difficulty="hard")
        self.assertEqual(tier, "wrong")

    def test_feedback_tier_combo_priority_over_fast(self) -> None:
        tier = decide_feedback_tier(True, streak=6, elapsed_ms=200, difficulty="medium")
        self.assertEqual(tier, "combo_correct")

    def test_feedback_tier_fast_correct(self) -> None:
        tier = decide_feedback_tier(True, streak=2, elapsed_ms=1800, difficulty="hard")
        self.assertEqual(tier, "fast_correct")

    def test_feedback_tier_normal_correct(self) -> None:
        tier = decide_feedback_tier(True, streak=1, elapsed_ms=8000, difficulty="easy")
        self.assertEqual(tier, "normal_correct")

    def test_checkpoint_reward_only_on_checkpoint_rounds(self) -> None:
        event = checkpoint_reward(round_index=2, accuracy_so_far=100.0, streak=10)
        self.assertFalse(event.triggered)
        self.assertEqual(event.stars, 0)
        self.assertIsNone(event.badge)

    def test_checkpoint_reward_stars_and_badge(self) -> None:
        event = checkpoint_reward(round_index=10, accuracy_so_far=96.0, streak=8)
        self.assertTrue(event.triggered)
        self.assertEqual(event.stars, 3)
        self.assertEqual(event.badge, "perfect_runner")

    def test_summarize_highlights_does_not_mutate_stats(self) -> None:
        stats = RoundStats()
        stats.record_correct()
        stats.record_correct()
        stats.record_wrong()
        before = (stats.correct_count, stats.wrong_count, stats.best_streak)

        summary = summarize_highlights(stats, fastest_ms=1450, total_stars=4)
        self.assertEqual(summary.fastest_ms, 1450)
        self.assertEqual(summary.total_stars, 4)
        self.assertEqual(summary.best_streak, 2)
        self.assertEqual(summary.accuracy_percent, stats.accuracy_percent)
        self.assertEqual(before, (stats.correct_count, stats.wrong_count, stats.best_streak))


class TestRoundStats(unittest.TestCase):
    def test_accuracy_no_answers(self) -> None:
        stats = RoundStats()
        self.assertEqual(stats.accuracy_percent, 0.0)

    def test_accuracy_all_correct(self) -> None:
        stats = RoundStats()
        for _ in range(5):
            stats.record_correct()
        self.assertEqual(stats.accuracy_percent, 100.0)

    def test_streak_resets_on_wrong(self) -> None:
        stats = RoundStats()
        stats.record_correct()
        stats.record_correct()
        self.assertEqual(stats.best_streak, 2)
        stats.record_wrong()
        stats.record_correct()
        self.assertEqual(stats.best_streak, 2)

    def test_compute_round_result(self) -> None:
        stats = RoundStats()
        stats.record_correct()
        stats.record_wrong()
        result = compute_round_result(stats, score=20)
        self.assertEqual(result.score, 20)
        self.assertEqual(result.correct_count, 1)
        self.assertEqual(result.wrong_count, 1)
        self.assertEqual(result.accuracy_percent, 50.0)


class TestReproducibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        entries = load_entries_from_markdown(str(_DATA_FILE))
        cls.pool = filter_entries(entries, grades_for_years(1, 6))

    def test_fixed_seed_deterministic_sequence(self) -> None:
        """Same seed must produce identical question prompts across two runs."""
        def run(seed: int) -> list[str]:
            rng = random.Random(seed)
            prompts = []
            for _ in range(10):
                q = build_mcq_question(rng, self.pool, "hz2py", "medium")
                self.assertIsNotNone(q)
                prompts.append(q.prompt)
            return prompts

        self.assertEqual(run(99), run(99))
        self.assertNotEqual(run(1), run(2))


class TestHardDistractors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        all_entries = load_entries_from_markdown(str(_DATA_FILE))
        cls.pool = filter_entries(all_entries, grades_for_years(1, 1))
        cls.all_entries = all_entries

    def test_hard_distractor_pool_can_include_cross_grade_entries(self) -> None:
        """With full entry set as distractor_pool, distractors may come from
        grades outside the play pool.  Over many trials at least one such
        cross-grade distractor must appear."""
        pool_pinyins = {e.pinyin_full for e in self.pool}
        rng = random.Random(42)
        found_cross_grade = False
        for _ in range(200):
            correct = rng.choice(self.pool)
            distractors = _pick_distractors_pinyin(correct, self.all_entries, rng, "hard", 3)
            if any(d not in pool_pinyins for d in distractors):
                found_cross_grade = True
                break
        self.assertTrue(
            found_cross_grade,
            "Expected at least one cross-grade distractor in 200 hard-mode trials",
        )


if __name__ == "__main__":
    unittest.main()
