# maogame

`maogame` is a small Python project for child-friendly educational mini-games built with `pygame`.

## Planned focus

- Early primary school learners
- Short, simple activities
- Multiple games under one launcher
- Shared runtime code with game-specific logic kept in separate modules

## Run locally

Create or reuse the existing virtual environment in `.venv`, then install the project:

```bash
.venv/bin/python -m pip install -e .
```

Start the launcher:

```bash
.venv/bin/python -m maogame
```

List the currently available games:

```bash
.venv/bin/python -m maogame --list-games
```

Current starter games:

- `counting` - count visible stars and choose the number
- `letters` - choose the first letter for a familiar word
- `shapes` - identify a named shape
- `matching` - match an uppercase letter to its lowercase pair
- `pick-cards` - choose 2 or more cards that add up to the target number

Run a short headless smoke test:

```bash
.venv/bin/python -m maogame --headless --max-frames 3
```

## Tests

Run the full test suite:

```bash
.venv/bin/python -m unittest discover -s tests
```

Run one test file:

```bash
.venv/bin/python -m unittest tests.test_counting_logic
```

Run a single test:

```bash
.venv/bin/python -m unittest tests.test_registry.RegistryTests.test_registered_games_have_expected_ids
```
