from __future__ import annotations

from dataclasses import dataclass, field


Color = tuple[int, int, int]


@dataclass(frozen=True)
class Palette:
    background: Color = (245, 248, 255)
    text: Color = (35, 49, 71)
    accent: Color = (77, 121, 255)
    accent_soft: Color = (221, 232, 255)
    success: Color = (89, 179, 118)
    error: Color = (224, 107, 107)
    card: Color = (255, 255, 255)
    card_border: Color = (201, 214, 235)
    card_selected: Color = (253, 236, 179)
    shape_circle: Color = (254, 163, 163)
    shape_square: Color = (122, 197, 205)
    shape_triangle: Color = (255, 206, 117)
    shape_star: Color = (176, 152, 255)


@dataclass(frozen=True)
class AppConfig:
    window_width: int = 960
    window_height: int = 640
    fps: int = 60
    title: str = "MaoGame"
    quiz_rounds: int = 5
    palette: Palette = field(default_factory=Palette)

