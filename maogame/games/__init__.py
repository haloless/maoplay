from .counting import GAME as COUNTING_GAME
from .hanzi_pinyin_path import GAME as HANZI_PINYIN_PATH_GAME
from .key_sprout import GAME as KEY_SPROUT_GAME
from .letters import GAME as LETTERS_GAME
from .matching import GAME as MATCHING_GAME
from .pick_cards import GAME as PICK_CARDS_GAME
from .shapes import GAME as SHAPES_GAME

REGISTERED_GAMES = (
	COUNTING_GAME,
	LETTERS_GAME,
	SHAPES_GAME,
	MATCHING_GAME,
	PICK_CARDS_GAME,
	KEY_SPROUT_GAME,
	HANZI_PINYIN_PATH_GAME,
)
