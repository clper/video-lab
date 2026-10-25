"""做法①：Pillow 画图文卡片 + FFmpeg 拼接（最简单、最容易批量）。

每个分镜画成几张静态卡片：念到关键词就切到下一张（多出一个元素，像 PPT 逐条出现），
卡片之间用 FFmpeg 的 xfade 过渡，最后交给 shared/finalize.py 合配音、烧字幕。

用法:  uv run python 1_cards/render.py build/hexagon
产物:  build/hexagon/cards/*.png，out/hexagon_1_cards.mp4
"""

import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared"))
from finalize import finalize  # noqa: E402

W, H, SS = 1080, 1920, 2  # 先按 2 倍尺寸画，再缩小，边缘更平滑
BG, PANEL = (21, 17, 14), (38, 29, 20)
AMBER, CREAM, MUTED = (245, 165, 36), (255, 244, 224), (184, 168, 144)
TRI, SQU, HEX = (108, 140, 255), (52, 195, 160), AMBER
FONT_BOLD, FONT_REG = "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"
SCENE_FADE, BEAT_FADE = 0.4, 0.25  # 换分镜 / 分镜内逐条出现 的过渡时长
EARLY = 0.1  # 比念到关键词稍早一点切，看起来更跟嘴


# ---------- 画图小工具（坐标都按 1080×1920 写，内部乘 SS） ----------

def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size * SS)


def canvas():
    img = Image.new("RGB", (W * SS, H * SS), BG)
    glow = ImageOps.invert(Image.radial_gradient("L")).resize((1500 * SS, 1500 * SS))
    img.paste((74, 48, 20), ((W - 1500) // 2 * SS, (880 - 750) * SS), glow.point(lambda v: int(v * 0.35)))
    return img, ImageDraw.Draw(img)


def mix(color, amount, base=BG):
    return tuple(round(b + (c - b) * amount) for c, b in zip(color, base))


def text_c(d, y, s, size, color, bold=True, x=W / 2):
    """以 x 为中心、y 为字顶写一行字。"""
    f = font(size, bold)
    left, top, right, _ = d.textbbox((0, 0), s, font=f)
    d.text((x * SS - (right - left) / 2 - left, y * SS - top), s, font=f, fill=color)


def headline(d, s, size=80):
    fits = lambda n: d.textlength(s, font=font(n)) <= (W - 160) * SS  # noqa: E731
    if fits(size):
        lines = [s]
    elif fits(72):  # 只超一点：缩一档字号，保持一行
        size, lines = 72, [s]
    else:
        lines = s.split("，", 1)
    for i, line in enumerate(lines):
        text_c(d, 260 + i * (size + 26), line, size, CREAM)
    bar_y = 260 + len(lines) * (size + 26) + 14
    d.rounded_rectangle(((W / 2 - 60) * SS, bar_y * SS, (W / 2 + 60) * SS, (bar_y + 8) * SS), 4 * SS, fill=AMBER)


def poly(cx, cy, r, n, rot=0.0):
    return [((cx + r * math.cos(rot + 2 * math.pi * i / n)) * SS, (cy + r * math.sin(rot + 2 * math.pi * i / n)) * SS) for i in range(n)]


def shape(d, kind, cx, cy, r, color, fill=0.28, width=6):
    n, rot = {"tri": (3, -math.pi / 2), "sq": (4, math.pi / 4), "hex": (6, 0.0)}[kind]
    d.polygon(poly(cx, cy, r, n, rot), fill=mix(color, fill), outline=color, width=width * SS)


HEX_CELLS = sorted(
    [(q, r) for q in range(-2, 3) for r in range(max(-2, -q - 2), min(2, -q + 2) + 1)],
    key=lambda c: (abs(c[0]) + abs(c[1]) + abs(c[0] + c[1]), c),
)  # 19 个格子，由内到外


def honeycomb(d, cx, cy, s, filled):
    for i, (q, r) in enumerate(HEX_CELLS):
        x, y = cx + s * 1.5 * q, cy + s * math.sqrt(3) * (r + q / 2)
        if i in filled:
            fill = AMBER if i % 3 else (230, 145, 25)
            d.polygon(poly(x, y, s * 0.9, 6), fill=fill, outline=(255, 205, 110), width=4 * SS)
        else:
            d.polygon(poly(x, y, s * 0.9, 6), fill=PANEL, outline=AMBER, width=5 * SS)


def tiling_window(img, kind, color, cx, cy, dia=290):
    """一个圆形小窗，里面是无限密铺的一角。"""
    size = dia * SS
    layer = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(layer)
    if kind == "tri":
        a, h = 92, 92 * math.sqrt(3) / 2
        for j in range(-1, 5):
            for k in range(-2, 9):
                left, top, bottom = k * a / 2 - 20, j * h, (j + 1) * h
                up = (k + j) % 2 == 0
                pts = [(left, bottom), (left + a, bottom), (left + a / 2, top)] if up else [(left, top), (left + a, top), (left + a / 2, bottom)]
                d.polygon([(x * SS, y * SS) for x, y in pts], fill=mix(color, 0.32 if up else 0.18), outline=color, width=4 * SS)
    elif kind == "sq":
        a = 80
        for j in range(-1, 5):
            for k in range(-1, 5):
                x, y = k * a - 15, j * a - 15
                d.rectangle((x * SS, y * SS, (x + a) * SS, (y + a) * SS), fill=mix(color, 0.32 if (j + k) % 2 else 0.18), outline=color, width=4 * SS)
    else:
        s = 50
        for q in range(-4, 5):
            for r in range(-5, 6):
                x, y = dia / 2 + s * 1.5 * q, dia / 2 + s * math.sqrt(3) * (r + q / 2)
                if abs(x - dia / 2) < dia / 2 + s and abs(y - dia / 2) < dia / 2 + s:
                    d.polygon(poly(x, y, s, 6), fill=mix(color, 0.32 if (q + 2 * r) % 3 else 0.18), outline=color, width=4 * SS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    img.paste(layer, (int((cx - dia / 2) * SS), int((cy - dia / 2) * SS)), mask)
    ImageDraw.Draw(img).ellipse(((cx - dia / 2) * SS, (cy - dia / 2) * SS, (cx + dia / 2) * SS, (cy + dia / 2) * SS), outline=color, width=5 * SS)


# ---------- 每个分镜：关键词列表 + 第 step 张卡片怎么画 ----------
# step=0 是分镜刚切进来时的样子，之后每念到一个关键词就多画一点

COLS = (220, 540, 860)


def draw_hook(img, d, step, scene):
    headline(d, scene["headline"])
    honeycomb(d, W / 2, 890, 85, filled={0, 2, 3, 5, 8, 11, 14})


def draw_tiling(img, d, step, scene):
    headline(d, scene["headline"])
    for i, (kind, color, label) in enumerate([("tri", TRI, "三角形"), ("sq", SQU, "正方形"), ("hex", HEX, "正六边形")]):
        if step > i:
            tiling_window(img, kind, color, COLS[i], 820)
            text_c(d, 1000, label, 46, color, x=COLS[i])
        else:
            d.ellipse(((COLS[i] - 145) * SS, 675 * SS, (COLS[i] + 145) * SS, 965 * SS), outline=mix(MUTED, 0.35), width=3 * SS)


def draw_question(img, d, step, scene):
    headline(d, scene["headline"])
    k = 180  # 面积相同：外接圆半径按 0.8774 / 0.7071 / 0.6204 缩放
    for x, (kind, color, ratio) in zip(COLS, [("tri", TRI, 0.8774), ("sq", SQU, 0.7071), ("hex", HEX, 0.6204)]):
        shape(d, kind, x, 800, k * ratio, color)
        text_c(d, 990, "面积 = 1", 40, MUTED, bold=False, x=x)
    if step >= 1:
        text_c(d, 1070, "?", 190, AMBER)


def draw_perimeter(img, d, step, scene):
    headline(d, scene["headline"])
    rows = [("三角形", TRI), ("正方形", SQU), ("正六边形", HEX)]
    for i, ((label, color), item) in enumerate(zip(rows, scene["data"])):
        y = 640 + i * 190
        text_c(d, y - 30, label, 46, color, x=176)
        d.rounded_rectangle((290 * SS, (y - 35) * SS, 810 * SS, (y + 35) * SS), 14 * SS, fill=PANEL)
        if step > i:
            end = 290 + 520 * item["value"] / 4.56
            d.rounded_rectangle((290 * SS, (y - 35) * SS, end * SS, (y + 35) * SS), 14 * SS, fill=color)
            f = font(58)
            d.text(((end + 22) * SS, y * SS), f"{item['value']:.2f}", font=f, fill=CREAM, anchor="lm")
            if i == 2:
                d.rounded_rectangle((890 * SS, (y - 26) * SS, 1000 * SS, (y + 26) * SS), 26 * SS, fill=AMBER)
                text_c(d, y - 19, "最短", 34, BG, x=945)


def draw_wax(img, d, step, scene):
    headline(d, scene["headline"])
    if step == 0:
        shape(d, "hex", W / 2, 880, 260, AMBER, fill=0.12, width=8)
    for i, item in enumerate(scene["data"]):
        if step > i:
            y = 560 + i * 380
            text_c(d, y, item["label"], 54, MUTED, bold=False)
            text_c(d, y + 90, item["value"].replace("-", "−"), 200, AMBER)


def draw_proof(img, d, step, scene):
    headline(d, scene["headline"])
    info = scene["data"]
    text_c(d, 560, info["year"], 240, AMBER)  # 一开口就念"1999"，所以年份直接放在第一张
    if step >= 1:
        name, en = info["person"].rstrip("）").split("（")
        text_c(d, 870, name, 62, CREAM)
        text_c(d, 955, en, 44, MUTED, bold=False)
    if step >= 2:
        d.rounded_rectangle((100 * SS, 1050 * SS, 980 * SS, 1250 * SS), 28 * SS, fill=PANEL, outline=AMBER, width=4 * SS)
        first, second = info["claim"].split("，")
        text_c(d, 1085, first, 50, CREAM)
        text_c(d, 1160, second, 50, AMBER)


def draw_outro(img, d, step, scene):
    headline(d, scene["headline"])
    honeycomb(d, W / 2, 890, 85, filled=set(range([0, 7, 19][step])))


SCENES = {
    "hook": (draw_hook, []),
    "tiling": (draw_tiling, ["三角形", "正方形", "六边形"]),
    "question": (draw_question, ["谁"]),
    "perimeter": (draw_perimeter, ["4.56", "4", "3.72"]),
    "wax": (draw_wax, ["7%", "18%"]),
    "proof": (draw_proof, ["托马斯", "把"]),
    "outro": (draw_outro, ["最少", "最大"]),
}


def word_time(scene, keyword):
    words = scene["words"]
    hit = next((w for w in words if w["text"] == keyword), None) or next(w for w in words if keyword in w["text"])
    return hit["start"]


# ---------- 拼成视频 ----------

def render_cards(timeline, card_dir):
    """画出所有卡片，返回 [(开始时间, 文件名, 过渡方式, 过渡时长)]。"""
    card_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for i, scene in enumerate(timeline["scenes"]):
        draw, keywords = SCENES[scene["id"]]
        times = [scene["start"]] + [word_time(scene, k) - EARLY for k in keywords]
        for step, t in enumerate(times):
            img, d = canvas()
            draw(img, d, step, scene)
            name = f"{i:02d}_{scene['id']}_{step}.png"
            img.resize((W, H), Image.LANCZOS).save(card_dir / name)
            cards.append((t, name, "smoothleft" if step == 0 else "fade", SCENE_FADE if step == 0 else BEAT_FADE))
    return cards


def cards_to_video(cards, total, card_dir, out):
    """每张卡片是一段静止画面，相邻两段用 xfade 叠化；第 k 段从它的开始时间起播。"""
    inputs, filters = [], []
    for k, (t, name, _, _) in enumerate(cards):
        nxt = cards[k + 1] if k + 1 < len(cards) else (total, None, None, 0)
        length = nxt[0] + nxt[3] - t  # 要撑到下一段过渡结束
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{length:.3f}", "-i", name]
        filters.append(f"[{k}:v]fps=30,format=yuv420p,settb=AVTB[c{k}]")
    last = "c0"
    for k, (t, _, kind, fade) in enumerate(cards[1:], 1):
        filters.append(f"[{last}][c{k}]xfade=transition={kind}:duration={fade}:offset={t:.3f}[x{k}]")
        last = f"x{k}"
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters), "-map", f"[{last}]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-t", f"{total:.3f}", str(out.resolve())]
    subprocess.run(cmd, check=True, cwd=card_dir)


def main(build_dir: Path) -> None:
    timeline = json.loads((build_dir / "timeline.json").read_text(encoding="utf-8"))
    card_dir = build_dir / "cards"
    cards = render_cards(timeline, card_dir)
    print(f"画了 {len(cards)} 张卡片 → {card_dir}")
    silent = build_dir / "1_cards_silent.mp4"
    cards_to_video(cards, timeline["duration"], card_dir, silent)
    finalize(silent, build_dir, ROOT / "out" / f"{timeline['id']}_1_cards.mp4")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
