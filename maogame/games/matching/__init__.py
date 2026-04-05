from maogame.core.registry import GameSpec


def create_scene():
    from .scene import MatchingScene

    return MatchingScene()


GAME = GameSpec(
    game_id="matching",
    title="Letter Match",
    summary="Match a big letter to the same small letter.",
    age_band="Ages 5-7",
    scene_factory=create_scene,
)
