import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from .behavior import State


ASSETS = Path(__file__).resolve().parent / "assets"


class AnimationLibrary:
    def __init__(self, display_size: int, assets: Path = ASSETS):
        manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
        self.animations = manifest["animations"]
        self.frames: dict[tuple[State, int], list[QPixmap]] = {}
        for state in State:
            spec = self.animations[state.value]
            images = []
            for name in spec["frames"]:
                frame = QPixmap(str(assets / name))
                if frame.isNull():
                    raise ValueError(f"Không đọc được ảnh: {name}")
                images.append(frame.scaled(display_size, display_size,
                                           Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.FastTransformation))
            if not images or spec["fps"] <= 0:
                raise ValueError(f"Hoạt ảnh không hợp lệ: {state}")
            self.frames[state, 1] = images
            self.frames[state, -1] = [
                QPixmap.fromImage(frame.toImage().flipped(Qt.Orientation.Horizontal))
                for frame in images
            ]

    def duration(self, state: State) -> float:
        spec = self.animations[state.value]
        return len(spec["frames"]) / spec["fps"]

    def index(self, state: State, elapsed: float) -> int:
        spec = self.animations[state.value]
        index = int((elapsed + 1e-9) * spec["fps"])
        count = len(spec["frames"])
        return index % count if spec["loop"] else min(index, count - 1)

    def frame(self, state: State, elapsed: float, direction: int) -> QPixmap:
        return self.frames[state, direction][self.index(state, elapsed)]
