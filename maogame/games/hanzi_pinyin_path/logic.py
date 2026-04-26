"""Logic layer for 汉字拼音小径 (hanzi_pinyin_path).

Covers:
- Parsing the elementary-school character markdown file.
- Filtering by grade range.
- Building MCQ questions (Mode 1 & 2) and match-pair sets (Mode 3).
- Judging pinyin input answers (Mode 4).
- Scoring and round-result computation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Literal, Sequence


# ---------------------------------------------------------------------------
# Tone-mark tables
# ---------------------------------------------------------------------------

# Maps each tone-marked vowel to (base_vowel, tone_number).
_TONE_MAP: dict[str, tuple[str, int]] = {
    # First tone
    "ā": ("a", 1), "ē": ("e", 1), "ī": ("i", 1), "ō": ("o", 1),
    "ū": ("u", 1), "ǖ": ("v", 1),
    # Second tone
    "á": ("a", 2), "é": ("e", 2), "í": ("i", 2), "ó": ("o", 2),
    "ú": ("u", 2), "ǘ": ("v", 2),
    # Third tone
    "ǎ": ("a", 3), "ě": ("e", 3), "ǐ": ("i", 3), "ǒ": ("o", 3),
    "ǔ": ("u", 3), "ǚ": ("v", 3),
    # Fourth tone
    "à": ("a", 4), "ě": ("e", 3),  # ě already listed; keep table clean
    "à": ("a", 4), "è": ("e", 4), "ì": ("i", 4), "ò": ("o", 4),
    "ù": ("u", 4), "ǜ": ("v", 4),
    # ü without tone (appears sometimes)
    "ü": ("v", 0),
}

# Rebuild cleanly to avoid accidental duplicates
_TONE_MAP = {}
_TONE_ENTRIES: list[tuple[str, str, int]] = [
    ("ā", "a", 1), ("ē", "e", 1), ("ī", "i", 1), ("ō", "o", 1), ("ū", "u", 1), ("ǖ", "v", 1),
    ("á", "a", 2), ("é", "e", 2), ("í", "i", 2), ("ó", "o", 2), ("ú", "u", 2), ("ǘ", "v", 2),
    ("ǎ", "a", 3), ("ě", "e", 3), ("ǐ", "i", 3), ("ǒ", "o", 3), ("ǔ", "u", 3), ("ǚ", "v", 3),
    ("à", "a", 4), ("è", "e", 4), ("ì", "i", 4), ("ò", "o", 4), ("ù", "u", 4), ("ǜ", "v", 4),
    ("ü", "v", 0),
]
for _ch, _base, _tone in _TONE_ENTRIES:
    _TONE_MAP[_ch] = (_base, _tone)


def _split_pinyin(pinyin_with_tone: str) -> tuple[str, int]:
    """Return (base_pinyin, tone) from a unicode pinyin string like 'xiǎo'.

    Tone 0 means neutral/light tone.
    """
    base_chars: list[str] = []
    detected_tone = 0
    for ch in pinyin_with_tone.lower():
        if ch in _TONE_MAP:
            base_ch, t = _TONE_MAP[ch]
            base_chars.append(base_ch)
            if t != 0:
                detected_tone = t
        else:
            base_chars.append(ch)
    return "".join(base_chars), detected_tone


# Reverse table: base vowel → (tone1, tone2, tone3, tone4)
_BASE_TO_TONED: dict[str, tuple[str, str, str, str]] = {
    "a": ("ā", "á", "ǎ", "à"),
    "e": ("ē", "é", "ě", "è"),
    "i": ("ī", "í", "ǐ", "ì"),
    "o": ("ō", "ó", "ǒ", "ò"),
    "u": ("ū", "ú", "ǔ", "ù"),
    "v": ("ǖ", "ǘ", "ǚ", "ǜ"),  # v represents ü
}
_VOWELS = frozenset("aeiouv")


def apply_tone_mark(base: str, tone: int) -> str:
    """Convert a base pinyin string and tone number to proper Unicode.

    E.g. apply_tone_mark('xiao', 3) → 'xiǎo'
         apply_tone_mark('lv',   4) → 'lǜ'
         apply_tone_mark('de',   0) → 'de'
    """
    if tone == 0:
        return base.replace("v", "ü")

    # Rule 1: a or e always takes the mark
    for vowel in ("a", "e"):
        idx = base.find(vowel)
        if idx != -1:
            toned = _BASE_TO_TONED[vowel][tone - 1]
            result = base[:idx] + toned + base[idx + 1:]
            return result.replace("v", "ü")

    # Rule 2: 'ou' → o takes the mark
    idx = base.find("ou")
    if idx != -1:
        toned = _BASE_TO_TONED["o"][tone - 1]
        result = base[:idx] + toned + base[idx + 1:]
        return result.replace("v", "ü")

    # Rule 3: last vowel takes the mark
    last_idx = -1
    for i, ch in enumerate(base):
        if ch in _VOWELS:
            last_idx = i
    if last_idx == -1:
        return base  # no vowel found (shouldn't happen in valid pinyin)
    ch = base[last_idx]
    toned = _BASE_TO_TONED[ch][tone - 1]
    result = base[:last_idx] + toned + base[last_idx + 1:]
    return result.replace("v", "ü")


def _pinyin_full_to_display(s: str) -> str:
    """Convert an internal 'xiao3' style pinyin string to Unicode 'xiǎo'."""
    if s and s[-1].isdigit():
        return apply_tone_mark(s[:-1], int(s[-1]))
    return apply_tone_mark(s, 0)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# All supported grade labels (canonical order)
ALL_GRADE_LABELS: tuple[str, ...] = (
    "一年级上册", "一年级下册",
    "二年级上册", "二年级下册",
    "三年级上册", "三年级下册",
    "四年级上册", "四年级下册",
    "五年级上册", "五年级下册",
    "六年级上册", "六年级下册",
)


@dataclass(frozen=True)
class CharacterEntry:
    hanzi: str
    pinyin_raw: str     # base form without tone marks, e.g. "xiao"
    tone: int           # 1-4; 0 = neutral/light tone
    grade_label: str    # e.g. "三年级下册"

    @property
    def pinyin_display(self) -> str:
        """Return a human-readable pinyin with proper Unicode tone marks."""
        return apply_tone_mark(self.pinyin_raw, self.tone)

    @property
    def pinyin_full(self) -> str:
        """Canonical 'base+tone' string used for comparison: e.g. 'xiao3'."""
        return f"{self.pinyin_raw}{self.tone}" if self.tone else self.pinyin_raw


@dataclass(frozen=True)
class MCQQuestion:
    """A multiple-choice question."""
    prompt: str                   # The thing shown to the player
    choices: tuple[str, ...]      # 4 answer strings
    answer_index: int
    direction: Literal["hz2py", "py2hz"]  # hz2py: show hanzi, pick pinyin; reverse


@dataclass(frozen=True)
class MatchPair:
    left: str   # hanzi
    right: str  # pinyin display


@dataclass
class RoundStats:
    correct_count: int = 0
    wrong_count: int = 0
    best_streak: int = 0
    total_answer_ms: int = 0
    answer_count: int = 0
    _current_streak: int = field(default=0, repr=False)

    @property
    def accuracy_percent(self) -> float:
        total = self.correct_count + self.wrong_count
        return round(self.correct_count / total * 100, 1) if total else 0.0

    @property
    def avg_answer_ms(self) -> float:
        return round(self.total_answer_ms / self.answer_count, 1) if self.answer_count else 0.0

    def record_correct(self) -> None:
        self.correct_count += 1
        self._current_streak += 1
        if self._current_streak > self.best_streak:
            self.best_streak = self._current_streak

    def record_wrong(self) -> None:
        self.wrong_count += 1
        self._current_streak = 0

    def record_time(self, ms: int) -> None:
        self.total_answer_ms += ms
        self.answer_count += 1


@dataclass(frozen=True)
class RoundResult:
    score: int
    correct_count: int
    wrong_count: int
    accuracy_percent: float
    best_streak: int
    avg_answer_ms: float


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Matches a grade section header like "## 一年级上册生字：100个"
_SECTION_RE = re.compile(
    r"##\s*([一二三四五六]年级[上下]册)"
)

# Matches one hanzi+pinyin token: 汉(pīnyīn)
_TOKEN_RE = re.compile(r"([\u4e00-\u9fff])\(([a-zA-Züāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ·]+)\)")


def load_entries_from_markdown(path: str) -> list[CharacterEntry]:
    """Parse the elementary-school character markdown file.

    Returns a list of CharacterEntry objects ordered as they appear in the file.
    """
    entries: list[CharacterEntry] = []
    current_grade: str = ""
    text = Path(path).read_text(encoding="utf-8")

    for line in text.splitlines():
        m = _SECTION_RE.search(line)
        if m:
            current_grade = m.group(1)
            continue
        if not current_grade:
            continue
        for token_match in _TOKEN_RE.finditer(line):
            hanzi = token_match.group(1)
            raw_pinyin = token_match.group(2)
            base, tone = _split_pinyin(raw_pinyin)
            entries.append(CharacterEntry(
                hanzi=hanzi,
                pinyin_raw=base,
                tone=tone,
                grade_label=current_grade,
            ))
    return entries


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_entries(
    entries: list[CharacterEntry],
    grade_range: Sequence[str],
) -> list[CharacterEntry]:
    """Return entries whose grade_label is in grade_range."""
    grade_set = set(grade_range)
    return [e for e in entries if e.grade_label in grade_set]


def grades_for_years(start_year: int, end_year: int) -> list[str]:
    """Return all grade labels for school years start_year..end_year (inclusive).

    E.g. grades_for_years(1, 2) → ['一年级上册', '一年级下册', '二年级上册', '二年级下册']
    """
    year_names = ["一", "二", "三", "四", "五", "六"]
    result = []
    for year in range(start_year, end_year + 1):
        label_base = f"{year_names[year - 1]}年级"
        result.append(f"{label_base}上册")
        result.append(f"{label_base}下册")
    return result


# ---------------------------------------------------------------------------
# Distractor generation helpers
# ---------------------------------------------------------------------------

def _same_initial(a: str, b: str) -> bool:
    """True if two base pinyins share the same initial consonant(s)."""
    initials = ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l",
                "g", "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w")
    def get_initial(py: str) -> str:
        for init in initials:
            if py.startswith(init):
                return init
        return ""
    return get_initial(a) == get_initial(b) and get_initial(a) != ""


def _same_final(a: str, b: str) -> bool:
    """True if two base pinyins share the same final (rime)."""
    initials = ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l",
                "g", "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w")
    def strip_initial(py: str) -> str:
        for init in initials:
            if py.startswith(init):
                return py[len(init):]
        return py
    fa, fb = strip_initial(a), strip_initial(b)
    return fa == fb and fa != ""


def _pick_distractors_pinyin(
    correct: CharacterEntry,
    pool: list[CharacterEntry],
    rng: Random,
    difficulty: str,
    count: int,
) -> list[str]:
    """Pick *count* distractor pinyin strings for a hz2py question."""
    correct_full = correct.pinyin_full
    used: set[str] = {correct_full}
    result: list[str] = []

    # Priority buckets
    near_sound: list[str] = []
    same_tone: list[str] = []
    rest: list[str] = []

    for e in pool:
        pf = e.pinyin_full
        if pf in used:
            continue
        if _same_initial(e.pinyin_raw, correct.pinyin_raw) or _same_final(e.pinyin_raw, correct.pinyin_raw):
            near_sound.append(pf)
        elif e.tone == correct.tone:
            same_tone.append(pf)
        else:
            rest.append(pf)

    # Deduplicate buckets
    near_sound = list(dict.fromkeys(near_sound))
    same_tone = list(dict.fromkeys(same_tone))
    rest = list(dict.fromkeys(rest))

    rng.shuffle(near_sound)
    rng.shuffle(same_tone)
    rng.shuffle(rest)

    # Hard: near_sound heavily preferred; Easy: mix is fine
    near_quota = count if difficulty == "hard" else max(1, count // 2)

    for pf in near_sound[:near_quota]:
        if len(result) >= count:
            break
        if pf not in used:
            result.append(pf)
            used.add(pf)

    for bucket in (same_tone, rest):
        for pf in bucket:
            if len(result) >= count:
                break
            if pf not in used:
                result.append(pf)
                used.add(pf)

    # Fallback: grab anything unique
    if len(result) < count:
        all_pool = list(dict.fromkeys(e.pinyin_full for e in pool))
        rng.shuffle(all_pool)
        for pf in all_pool:
            if len(result) >= count:
                break
            if pf not in used:
                result.append(pf)
                used.add(pf)

    return result[:count]


def _pick_distractors_hanzi(
    correct: CharacterEntry,
    pool: list[CharacterEntry],
    rng: Random,
    count: int,
) -> list[str]:
    """Pick *count* distractor hanzi strings for a py2hz question."""
    used: set[str] = {correct.hanzi}
    result: list[str] = []
    candidates = [e.hanzi for e in pool if e.hanzi not in used]
    candidates = list(dict.fromkeys(candidates))
    rng.shuffle(candidates)
    for hz in candidates:
        if len(result) >= count:
            break
        if hz not in used:
            result.append(hz)
            used.add(hz)
    return result[:count]


# ---------------------------------------------------------------------------
# Question builders
# ---------------------------------------------------------------------------

def build_mcq_question(
    rng: Random,
    entries: list[CharacterEntry],
    direction: Literal["hz2py", "py2hz"],
    difficulty: str = "medium",
) -> MCQQuestion | None:
    """Build a 4-choice MCQ question from *entries*.

    direction:
      'hz2py' – show a hanzi, pick the correct pinyin.
      'py2hz' – show a pinyin, pick the correct hanzi.

    Returns None if the pool is too small (< 4 unique options).
    """
    if len(entries) < 4:
        return None

    correct = rng.choice(entries)

    if direction == "hz2py":
        # Use display (unicode) form so choices render correctly in the UI.
        # Deduplication inside _pick_distractors_pinyin still uses pinyin_full.
        correct_display = correct.pinyin_display
        distractors_full = _pick_distractors_pinyin(correct, entries, rng, difficulty, 3)
        if len(distractors_full) < 3:
            return None
        distractor_displays = [_pinyin_full_to_display(d) for d in distractors_full]
        choices_list = [correct_display] + distractor_displays
        rng.shuffle(choices_list)
        return MCQQuestion(
            prompt=correct.hanzi,
            choices=tuple(choices_list),
            answer_index=choices_list.index(correct_display),
            direction=direction,
        )
    else:  # py2hz
        correct_answer = correct.hanzi
        distractors = _pick_distractors_hanzi(correct, entries, rng, 3)
        if len(distractors) < 3:
            return None
        choices_list = [correct_answer] + distractors
        rng.shuffle(choices_list)
        return MCQQuestion(
            prompt=correct.pinyin_display,
            choices=tuple(choices_list),
            answer_index=choices_list.index(correct_answer),
            direction=direction,
        )


def build_match_pairs(
    rng: Random,
    entries: list[CharacterEntry],
    pair_count: int,
    difficulty: str = "medium",
) -> list[MatchPair]:
    """Return *pair_count* unique hanzi-pinyin pairs for Mode 3 (matching)."""
    if len(entries) < pair_count:
        pair_count = len(entries)
    chosen = rng.sample(entries, pair_count)
    return [MatchPair(left=e.hanzi, right=e.pinyin_display) for e in chosen]


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def normalize_pinyin_input(raw_text: str) -> str:
    """Normalize user-typed pinyin: lowercase, strip whitespace, 'v' stays as-is."""
    return raw_text.strip().lower()


def judge_pinyin_answer(
    target: CharacterEntry,
    typed_base: str,
    typed_tone: int,
    strict_tone: bool = True,
) -> bool:
    """Return True if the typed answer matches the target entry.

    typed_base  – base pinyin without tone (e.g. 'xiao').
    typed_tone  – tone number 0-4 as selected by the player.
    strict_tone – if False, tone mismatch is forgiven.
    """
    norm_typed = normalize_pinyin_input(typed_base)
    norm_target = target.pinyin_raw
    if norm_typed != norm_target:
        return False
    if strict_tone:
        return typed_tone == target.tone
    return True


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_hit(streak: int, base: int = 10) -> int:
    """Points awarded for a correct answer given the current streak."""
    bonus = min(streak * 2, 20)
    return base + bonus


def compute_round_result(stats: RoundStats, score: int) -> RoundResult:
    """Summarise a completed round."""
    return RoundResult(
        score=score,
        correct_count=stats.correct_count,
        wrong_count=stats.wrong_count,
        accuracy_percent=stats.accuracy_percent,
        best_streak=stats.best_streak,
        avg_answer_ms=stats.avg_answer_ms,
    )
