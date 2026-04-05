from maogame.core.registry import GameSpec


def create_scene():
    from .scene import LettersScene

    return LettersScene()


GAME = GameSpec(
    game_id="letters",
    title="First Letter Fun",
    summary="Spot the first letter that completes a familiar word.",
    age_band="Ages 5-7",
    scene_factory=create_scene,
)

