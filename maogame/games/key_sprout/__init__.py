from maogame.core.registry import GameSpec


def create_scene():
    from .scene import KeySproutScene

    return KeySproutScene()


GAME = GameSpec(
    game_id="key-sprout",
    title="Key Sprout",
    summary="Type the matching letters and numbers to grow a colorful garden.",
    age_band="Ages 6-7",
    scene_factory=create_scene,
)
