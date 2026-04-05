from maogame.core.registry import GameSpec


def create_scene():
    from .scene import PickCardsScene

    return PickCardsScene()


GAME = GameSpec(
    game_id="pick-cards",
    title="Pick the Cards",
    summary="Pick 2 or more cards that add up to the target number.",
    age_band="Ages 5-7",
    scene_factory=create_scene,
)