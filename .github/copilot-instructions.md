# Copilot Instructions

## Build, test, and run

- Use the project virtual environment in `.venv`.
- Install the package and runtime dependency with `.venv/bin/python -m pip install -e .`.
- Start the launcher with `.venv/bin/python -m maogame`.
- List available games with `.venv/bin/python -m maogame --list-games`.
- Run a short headless smoke test with `.venv/bin/python -m maogame --headless --max-frames 3`.
- Run the full test suite with `.venv/bin/python -m unittest discover -s tests`.
- Run one test file with `.venv/bin/python -m unittest tests.test_counting_logic`.
- Run one test with `.venv/bin/python -m unittest tests.test_registry.RegistryTests.test_registered_games_have_expected_ids`.

## High-level architecture

- `maogame.app` is the CLI entry point. It parses flags, optionally enables headless mode, initializes `pygame`, builds the shared `Runtime`, and starts `GameLoop`.
- `maogame.launcher.LauncherScene` is the root menu. It renders the list of games from the central registry and launches the selected game scene. Keep layout calculations data-driven so the menu still fits when more games are added.
- Shared engine code lives in `maogame.core`:
  - `scene.py` defines `Scene` and `SceneTransition`.
  - `game_loop.py` owns the event loop and scene switching.
  - `runtime.py` carries shared config, assets, RNG, and the game registry.
  - `registry.py` defines `GameSpec` and loads the fixed set of registered games.
  - `quiz.py` provides the shared multiple-choice scene flow used by the starter games.
- Each game lives in its own package under `maogame.games.<game_id>`.
  - `__init__.py` exposes a `GAME` registration object.
  - `logic.py` contains question generation and other non-graphical rules.
  - `scene.py` contains the `pygame` rendering and input layer for that game.

## Key conventions

- Keep game registration lightweight and lazy. Each `scene_factory` imports its scene inside the factory so registry access and non-graphical tests do not require `pygame`.
- Keep testable game logic in `logic.py`; avoid mixing question generation or answer evaluation into `scene.py`.
- New games should be self-contained packages under `maogame.games` and should not import other games directly. Shared behavior belongs in `maogame.core`.
- The current test suite uses the standard library `unittest`, not `pytest`.
- Use the existing command style from `README.md`: invoke tools through `.venv/bin/python` instead of assuming a globally active environment.
