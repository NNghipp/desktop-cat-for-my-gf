import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QImage

from .behavior import State


ASSETS = Path(__file__).resolve().parent / "assets"


COATS = {
    "calico": ("Tam thể", None),
    # Body, body shadow, patch, patch highlight, deep marking.
    "siamese": ("Xiêm", ["#fff4de", "#ddcbb4", "#947057", "#ba9980", "#76513b"]),
    "orange": ("Cam", ["#ffad42", "#f28c28", "#f28c28", "#ffad42", "#a9561c"]),
    "white": ("Trắng", ["#fff9ec", "#ded5c9", "#ece4d7", "#faf4ea", "#cec5b9"]),
    "gray": ("Xám", ["#b4b4b3", "#919293", "#929497", "#c4c3c0", "#76777a"]),
    "tuxedo": ("Xám trắng", ["#fff7e7", "#ded5c6", "#87898c", "#adafb0", "#65686e"]),
    "tabby": ("Mướp nâu", ["#d8b594", "#b78e6b", "#ae7c56", "#ce9f77", "#835a40"]),
}
# The role atlas shares the native frame grid. Protected face pixels and
# linework are copied verbatim, even when their RGB also occurs in the fur.
def recolor(image, coat, mask, index):
    colors = COATS[coat][1] or ("#ffedd6","#daba9a","#e79841","#ffbc6a","#593e2f")
    palette = [QColor(value) for value in colors]
    eye = QColor("#0b0908")
    glint = QColor("#ffffff")
    offset = index * image.width()
    for y in range(image.height()):
        for x in range(image.width()):
            role = mask.pixelColor(offset+x,y).red()
            if role == 22:
                image.setPixelColor(x,y,QColor("#76503a"))
            elif role == 21:
                image.setPixelColor(x,y,QColor("#c66a20"))
            elif role in (14,15):
                image.setPixelColor(x,y,eye if role == 14 else glint)
            elif 16 <= role <= 20:
                image.setPixelColor(x,y,palette[role-16])
            elif coat == "calico":
                continue
            elif 1 <= role <= 5:
                image.setPixelColor(x,y,palette[role-1])
            elif 9 <= role <= 13:
                shade = 4 if coat == "siamese" else role-9
                image.setPixelColor(x,y,palette[shade])
    return image


class AnimationLibrary:
    def __init__(self, display_size: int, assets: Path = ASSETS, coat="calico"):
        manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
        self.animations = manifest["animations"]
        self.frames: dict[tuple[State, int], list[QPixmap]] = {}
        for state in State:
            spec = self.animations[state.value]
            filename = f"orange-{state.value}.png" if coat == "orange" else f"{state.value}.png"
            mask = QImage(str(assets / "masks" / filename))
            if mask.isNull() and (coat != "calico" or assets == ASSETS):
                raise ValueError(f"Missing coat mask: {state.value}")
            images = []
            for index, name in enumerate(spec["frames"]):
                frame = QPixmap(str(assets / name))
                if frame.isNull():
                    raise ValueError(f"Không đọc được ảnh: {name}")
                if not mask.isNull():
                    frame = QPixmap.fromImage(recolor(frame.toImage(), coat, mask, index))
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
