from maogame.core.registry import GameSpec


def create_scene():
    from .scene import ShapesScene

    return ShapesScene()


GAME = GameSpec(
    game_id="shapes",
    title="Shape Match",
    summary="Find the named shape from a set of simple shapes.",
    age_band="Ages 5-7",
    scene_factory=create_scene,
)

