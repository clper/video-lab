"""《为什么没有绿色的恒星》文字动效镜头：s13「可太阳看起来，一点也不绿」。

这是全片的转折点：前面刚算出太阳的峰值在绿色，这里一句话推翻直觉。
用故障效果（RGB 分离 + 横向切片抖动）做"认知被打断"的感觉。

用法:
    uv run python archive/004-green-star/kinetic/render_glitch.py
    uv run python archive/004-green-star/kinetic/render_glitch.py --still
"""

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vlab import fonts
from vlab.render.glsl import open_encoder

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
TL = json.loads((PROJ / "build" / "green-star" / "timeline.json").read_text(encoding="utf-8"))
W, H, FPS = TL["width"], TL["height"], TL["fps"]
SCENES = {s["id"]: s for s in TL["scenes"]}
SID = "s13_notgreen"
F_B, F_R = str(fonts.BOLD), str(fonts.REGULAR)   # 思源黑体，随仓库入库
BG = (10, 13, 24)
INK, DIM, GREEN = (241, 243, 250), (145, 153, 180), (110, 230, 150)


@lru_cache(maxsize=16)
def font(path, size):
    return ImageFont.truetype(path, size)


def word_time(text, nth=0):
    sc = SCENES[SID]
    hits = [w for w in sc["words"] if w["text"].strip() == text] or \
           [w for w in sc["words"] if text in w["text"]]
    if len(hits) <= nth:
        raise KeyError(f"{SID} 里没有 {text!r}；可用：{[w['text'] for w in sc['words']]}")
    return hits[nth]["start"] - sc["start"]


def ease_out(x):
    return 1 - (1 - min(max(x, 0.0), 1.0)) ** 3


def glitch(img, amount, seed):
    """故障：RGB 三通道错开 + 几条横向切片左右抖动。amount 0..1"""
    if amount <= 0.01:
        return img
    a = np.asarray(img).astype(np.int16)
    rng = np.random.default_rng(seed)
    out = a.copy()
    # RGB 分离
    sx = int(round(16 * amount))
    if sx:
        out[:, :, 0] = np.roll(a[:, :, 0], sx, axis=1)
        out[:, :, 2] = np.roll(a[:, :, 2], -sx, axis=1)
    # 横向切片抖动
    for _ in range(int(7 * amount) + 1):
        y0 = rng.integers(0, H - 1)
        h = int(rng.integers(6, 46))
        y1 = min(H, y0 + h)
        shift = int(rng.integers(-70, 70) * amount)
        out[y0:y1] = np.roll(out[y0:y1], shift, axis=1)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def frame(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 上半：刚得出的结论（会被推翻）
    a1 = ease_out(t / 0.7)
    if a1 > 0.01:
        d.text((W / 2, H * 0.30), "太阳发光最强的波长，就在绿色",
               font=font(F_R, 48), fill=tuple(int(v * a1 * 0.75) for v in DIM), anchor="mm")

    # 下半：转折
    t_turn = word_time("可") if any(w["text"].strip() == "可" for w in SCENES[SID]["words"]) else 0.6
    a2 = ease_out((t - t_turn) / 0.5) if t >= t_turn else 0.0
    if a2 > 0.01:
        d.text((W / 2, H * 0.52), "可太阳看起来",
               font=font(F_B, 72), fill=tuple(int(v * a2) for v in INK), anchor="mm")

    t_hit = word_time("一点")
    a3 = ease_out((t - t_hit) / 0.35) if t >= t_hit else 0.0
    if a3 > 0.01:
        d.text((W / 2, H * 0.68), "一点也不绿",
               font=font(F_B, 104), fill=tuple(int(v * a3) for v in GREEN), anchor="mm")

    # 故障只在"一点也不绿"砸下来的瞬间最强，然后迅速收住
    g = 0.0
    if t >= t_hit:
        g = max(0.0, 1.0 - (t - t_hit) / 0.55)
    return glitch(img, g, seed=int(t * FPS))


def main():
    sc = SCENES[SID]
    dur = sc["end"] - sc["start"]
    if "--still" in sys.argv:
        t_hit = word_time("一点")
        sheet = Image.new("RGB", (W, H // 2 * 3))
        for i, t in enumerate((0.8, t_hit + 0.08, dur - 0.3)):
            sheet.paste(frame(t, dur).resize((W, H // 2), Image.LANCZOS), (0, H // 2 * i))
        p = HERE / "still_glitch.png"
        sheet.save(p)
        print("自检图 →", p)
        return
    out_dir = PROJ / "media" / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{SID}.mp4"
    n = round(sc["end"] * FPS) - round(sc["start"] * FPS)
    enc = open_encoder(out, fps=FPS, size=(W, H))
    for i in range(n):
        enc.stdin.write(np.asarray(frame(i / FPS, dur)).tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"  {SID}  {n} 帧  {dur:.2f}s  → {out.name}")


if __name__ == "__main__":
    main()
