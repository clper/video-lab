"""《为什么没有绿色的恒星》太阳与大气镜头：s11、s19、s21、s25。

    s11  太阳亮起，温度数字滚到 5772，落进刚算出的区间
    s19  地面看：太阳是黄的（大气散射着色器，真实景深）
    s20  蓝光被散射铺满天空，剩下的阳光偏黄（这一段的解释）
    s21  大气层外：同一颗太阳是白的（太阳特写，和 s19 形成直接对比）
    s25  收尾：所有颜色一起照进眼睛，收束成白

s19 用 003 的大气散射着色器（真·瑞利散射，不是手工调色），
其余用 sun.frag。s19 → s21 是全片唯一的"同一事物两种样子"的对照，
所以 s21 必须明显比 s19 白，否则这一段白讲。文字一律 Pillow 叠加（这台机器的 ffmpeg drawtext 会崩）。

用法:
    uv run python videos/004-green-star/shader/render_sun.py
    uv run python videos/004-green-star/shader/render_sun.py --still
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
SCENES = {s["id"]: s for s in TL["scenes"]}
F_B, F_R = str(fonts.BOLD), str(fonts.REGULAR)   # 思源黑体，随仓库入库
INK, DIM, GOLD, GREEN = (241, 243, 250), (145, 153, 180), (255, 205, 100), (110, 230, 150)

SUN_T = 5772


@lru_cache(maxsize=32)
def font(path, size):
    return ImageFont.truetype(path, size)


def word_time(sid, text, nth=0):
    """词的开始时间（相对本镜头）。Edge TTS 分词和直觉不同，找不到报错并列出可用词。"""
    sc = SCENES[sid]
    hits = [w for w in sc["words"] if w["text"].strip() == text] or \
           [w for w in sc["words"] if text in w["text"]]
    if len(hits) <= nth:
        raise KeyError(f"{sid} 里没有第 {nth + 1} 个 {text!r}；可用：{[w['text'] for w in sc['words']]}")
    return hits[nth]["start"] - sc["start"]


def ease_out(x):
    return 1 - (1 - min(max(x, 0.0), 1.0)) ** 3


def fade(t, t0, dur=0.5):
    return ease_out((t - t0) / dur) if t >= t0 else 0.0


def label(d, xy, text, size, color, alpha, anchor="mm", bold=True):
    if alpha <= 0.01:
        return
    d.text(xy, text, font=font(F_B if bold else F_R, size),
           fill=tuple(int(v * alpha) for v in color), anchor=anchor)


# ── 文字层 ─────────────────────────────────────────────────────
def ov_s11(t, img):
    """温度数字滚到 5772，并标明它正好落在刚算出的区间里"""
    d = ImageDraw.Draw(img)
    t_num = word_time("s11_sun", "表面") - 0.15
    a = fade(t, t_num, 0.5)
    if a > 0.01:
        prog = ease_out((t - t_num) / 1.6)
        val = int(1000 + (SUN_T - 1000) * prog)
        label(d, (W * 0.72, H * 0.40), f"{val:,}", 122, GOLD, a)
        label(d, (W * 0.72, H * 0.545), "度", 44, DIM, a, bold=False)
    a2 = fade(t, word_time("s11_sun", "正好") - 0.2, 0.6)
    if a2 > 0.01:
        label(d, (W * 0.72, H * 0.68), "正好落在 5100 – 5800 之间", 38, GREEN, a2)
    label(d, (W * 0.16, H * 0.82), "太阳", 56, INK, fade(t, 0.3, 0.6))
    return img


def ov_s19(t, img):
    """地面看：太阳是黄的"""
    d = ImageDraw.Draw(img)
    a = fade(t, word_time("s19_yellow", "太阳") - 0.2, 0.6)
    label(d, (W / 2, H * 0.12), "可太阳明明是黄的", 60, INK, a)
    a2 = fade(t, word_time("s19_yellow", "哪里") - 0.2, 0.5)
    label(d, (W / 2, H * 0.88), "在地面上看", 38, DIM, a2, bold=False)
    return img


def ov_s20(t, img):
    """蓝光被散射到整个天空，所以天是蓝的，剩下的阳光偏黄"""
    d = ImageDraw.Draw(img)
    a = fade(t, word_time("s20_atmos", "大气", nth=1) - 0.2, 0.6)
    label(d, (W / 2, H * 0.10), "大气把一部分蓝光散射到整个天空", 50, INK, a)
    a2 = fade(t, word_time("s20_atmos", "蓝天") - 0.25, 0.6)
    label(d, (W * 0.22, H * 0.30), "这才有了蓝天", 44, (150, 200, 255), a2)
    a3 = fade(t, word_time("s20_atmos", "偏黄") - 0.3, 0.6)
    label(d, (W * 0.76, H * 0.80), "剩下的阳光偏黄", 44, (255, 215, 130), a3)
    return img


def ov_s21(t, img):
    """升出大气层：太阳恢复白色"""
    d = ImageDraw.Draw(img)
    a = fade(t, word_time("s21_space", "外面") - 0.2, 0.6)
    label(d, (W / 2, H * 0.12), "在大气层外面看", 58, INK, a)
    a2 = fade(t, word_time("s21_space", "白") - 0.2, 0.6)
    label(d, (W / 2, H * 0.86), "太阳是白的", 64, GOLD, a2)
    return img


def ov_s25(t, img):
    """收尾：所有颜色一起照进眼睛，叫白色"""
    d = ImageDraw.Draw(img)
    a = fade(t, word_time("s25_white", "一直都在") - 0.4, 0.7)
    label(d, (W / 2, H * 0.13), "绿色的恒星一直都在", 60, GREEN, a)
    a2 = fade(t, word_time("s25_white", "太阳") - 0.2, 0.6)
    label(d, (W / 2, H * 0.215), "太阳就是一颗", 42, INK, a2)
    a3 = fade(t, word_time("s25_white", "白色") - 0.35, 0.8)
    label(d, (W / 2, H * 0.85), "你给这个颜色起了另一个名字", 40, DIM, a3 * 0.9, bold=False)
    label(d, (W / 2, H * 0.93), "白　色", 72, INK, a3)
    return img


# 镜头表：(着色器, 文字层, uniform 函数)
def sun_uni(**over):
    def f(t, dur):
        u = dict(uTemp=SUN_T, uRadius=0.26, uGround=0.0, uGlow=0.55, uBright=1.0,
                 uGreenRing=0.0, uCenter=(0.0, 0.0))
        for k, v in over.items():
            u[k] = v(t, dur) if callable(v) else v
        return u
    return f


SHOTS = {
    "s11_sun":   ("sun", ov_s11, sun_uni(uRadius=0.20, uCenter=(-0.34, 0.0),
                                         uBright=lambda t, d: min(1.0, ease_out(t / 0.8)),
                                         uGlow=lambda t, d: 0.32 + 0.22 * min(1.0, t / d),
                                         uGreenRing=lambda t, d: 0.55 * fade(t, word_time("s11_sun", "正好") - 0.2, 0.8))),
    "s19_yellow": ("atmo", ov_s19, lambda t, d: dict(uSunElev=0.22, uSunAzim=0.0, uPitch=0.12,
                                                     uExposure=1.0, uCloudCover=0.18)),
    # 从"地面那种黄"过渡到"大气外的白"，这是这一段的全部意义
    # 镜头从贴近地平线缓慢抬起，蓝天的范围随之铺开（散射本身由着色器算）
    "s20_atmos": ("atmo", ov_s20, lambda t, d: dict(uSunElev=0.20 + 0.10 * ease_out(t / d),
                                                    uSunAzim=0.0, uPitch=0.10 + 0.22 * ease_out(t / d),
                                                    uExposure=1.0, uCloudCover=0.14)),
    "s21_space": ("sun", ov_s21, sun_uni(uRadius=0.19, uGlow=0.45, uCenter=(0.0, -0.02),
                                         uGround=lambda t, d: max(0.0, 1.0 - ease_out(t / (d * 0.5))))),
    # 结尾缓慢变亮，但不能过曝成一片灰白，字还要看得清
    "s25_white": ("sun", ov_s25, sun_uni(uRadius=lambda t, d: 0.17 + 0.05 * ease_out(t / d),
                                         uGlow=lambda t, d: 0.40 + 0.25 * ease_out(t / d), uCenter=(0.0, -0.03),
                                         uBright=lambda t, d: 1.0 + 0.10 * ease_out(max(0.0, (t - d * 0.65) / (d * 0.35))))),
}


def render(sid, renderers, out_dir):
    sc = SCENES[sid]
    dur = sc["end"] - sc["start"]
    n = round(sc["end"] * FPS) - round(sc["start"] * FPS)
    kind, ov, uni = SHOTS[sid]
    r = renderers[kind]
    out = out_dir / f"{sid}.mp4"
    enc = open_encoder(out, fps=FPS, size=(W, H))
    for i in range(n):
        t = i / FPS
        img = Image.fromarray(r.frame(t, **uni(t, dur)))
        enc.stdin.write(np.asarray(ov(t, img)).tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"  {sid}  {n} 帧  {dur:.2f}s  → {out.name}")


def main():
    still = "--still" in sys.argv
    ss = 1 if still else 2
    renderers = {"sun": ShaderRenderer(SHADERS / "sun.frag", ss=ss, size=(W, H)),
                 "atmo": ShaderRenderer(SHADERS / "atmosphere.frag", ss=ss, size=(W, H))}
    if still:
        sheet = Image.new("RGB", (W, H // 2 * len(SHOTS)))
        for i, sid in enumerate(SHOTS):
            sc = SCENES[sid]
            dur = sc["end"] - sc["start"]
            t = dur * (0.95 if sid == "s21_space" else 0.75)
            kind, ov, uni = SHOTS[sid]
            img = ov(t, Image.fromarray(renderers[kind].frame(t, **uni(t, dur))))
            sheet.paste(img.resize((W, H // 2), Image.LANCZOS), (0, H // 2 * i))
        p = HERE / "still_sun.png"
        sheet.save(p)
        print("自检图 →", p)
        return
    out_dir = PROJ / "media" / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"太阳与大气镜头 {W}x{H}:")
    for sid in SHOTS:
        render(sid, renderers, out_dir)


if __name__ == "__main__":
    main()
