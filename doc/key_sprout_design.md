# Key Sprout Design

## Concept Summary

- Game ID: key-sprout
- Working title: Key Sprout
- Target age: 6-7
- Primary learning goal: Build familiarity and confidence with keyboard keys A-Z, a-z, and 0-9.
- Session length: 3-6 minutes per run.

Key Sprout is a fast reaction typing game with two play styles:
- Character Mode: colorful letter and number seeds appear one at a time.
- Word Mode: the player types a full word target before time runs out.

Correct answers grow a cheerful garden and increase score streaks. The loop is simple enough for young children and supports progressive challenge.

## Why It Fits This Repo

- Uses simple, testable generation and scoring rules that can live in logic.py.
- Keeps pygame rendering and animation responsibilities in scene.py.
- Supports launcher registration as a normal self-contained package under maogame/games/key_sprout.
- Difficulty model mirrors existing game patterns with explicit level metadata.

## Candidate Concepts Considered

1. Falling Key Rain
- Children type characters that fall from top to bottom.
- Strong urgency and easy to understand.
- Risk: too much pressure for younger learners on small screens.

2. Balloon Pop Typing
- Balloons with target characters drift across the screen; typing pops them.
- Good visual delight and easier pacing control.
- Risk: more collision and motion tuning needed.

3. Garden Grow Typing (Selected)
- Character seeds appear in garden plots; typing grows flowers and bugs.
- Friendly low-stress tone and clear reward feedback.
- Best fit for 6-7 age band with achievement-driven loop.

## Final Gameplay Requirements

### Core Loop

1. Player selects difficulty: Easy, Medium, Hard.
2. Player selects play mode: Character Mode or Word Mode.
3. Game shows one active target at a time.
4. In Character Mode, the target is one character.
5. In Word Mode, the target is one whole word and the player types all letters.
4. Correct input:
- score increases,
- streak increases,
- one plant visually grows,
- short celebration animation plays.
5. Wrong input or timeout:
- streak resets,
- life/heart decreases,
- gentle correction animation plays.
6. Round ends when timer reaches zero or hearts are exhausted.
7. Result screen shows score, best streak, stars earned, and encouraging message.

### Input Rules

- Accept keyboard events for letters and digits only in Character Mode.
- In Word Mode, accept letter keys and Backspace.
- Character Mode matching is based on exact target definition per difficulty:
- Easy: lowercase letters a-z only.
- Medium: mixed uppercase and lowercase letters A-Z and a-z.
- Hard: mixed uppercase, lowercase, and digits 0-9.
- If a non-target key is pressed (for example Shift, Tab, arrows), ignore input and do not penalize.

Word Mode input behavior:
- Player types the full target word.
- If typed wrongly, Backspace removes the last character so the player can fix the word.
- Wrong letter input does not immediately consume hearts; timeout still counts as a miss.

### Difficulty Levels

Define level metadata in logic.py with deterministic parameters:

- Easy
- Character set: lowercase a-z
- Time per prompt: 3.5 seconds
- Total round time: 90 seconds
- Hearts: 5
- Score per correct: 10
- Streak bonus: +2 per step after streak 3 (capped at +10)

- Medium
- Character set: A-Z and a-z
- Time per prompt: 2.6 seconds
- Total round time: 90 seconds
- Hearts: 4
- Score per correct: 12
- Streak bonus: +3 per step after streak 3 (capped at +15)

- Hard
- Character set: A-Z, a-z, 0-9
- Time per prompt: 1.9 seconds
- Total round time: 90 seconds
- Hearts: 3
- Score per correct: 15
- Streak bonus: +4 per step after streak 2 (capped at +20)

Word Mode target length ranges by difficulty:
- Easy: 3-4 letters
- Medium: 4-6 letters
- Hard: 5-8 letters

### Scoring And Achievement

- Score formula:
- points = base_points + streak_bonus
- streak_bonus is derived from current streak and difficulty cap.
- Track:
- current_score
- best_streak
- correct_count
- miss_count
- accuracy_percent
- Star rating at end of round:
- 1 star: score >= 300
- 2 stars: score >= 600
- 3 stars: score >= 900
- Persist local best score per difficulty for visible long-term achievement.

### Fail And Recovery Behavior

- Timeout counts as a miss.
- Wrong key counts as a miss.
- Miss reduces hearts by 1.
- When hearts reach 0, round ends immediately with a soft fail state.
- Encourage replay with positive copy (for example: Great try. Let us grow even bigger next round.).

## Content Generation Rules (logic.py)

- Expose deterministic APIs that use random.Random passed in by caller.
- Persist the 1000-word candidate source list from https://gist.github.com/deekayen/4148741 at `maogame/games/key_sprout/words_1000.txt`.
- Required data structures:
- Difficulty dataclass with level_id, title, charset, prompt_timeout_sec, round_duration_sec, hearts, base_points, streak_bonus_start, streak_bonus_step, streak_bonus_cap.
- Prompt dataclass with target_char and expires_at_ms.
- RoundState dataclass with score, streak, best_streak, hearts, remaining_time_ms, counts.
- Required functions:
- choose_next_target(rng, difficulty, previous_target=None) -> str
- choose_word_target(rng, min_len, max_len, previous_word=None) -> str
- score_for_hit(streak_before_hit, difficulty) -> int
- register_hit(state, difficulty) -> RoundState
- register_miss(state) -> RoundState
- compute_star_rating(score) -> int
- accuracy_percent(correct_count, miss_count) -> int

Rules for choose_next_target:

- Uniform random selection from difficulty charset.
- Do not repeat the exact same target more than 2 times in a row.

## Scene And UI Requirements (scene.py)

### Visual Direction

- Bright day-garden palette with high contrast text.
- Large, rounded glyph rendering for readability.
- Character target appears center stage with bounce-in animation.
- Word Mode shows the full target word with a typed-progress line beneath it.
- Correct input animation:
- flower grows one stage,
- score pops upward,
- confetti burst (short, low particle count).
- Miss animation:
- target wiggle + fade,
- heart icon pulse down.

### Accessibility And Readability

- Minimum target glyph size equivalent to about 96 px on 1280x720.
- Keep color contrast high (avoid low-contrast pastel text on bright backgrounds).
- Offer optional reduced motion flag in runtime config if available; otherwise make animations brief and non-blocking.

### HUD

- Top-left: score.
- Top-center: timer bar/countdown.
- Top-right: hearts.
- Bottom: streak meter and best streak badge.

### Controls

- Any valid key press attempts answer.
- In Word Mode, Backspace edits the typed word buffer.
- Enter confirms buttons on menus.
- Escape returns to launcher from pre-round and result screens.

## Assets

- No mandatory external assets required for first version.
- Prefer procedural shapes and existing default fonts in pygame for MVP.
- Optional enhancement: bundle one child-friendly rounded font if licensing is clear.

## Package And Registration Plan

- Add package: maogame/games/key_sprout/
- Files:
- __init__.py with GAME registration object.
- logic.py for deterministic gameplay rules.
- scene.py for rendering, animation, and input.
- Registration:
- Use lazy scene_factory import pattern consistent with existing games.

## Implementation Milestones

1. Logic foundation
- Add Difficulty, RoundState, and scoring functions.
- Add prompt generation and anti-repeat behavior.
- Add unit tests for deterministic and edge cases.

2. Basic playable scene
- Difficulty select screen.
- Mode toggle on level select (Character or Word).
- Round loop with target display and keyboard validation.
- Score, hearts, timer, and result screen.

3. Visual polish
- Add bounce, pop, confetti, and miss effects.
- Tune pacing and color readability.
- Ensure consistent frame behavior in headless-safe logic separation.

4. Integration
- Register game in central registry.
- Verify launcher entry and round start/exit flows.
- Run full unittest suite and quick headless smoke test.

## Test Matrix (unittest)

Create tests in tests/test_key_sprout_logic.py.

1. Difficulty definitions
- Verify exactly three levels exist.
- Verify each charset matches expected keys.

2. Target generation
- choose_next_target always returns from charset.
- Anti-repeat rule prevents 3+ identical consecutive targets.
- choose_word_target returns alphabetic words inside configured length range.

3. Scoring
- score_for_hit matches base and capped streak bonus.
- register_hit increases score/streak and updates best_streak.
- register_miss resets streak and decreases hearts by 1.

4. Round outcomes
- Hearts reaching zero indicates terminal fail state.
- compute_star_rating returns 0-3 with expected thresholds.
- accuracy_percent handles divide-by-zero as 0.

5. Determinism
- Same random seed produces same initial target sequence per difficulty.

6. Word mode behavior
- Backspace removes last typed letter.
- Wrong input can be corrected without immediate life loss.

## Acceptance Criteria

1. Child can complete one full round using only keyboard input.
2. Easy mode uses lowercase only; Medium adds uppercase; Hard adds digits.
3. Score increases on correct input and visibly communicates achievement.
4. At least two animated effects are present for hit/miss feedback.
5. Logic unit tests pass for scoring, difficulty, and target generation.
6. Game appears in launcher and starts without importing pygame during registry-only tests.
7. Word Mode can complete a whole-word target and supports Backspace correction.
8. Candidate words are loaded from the saved 1000-word list file.

## Open Decisions (TBD)

- TBD: Whether to include punctuation in a future Expert mode.
- TBD: Whether per-key heatmap stats should be tracked for parent/teacher view.
- TBD: Whether to add adaptive difficulty that increases speed after long streaks.