from maogame.core.registry import GameSpec


def _create_scene():
    from .scene import HanziPinyinPathScene

    return HanziPinyinPathScene()


GAME = GameSpec(
    game_id="hanzi-pinyin-path",
    title="汉字拼音小径",
    summary="按年级练习汉字与拼音对应，支持选择与连线",
    age_band="6-12",
    scene_factory=_create_scene,
)
