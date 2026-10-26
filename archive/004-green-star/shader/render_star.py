"""《为什么没有绿色的恒星》星空镜头：s01、s02、s24、s26。

这四镜共用一个着色器，靠 uniform 控制漂移、推进、压暗和那颗"想亮起来的绿星"。
文字用 Pillow 叠在每帧上（这台机器的 ffmpeg drawtext 会崩）。

用法:
    uv run python archive/004-green-star/shader/render_star.py          # 渲染四个镜头
    uv run python archive/004-green-star/shader/render_star.py --still  # 只出自检图
"""

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vlab import fonts
from vlab.render.glsl import ShaderRenderer, open_encoder
from vlab.scenes import SHADERS

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
TL = json.loads((PROJ / "build" / "green-star" / "timeline.json").read_text(encoding="utf-8"))
W, H, FPS = TL["width"], TL["height"], TL["fps"]
F_B, F_R = str(fonts.BOLD), str(fonts.REGULAR)   # 思源黑体，随仓库入库
INK, DIM, GOLD = (238, 240, 250), (150, 156, 178), (255, 205, 100)

SCENES = {s["id"]: s for s in TL["scenes"]}


@lru_cache(maxsize=32)
def font(path, size):
    return ImageFont.truetype(path, size)


def word_time(sid, word, nth=0):
    """取某个词的开始时间（相对本镜头）。画面跟着配音走，不写死秒数。

    Edge TTS 的分词和直觉不同（"一颗"会切成 "一" / "颗"），所以绑定的词
    必须是 timeline.json 里真实存在的词；找不到时直接报错并列出可用的词。
    """
    sc = SCENES[sid]
    hits = [w for w in sc["words"] if word in w["text"]]
    if len(hits) <= nth:
        raise KeyError(f"{sid} 里没有第 {nth + 1} 个 {word!r}；可用：{[w['text'] for w in sc['words']]}")
    return hits[nth]["start"] - sc["start"]


def ease_out(x):
    return 1 - (1 - min(max(x, 0.0), 1.0)) ** 3


def fade(t, t0, dur=0.5):
    return ease_out((t - t0) / dur) if t >= t0 else 0.0


def label(d, xy, text, size, color, alpha, anchor="mm", bold=True):
    if alpha <= 0.01:
        return
    c = tuple(int(v * alpha) for v in color)
    d.text(xy, text, font=font(F_B if bold else F_R, size), fill=c, anchor=anchor)


# ── 各镜头的文字层 ────────────────────────────────────────────────
def overlay_s01(t, img):
    """三颗星依次标注：参宿四（红）、参宿七（蓝白）、天狼星（白）"""
    d = ImageDraw.Draw(img)
    stars = [("参宿四", "约 3600 度", (255, 150, 110), 0.30, 0.34, "红"),
             ("参宿七", "约 12100 度", (170, 200, 255), 0.56, 0.60, "蓝白"),
             ("天狼星", "约 9900 度", (235, 240, 255), 0.78, 0.26, "白")]
    for i, (name, temp, col, fx, fy, kind) in enumerate(stars):
        a = fade(t, word_time("s01_sky", ["红色", "蓝色", "白色"][i]) - 0.15, 0.45)
        if a <= 0.01:
            continue
        x, y = fx * W, fy * H
        r_in, r_out = 8, 20
        d.ellipse([x - r_out, y - r_out, x + r_out, y + r_out],
                  fill=tuple(int(c * a * 0.22) for c in col))      # 柔光晕
        d.ellipse([x - r_in, y - r_in, x + r_in, y + r_in], fill=tuple(int(c * a) for c in col))
        label(d, (x, y - 42), name, 38, INK, a)
        label(d, (x, y + 40), f"{kind} · {temp}", 26, DIM, a * 0.9, bold=False)
    return img


def green_try(t, dur):
    """绿星的亮度：亮起来一下，然后熄灭。标签跟着它走，不能它灭了标签还亮着。"""
    return max(0.0, float(np.sin(np.pi * min(1.0, t / (dur * 0.5))) ** 0.7))


def overlay_s02(t, img):
    """绿星想亮起来又熄灭，最后留下一行结论"""
    d = ImageDraw.Draw(img)
    sc = SCENES["s02_nogreen"]
    g = green_try(t, sc["end"] - sc["start"])
    a = fade(t, word_time("s02_nogreen", "绿色") - 0.1, 0.4) * g
    if a > 0.01:
        label(d, (W * 0.61, H * 0.40 - 46), "绿色？", 36, (140, 240, 160), a)
    a2 = fade(t, word_time("s02_nogreen", "稀少") - 0.1, 0.6)
    if a2 > 0.01:
        label(d, (W / 2, H * 0.80), "没有绿色的恒星", 72, INK, a2)
    return img


def overlay_s24(t, img):
    d = ImageDraw.Draw(img)
    a = fade(t, 0.3, 0.6)
    label(d, (W / 2, H * 0.40), "为什么没有绿色的恒星？", 62, INK, a * 0.85)
    a2 = fade(t, word_time("s24_rethink", "问错") - 0.15, 0.5)
    if a2 > 0.01:
        label(d, (W / 2, H * 0.58), "这个问题，问错了", 76, GOLD, a2)
    return img


def overlay_s26(t, img):
    d = ImageDraw.Draw(img)
    sc = SCENES["s26_outro"]
    dur = sc["end"] - sc["start"]
    a = fade(t, word_time("s26_outro", "白色") - 0.2, 0.6)
    a2 = fade(t, word_time("s26_outro", "绿色") - 0.2, 0.6)
    label(d, (W / 2, H * 0.44), "每一颗白色的星", 58, INK, a)
    label(d, (W / 2, H * 0.56), "都可能是一颗「绿色」的恒星", 58, GOLD, a2)
    end = fade(t, dur - 2.6, 0.7)
    if end > 0.01:
        label(d, (W / 2, H * 0.82), "「为什么」· 日常科学", 34, DIM, end * 0.9, bold=False)
    return img


SHOTS = {
    "s01_sky":     (overlay_s01, lambda t, d: dict(uDrift=0.010, uZoom=1.0 - 0.02 * t / d, uDim=0.0, uGreenTry=0.0, uTwinkle=1.0)),
    "s02_nogreen": (overlay_s02, lambda t, d: dict(uDrift=0.010, uZoom=0.98, uDim=0.45 * ease_out((t - d * 0.55) / 1.2) if t > d * 0.55 else 0.0,
                                                   uGreenTry=green_try(t, d), uTwinkle=1.0)),
    "s24_rethink": (overlay_s24, lambda t, d: dict(uDrift=0.008, uZoom=1.02, uDim=0.25, uGreenTry=0.0, uTwinkle=0.8)),
    "s26_outro":   (overlay_s26, lambda t, d: dict(uDrift=0.006, uZoom=1.0 + 0.10 * t / d, uDim=0.0, uGreenTry=0.0, uTwinkle=1.0)),
}


def render(sid, renderer, out_dir):
    sc = SCENES[sid]
    dur = sc["end"] - sc["start"]
    n = round(sc["end"] * FPS) - round(sc["start"] * FPS)
    ov, uni = SHOTS[sid]
    out = out_dir / f"{sid}.mp4"
    enc = open_encoder(out, fps=FPS, size=(W, H))
    for i in range(n):
        t = i / FPS
        img = Image.fromarray(renderer.frame(t, **uni(t, dur)))
        enc.stdin.write(np.asarray(ov(t, img)).tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"  {sid}  {n} 帧  {dur:.2f}s  → {out.name}")


def main():
    still = "--still" in sys.argv
    out_dir = PROJ / "media" / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    r = ShaderRenderer(SHADERS / "starfield.frag", ss=2 if not still else 1, size=(W, H))
    if still:
        sheet = Image.new("RGB", (W, H // 2 * len(SHOTS)))
        for i, sid in enumerate(SHOTS):
            sc = SCENES[sid]
            dur = sc["end"] - sc["start"]
            t = dur * 0.75
            ov, uni = SHOTS[sid]
            img = ov(t, Image.fromarray(r.frame(t, **uni(t, dur))))
            sheet.paste(img.resize((W, H // 2), Image.LANCZOS), (0, H // 2 * i))
        p = HERE / "still_star.png"
        sheet.save(p)
        print("自检图 →", p)
        return
    print(f"星空镜头 {W}x{H}:")
    for sid in SHOTS:
        render(sid, r, out_dir)


if __name__ == "__main__":
    main()
