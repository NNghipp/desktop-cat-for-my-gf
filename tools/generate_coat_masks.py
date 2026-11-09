"""Classify pixels in the untouched bb55977 masters; never paint the sprites."""
from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "desktop_cat/assets"
# Per-pose eye centres and nose row, measured on the original PNGs.
LANDMARKS = {
    "walk": [(32,42,y,y+3) for y in (35,35,36,36,36,35,35,35)],
    "eat": [(29,39,34,37),(32,41,40,43),(33,43,44,47),(33,43,46,49),(32,41,40,43),(32,41,35,38)],
    "sleep": [(33,43,45,48),(35,44,47,50),(33,43,49,52),(33,43,46,49)],
    "wake": [(33,43,45,48),(34,44,45,48),(32,42,43,46),(33,43,43,46),(34,43,39,42),(33,43,33,36)],
    "angry": [(36,48,38,42),(37,49,38,42),(37,49,38,42),(37,49,38,42),(37,48,38,42),(37,48,38,42)],
}
CLOSED = {"sleep": range(4), "eat": (2,3,4), "wake": (0,1,3)}
FUR = ["ffedd6","daba9a","e79841","ffbc6a","593e2f"]
# Left edge of the visible food/bowl on scanlines 50..59. In the two
# lowest head poses the tongue overlaps the rim and remains a face feature.
BOWL_LEFT = [
    (44,42,39,38,37,36,36,36,36,37),
    (42,42,40,37,37,36,36,36,37,37),
    (64,64,40,37,36,36,36,36,37,37),
    (64,64,40,40,36,35,35,35,36,36),
    (42,41,37,36,35,35,35,35,36,36),
    (44,42,40,38,37,36,36,36,37,38),
]
# Inclusive bounds traced around each nose and mouth on the native master.
SNOUT = [(31,36,38,40),(33,42,40,47),(34,46,41,52),
         (33,48,40,53),(33,42,40,46),(32,37,40,40)]


def local_fur(im, x, y):
    # Resolve ambiguous red/pink quantization samples from their own patch.
    from collections import Counter
    for radius in (1,2,3):
        shades = Counter()
        for yy in range(max(0,y-radius), min(im.height,y+radius+1)):
            for xx in range(max(0,x-radius), min(im.width,x+radius+1)):
                r,g,b,a = im.getpixel((xx,yy))
                color = bytes((r,g,b)).hex()
                if a and color in FUR:
                    shades[FUR.index(color)+1] += 1
        if shades:
            return shades.most_common(1)[0][0]
    return 5


# Mask values: 0 transparent/accessory, 1..5 fur shades, 6 contour/linework,
# 7 protected features, 9..13 point fur, 14 eye, 15 glint, 16..20 restored fur.
def classify(im, state, index):
    left,right,eye,nose = LANDMARKS[state][index]
    mask = Image.new("L", im.size)
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a = im.getpixel((x,y))
            if not a:
                continue
            rgb = bytes((r,g,b)).hex()
            if (state == "sleep" and x < 25 and y < 38
                    or state == "eat" and 50 <= y < 60 and x >= BOWL_LEFT[index][y-50]):
                continue
            near_eye = abs(y-eye) <= (4 if state=="angry" else 2) and min(abs(x-left),abs(x-right)) <= (4 if state=="angry" else 2)
            muzzle = nose-1 <= y <= nose+5 and left-1 <= x <= right+2
            if near_eye or muzzle:
                role = 7
                if near_eye and not muzzle and rgb in FUR and rgb != "593e2f":
                    role = FUR.index(rgb)+1
                elif near_eye and rgb=="593e2f" and min(abs(x-left),abs(x-right))>1:
                    role = 5
                elif muzzle and rgb in ("ffedd6","daba9a") and not (left+2 <= x <= right-2 and y<=nose):
                    role = FUR.index(rgb)+1
            elif rgb == "311c11":
                role = 6
            elif rgb in FUR:
                role = FUR.index(rgb)+1
            elif rgb in ("732a30","ee2f31") and not (state=="angry" and x>=34):
                role = 5 if rgb=="732a30" else 3
            else:
                role = 7
            if state == "eat":
                x0,y0,x1,y1 = SNOUT[index]
                if x0 <= x <= x1 and y0 <= y <= y1 and rgb not in FUR[:2]:
                    role = 7
                elif rgb in FUR:
                    role = FUR.index(rgb)+1
                elif (rgb in ("732a30","ee2f31") and not near_eye) or (rgb == "f29994" and (x < left-6 or y > nose+2)):
                    role = 16 + local_fur(im,x,y)-1
            if 1<=role<=5 and (x<=18 or y>=56):
                role += 8
            if state != "angry" and index not in CLOSED.get(state, ()):
                for center, fur_role in ((left,3), (right,5)):
                    dx, dy = x-center, y-eye
                    # Remove the previous eye ink inside this socket only.
                    wide = state == "angry"
                    if (-(4 if wide else 2) <= dx <= (4 if wide else 2)
                            and -(4 if wide else 2) <= dy <= (2 if wide else 1)
                            and rgb in ("311c11","732a30","fffcf3")
                            and all(im.getpixel((x+a,y+b))[3] for a,b in
                                    ((-1,0),(1,0),(0,-1),(0,1)))):
                        role = 16 + fur_role - 1
                    if dx in (0,1) and dy in (-1,0,1):
                        role = 15 if (dx,dy)==(0,-1) else 14
            mask.putpixel((x,y),role)
    return mask


def ginger_markings(roles, state, index):
    """Place stripes in cat-local coordinates, clipped to paintable fur."""
    left, right, eyes, nose = LANDMARKS[state][index]
    mid = (left + right) // 2
    fur = {(x,y) for y in range(64) for x in range(64)
           if roles.getpixel((x,y)) in (1,2,3,4,5,9,10,11,12,13)}
    result = roles.copy()

    def stroke(points):
        pixels = [point for point in points if point in fur]
        for x,y in pixels:
            if any((x+dx,y+dy) in pixels for dx,dy in ((0,1),(0,-1),(1,0),(-1,0))):
                result.putpixel((x,y),21)

    for dx, length in ((-3,3),(0,4),(3,3)):
        x = mid+dx
        top = min((y for y in range(eyes-11,eyes-3) if (x,y) in fur), default=eyes-7)
        stroke([(x,top+k) for k in range(length) if top+k < eyes-2])
    for x in (left-5,right+3):
        stroke([(x+k,eyes+1) for k in range(3)])

    # The exposed flank starts behind the head. Follow the upper edge at
    # each stripe; curled and stretching poses expose different back lengths.
    flank = [(x,y) for x,y in fur if mid-20 <= x < left-5 and y >= nose-4]
    if flank:
        base = min(x for x,y in flank)
        for x in range(base+2,left-4,3):
            ys = [y for xx,y in flank if xx==x]
            if ys:
                top = min(ys)
                stroke([(x,top),(x,top+1),(x+1,top+1),(x+1,top+2)])

    # Tail bands start at the moving tip. Stay within the narrow exposed
    # tail until it joins the haunch (the curled sleeping tail lies lower).
    tail = [(x,y) for x,y in fur if x < left-9]
    if tail:
        tip = min(y for x,y in tail)
        for y in (tip+3,tip+4,tip+9,tip+10):
            xs = [x for x,yy in tail if yy==y]
            if xs:
                stroke([(x,y) for x in range(min(xs),min(xs)+5)])
    # Anchor each cuff to a connected toe span on the lowest fur scanline.
    bottom = max(y for x,y in fur)
    toes = sorted(x for x,y in fur if y==bottom)
    for x in toes:
        if x-1 not in toes:
            stroke([(x+k,bottom-2) for k in range(3)])
    return result


# Inclusive runs of old eyelid ink, traced separately from nose and whiskers.
SLEEP_LIDS = (
    (((45,32,35),(46,32,35)), ((44,41,41),(45,42,44),(46,42,44))),
    (((46,32,36),(47,33,36)), ((47,42,45),(48,44,45))),
    (((49,31,35),(50,31,35)), ((49,40,44),(50,40,44))),
    (((45,32,35),(46,32,35)), ((45,41,44),(46,41,44))),
)


def sleeping_expression(mask, master, index):
    left, right, y, _ = LANDMARKS["sleep"][index]
    # Restore each old stroke to its local cheek shade. Only these pixels
    # and the new lids are touched, after the optional ginger stripe pass.
    # Some right-cheek fur was tagged as protected dark eye shading. Restore its coat shade locally.
    for yy in range(y-2,y+3):
        for xx in range(right-2,right+3):
            if mask.getpixel((xx,yy)) == 7 and master.getpixel((xx,yy))[:3] == (89,62,47):
                mask.putpixel((xx,yy),20)
    for runs, fur_role in zip(SLEEP_LIDS[index], (18,20)):
        for row, start, end in runs:
            for x in range(start,end+1):
                mask.putpixel((x,row),fur_role)
    for center in (left,right):
        for dx,dy in ((-1,0),(0,1),(1,0)):
            mask.putpixel((center+dx,y+dy),22)


def clean_calico_fur(im, roles, state, index):
    """Restore red quantization specks from neighbouring calico fur only."""
    left, right, eye, nose = LANDMARKS[state][index]
    result = roles.copy()
    mouth = SNOUT[index] if state == "eat" else (
        (left-1,eye+3,right+2,eye+15) if state == "angry"
        else (left+1,nose-1,right-1,nose+4))
    x0,y0,x1,y1 = mouth
    for y in range(64):
        for x in range(64):
            rgb = bytes(im.getpixel((x,y))[:3]).hex()
            if not im.getpixel((x,y))[3] or rgb not in ("ee2f31","732a30","f29994"):
                continue
            role = roles.getpixel((x,y))
            if role in (0,14,15,16,17,18,19,20,22):
                continue
            if x0<=x<=x1 and y0<=y<=y1:
                continue
            if state=="angry" and 34<=x<=47 and y<eye-5:
                continue
            # Pink inner-ear clusters are intentional. Red/maroon ink
            # elsewhere is a quantization remnant on the coat.
            if rgb=="f29994" and y<eye-2:
                continue
            result.putpixel((x,y),16+local_fur(im,x,y)-1)
    return result


if __name__ == "__main__":
    folder = ASSETS / "masks"
    folder.mkdir(exist_ok=True)
    for state, landmarks in LANDMARKS.items():
        strip = Image.new("L", (64*len(landmarks),64))
        ginger = strip.copy()
        calico = strip.copy()
        for index in range(len(landmarks)):
            im = Image.open(ASSETS/state/f"{index:02}.png").convert("RGBA")
            roles = classify(im,state,index)
            striped = ginger_markings(roles,state,index)
            if state == "sleep":
                sleeping_expression(roles,im,index)
                sleeping_expression(striped,im,index)
            calico.paste(clean_calico_fur(im,roles,state,index),(64*index,0))
            strip.paste(roles,(64*index,0))
            ginger.paste(striped,(64*index,0))
        calico.save(folder/f"calico-{state}.png")
        ginger.save(folder/f"orange-{state}.png")
        strip.save(folder/f"{state}.png")
