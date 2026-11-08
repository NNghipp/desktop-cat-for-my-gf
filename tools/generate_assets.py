"""Draw original, replaceable 64px calico sprites using Pillow only.

Run from any directory: .venv/Scripts/python tools/generate_assets.py
No downloaded images, fonts or network services are required.
"""
from pathlib import Path
import json
import math

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "desktop_cat" / "assets"
PREVIEWS = ROOT / "previews"
INK = "#3c303b"
WHITE = "#fff5df"
SHADE = "#dfd1bc"
ORANGE = "#e99b54"
LIGHT = "#ffc077"
DARK = "#58505c"
PINK = "#e89d9c"
GREEN = "#8bba96"


SHEET = Image.open(ROOT / "tools" / "calico-sheet.png").convert("RGBA")
STATES = ["walk", "eat", "sleep", "wake", "angry"]
COLUMNS = {"walk": range(8), "eat": [0, 2, 3, 4, 5, 7],
           "sleep": [0, 2, 3, 5], "wake": [0, 2, 3, 5, 6, 7],
           "angry": [0, 1, 2, 4, 5, 7]}


def draw_frame(state, i):
    if state == "angry":
        with Image.open(ROOT / "tools" / "angry-sheet.png") as sheet:
            size = sheet.width // 3
            x, y = (i % 3) * size, (i // 3) * size
            tile = sheet.crop((x, y, x + size, y + size))
        tile.putalpha(tile.getchannel("A").point(lambda a: 255 if a >= 180 else 0))
        tile = tile.crop(tile.getbbox())
        tile = tile.resize((round(tile.width * 0.12), round(tile.height * 0.12)),
                           Image.Resampling.NEAREST)
        frame = Image.new("RGBA", (64, 64))
        frame.paste(tile, ((64 - tile.width) // 2, 60 - tile.height))
        return frame
    row = STATES.index(state)
    col = COLUMNS[state][i]
    w, h = SHEET.size
    tile = SHEET.crop((round(col*w/8), round(row*h/5),
                       round((col+1)*w/8), round((row+1)*h/5)))
    alpha = tile.getchannel("A").point(lambda v: 255 if v >= 160 else 0)
    tile.putalpha(alpha)
    tile = tile.crop(alpha.getbbox())
    scale = 55 / (w/8)
    tile = tile.resize((round(tile.width*scale), round(tile.height*scale)),
                       Image.Resampling.NEAREST).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    frame = Image.new("RGBA", (64, 64))
    frame.paste(tile, ((64-tile.width)//2, 60-tile.height))
    if state == "walk":
        # Bend the original hindquarter gradually from hip to paw. The fur,
        # outline and toes all travel together. Front paws use the sheet gait.
        original = frame
        frame = original.copy()
        swing = (-2, -1, 1, 2, 2, 1, 0, -1)[i]
        rise = (0, 1, 2, 2, 1, 0, 0, 0)[i]
        for y in range(49, 60):
            bend = (y - 49) / 10
            for x in range(12, 33):
                weight = bend * min(1, (33 - x) / 5)
                source = (x - round(swing * weight), y + round(rise * weight))
                frame.putpixel((x, y), original.getpixel(source))
    return frame


def font(size):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def generate():
    ASSETS.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    specs = {"walk": (8, 8, True), "eat": (6, 6, True),
             "sleep": (4, 2, True), "wake": (6, 6, False), "angry": (6, 8, True)}
    manifest = {"sprite_size": [64, 64], "animations": {}}
    drawings = {}
    sheet = Image.new("RGB", (8 * 144 + 32, 5 * 164 + 40), "#f7efdf")
    sd = ImageDraw.Draw(sheet)
    labels = {"walk": "Đi bộ", "eat": "Ăn", "sleep": "Ngủ",
              "wake": "Thức dậy", "angry": "Tức giận"}
    for row, (state, (count, fps, loop)) in enumerate(specs.items()):
        names = []
        drawings[state] = []
        folder = ASSETS / state
        folder.mkdir(exist_ok=True)
        sd.text((20, 12 + row * 164), f"{labels[state]}  /  {fps} fps", font=font(15), fill=INK)
        for i in range(count):
            image = draw_frame(state, i)
            name = f"{state}/{i:02}.png"
            image.save(ASSETS / name)
            names.append(name)
            drawings[state].append(image)
            sheet.paste(image.resize((128, 128), Image.Resampling.NEAREST),
                        (16 + i * 144, 40 + row * 164),
                        image.resize((128, 128), Image.Resampling.NEAREST))
        manifest["animations"][state] = {"frames": names, "fps": fps,
                                           "loop": loop, "ground_y": 60}
    (ASSETS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sheet.save(PREVIEWS / "contact_sheet.png")
    gif = []
    for tick in range(48):
        canvas = Image.new("RGB", (1000, 286), "#f7efdf")
        cd = ImageDraw.Draw(canvas)
        cd.text((28, 19), "MÈO TAM THỂ", font=font(23), fill=INK)
        cd.text((28, 52), "Một người bạn nhỏ trên desktop", font=font(14), fill="#8b7769")
        for col, state in enumerate(specs):
            count, fps, loop = specs[state]
            index = int(tick / 12 * fps)
            index = index % count if loop else min(index % (count * 2), count - 1)
            sprite = drawings[state][index].resize((128, 128), Image.Resampling.NEAREST)
            cd.rounded_rectangle((18 + col * 196, 90, 198 + col * 196, 268), radius=16,
                                 fill="#fffbf4", outline="#e6d6bd")
            canvas.paste(sprite, (44 + col * 196, 103), sprite)
            cd.text((108 + col * 196, 242), labels[state], font=font(16),
                    fill=INK, anchor="mm")
        gif.append(canvas)
    gif[0].save(PREVIEWS / "preview.png")
    gif[0].save(PREVIEWS / "preview.gif", save_all=True, append_images=gif[1:],
                duration=83, loop=0, disposal=2)
    drawings["walk"][0].resize((256, 256), Image.Resampling.NEAREST).save(
        ASSETS / "cat.ico", sizes=[(32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Generated {sum(x[0] for x in specs.values())} frames in {ASSETS}")


if __name__ == "__main__":
    generate()
