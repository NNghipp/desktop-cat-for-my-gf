from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    sprite_size: int = 64
    display_scale: int = 2
    speed: float = 40.0  # Qt logical pixels / second
    walk_min: float = 45.0
    walk_max: float = 90.0
    eat_seconds: float = 8.0
    sleep_min: float = 30.0
    sleep_max: float = 60.0
    angry_seconds: float = 2.0
    frame_interval_ms: int = 16

    @property
    def display_size(self) -> int:
        return self.sprite_size * self.display_scale
