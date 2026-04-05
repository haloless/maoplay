from maogame.core.registry import GameSpec


def create_scene():
    from .scene import CountingScene

    return CountingScene()


GAME = GameSpec(
    game_id="counting",
    title="Counting Stars",
    summary="Count a small group of stars and pick the right number.",
    age_band="Ages 5-7",
    scene_factory=create_scene,
)

