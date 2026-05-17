# Game Test Agent Playbook

This document defines a practical workflow to run a player-minded game test pass with the `Game Test Agent`.

## Goals

- Launch and smoke-test real game scenes.
- Catch runtime and gameplay issues early.
- Produce a structured report with prioritized fixes.

## Recommended Test Levels

- `quick`:
  - List games
  - Launch each target game headless for a short frame window
  - Run one relevant test module
- `normal`:
  - All quick checks
  - Run full unit test suite
  - Inspect target game `logic.py` and `scene.py`
  - Provide prioritized findings with fix proposals
- `deep`:
  - All normal checks
  - Add/adjust automated tests for discovered gaps
  - Patch code if requested and re-verify

## Baseline Commands

```bash
.venv/bin/python -m maogame --list-games
.venv/bin/python -m maogame --headless --max-frames 3
.venv/bin/python -m unittest discover -s tests
```

Per-game startup smoke:

```bash
for game in $(.venv/bin/python -m maogame --list-games | cut -d: -f1); do
  .venv/bin/python -m maogame --headless --start-game "$game" --max-frames 3
done
```

## Prompt Templates

Quick report only:

```text
Run a quick game test pass for all registered games.
Depth: quick.
Report only, do not patch code.
Return findings ordered by severity with reproduction steps.
```

Deep test with fixes:

```text
Run a deep game test pass for hanzi_pinyin_path and key-sprout.
Depth: deep.
Patch high-severity issues and add/update tests.
Then rerun verification and summarize remaining risks.
```

## Report Checklist

- Tested targets and exact commands executed
- Findings sorted by severity
- Expected vs actual behavior for each issue
- Reproduction steps
- Proposed fix and test impact
- Remaining risks and suggested next steps

## Notes

- Headless runs validate startup/event-loop stability and basic flow only.
- Manual visual UX review is still needed for layout, readability, and animation quality.
