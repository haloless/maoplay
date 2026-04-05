from __future__ import annotations

from typing import Optional

import pygame


def is_confirm_key(event: pygame.event.Event) -> bool:
    return event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)


def is_back_key(event: pygame.event.Event) -> bool:
    return event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)


def move_selection(current: int, delta: int, total: int) -> int:
    if total <= 0:
        return 0
    return (current + delta) % total


def digit_choice(event: pygame.event.Event, total: int) -> Optional[int]:
    if event.type != pygame.KEYDOWN:
        return None
    digits = {
        pygame.K_1: 0,
        pygame.K_2: 1,
        pygame.K_3: 2,
        pygame.K_4: 3,
        pygame.K_5: 4,
        pygame.K_6: 5,
        pygame.K_7: 6,
        pygame.K_8: 7,
        pygame.K_9: 8,
    }
    choice = digits.get(event.key)
    if choice is None or choice >= total:
        return None
    return choice

