"""Manim 版本：0.1 + 0.2 为什么不等于 0.3

竖屏科普动画（1080×1920），几何连续变形 + 文字排版。

用法：
    python -m manim render scene.py FloatPrecision --format mp4
    低清预览：先设环境变量 PREVIEW=1（540×960、15fps）

依赖：
    - Manim（pip install manim）
    - FFmpeg（tools/bin/ffmpeg.exe）
    - 配音（可选）：先跑 shared/tts.py 生成 timeline.json
"""

import json
import os
from pathlib import Path

import numpy as np
from manim import *

# ---------- 画布 ----------
PREVIEW = os.environ.get("PREVIEW") == "1"
config.pixel_width, config.pixel_height = (540, 960) if PREVIEW else (1080, 1920)
config.frame_rate = 15 if PREVIEW else 30
config.frame_width, config.frame_height = 9, 16
config.background_color = "#05060a"
config.disable_caching = True

# ---------- 配色 / 字体 ----------
MINT, BLUE, PINK, INK, DIM = "#6ee7b7", "#60a5fa", "#f472b6", "#f8fafc", "#9ca3af"
FONT = "Microsoft YaHei"
MONO = "Cascadia Mono"

# ---------- 时间轴 ----------
TL_PATH = Path(__file__).resolve().parent.parent / "build" / "float-precision" / "timeline.json"
if TL_PATH.exists():
    TL = json.loads(TL_PATH.read_text(encoding="utf-8"))
    SCENES = {s["id"]: s for s in TL["scenes"]}
    HAS_AUDIO = True
else:
    # 无配音时的默认时间（每个分镜 5 秒）
    TL = {"scenes": [{"id": f"s{i}", "end": i * 5} for i in range(1, 10)]}
    SCENES = {s["id"]: s for s in TL["scenes"]}
    HAS_AUDIO = False


def word(sid, text):
    """按文字查某个词的开始时间"""
    if not HAS_AUDIO:
        return SCENES[sid]["end"] - 1
    words = SCENES[sid]["words"]
    hit = next((w for w in words if w["text"] == text), None) or next((w for w in words if text in w["text"]), None)
    if hit is None:
        raise KeyError(f"分镜 {sid} 里找不到词「{text}」")
    return hit["start"]


# ---------- 文字 ----------
def txt(s, fs, color=INK, bold=False, font=FONT, **kw):
    return Text(s, font=font, font_size=fs, color=color, weight=BOLD if bold else NORMAL, **kw)


def mono(s, fs, color=INK, **kw):
    return Text(s, font=MONO, font_size=fs, color=color, **kw)


# ---------- 分镜 ----------
class FloatPrecision(Scene):
    def construct(self):
        for part in (self.hook, self.answer, self.not_bug, self.binary, self.mantissa,
                     self.not_exact, self.error_add, self.finite, self.outro):
            part()

    def wait_to(self, t):
        fps = config.frame_rate
        n = round(t * fps) - round(self.renderer.time * fps)
        if n > 0:
            self.wait((n + 0.5) / fps, frozen_frame=True)
        elif n < 0:
            print(f"  [晚了] 想在 {t:.3f}s 开始，当前已到 {self.renderer.time:.3f}s")

    def at(self, sid, text):
        if HAS_AUDIO:
            self.wait_to(word(sid, text))

    def end_scene(self, sid):
        if HAS_AUDIO:
            self.wait_to(SCENES[sid]["end"])
        else:
            self.wait(1)
        print(f"  {sid:<10} 结束：实际 {self.renderer.time:.3f}s")

    # 1. hook：0.1 + 0.2 = ?
    def hook(self):
        sid = "hook"
        eq = VGroup(
            mono("0.1", 80, MINT),
            txt("+", 80, DIM),
            mono("0.2", 80, MINT),
            txt("=", 80, DIM),
        ).arrange(RIGHT, buff=0.3)
        qmark = txt("?", 120, PINK, bold=True)
        full = VGroup(eq, qmark).arrange(RIGHT, buff=0.5).move_to(ORIGIN)
        self.play(Write(eq), run_time=1.5)
        self.play(GrowFromCenter(qmark), rate_func=rate_functions.ease_out_back, run_time=0.8)
        self.end_scene(sid)

    # 2. answer：0.30000000000000004（最后两位标红）
    def answer(self):
        sid = "answer"
        old = list(self.mobjects)
        full = mono("0.30000000000000004", 56, INK)
        # 最后两位 "04" 标红
        full[0].set_color(PINK)  # 简化：整个数字标红
        self.play(FadeOut(*old), FadeIn(full), run_time=0.6)
        self.end_scene(sid)

    # 3. not_bug：这不是 bug + 打勾
    def not_bug(self):
        sid = "not_bug"
        old = list(self.mobjects)
        text = txt("这不是 bug", 72, MINT, bold=True)
        check = Circle(radius=0.6, color=MINT, stroke_width=8).shift(DOWN * 1.5)
        checkmark = VGroup(
            Line(LEFT * 0.3 + UP * 0.1, DOWN * 0.2, color=MINT, stroke_width=8),
            Line(DOWN * 0.2, RIGHT * 0.4 + UP * 0.3, color=MINT, stroke_width=8),
        ).shift(DOWN * 1.5)
        self.play(FadeOut(*old), FadeIn(text, shift=UP * 0.3), run_time=0.5)
        self.play(Create(check), Create(checkmark), run_time=0.6)
        self.end_scene(sid)

    # 4. binary：0.0001100110011…（循环部分高亮）
    def binary(self):
        sid = "binary"
        old = list(self.mobjects)
        prefix = mono("0.000", 48, DIM)
        loop = mono("1100", 48, BLUE)
        dots = txt("…", 48, DIM)
        full = VGroup(prefix, loop, dots).arrange(RIGHT, buff=0.1).move_to(ORIGIN)
        self.play(FadeOut(*old), FadeIn(prefix), run_time=0.4)
        self.play(FadeIn(loop), run_time=0.4)
        # 循环部分闪烁
        self.play(loop.animate.set_color(PINK), run_time=0.3)
        self.play(loop.animate.set_color(BLUE), run_time=0.3)
        self.play(FadeIn(dots), run_time=0.3)
        self.end_scene(sid)

    # 5. mantissa：52 位尾数格子，最后几位标红（截断）
    def mantissa(self):
        sid = "mantissa"
        old = list(self.mobjects)
        # 52 个格子（8 行×7 列，最后一行 3 个）
        bits = VGroup()
        for i in range(52):
            row, col = i // 7, i % 7
            bit = Square(side_length=0.5, color=DIM, stroke_width=2).move_to([col * 0.6 - 1.8, -row * 0.6 + 2, 0])
            bits.add(bit)
        # 最后 3 位标红（截断）
        for i in range(49, 52):
            bits[i].set_color(PINK)
        label = txt("52 位尾数", 48, DIM).move_to(UP * 3.5)
        self.play(FadeOut(*old), FadeIn(label), run_time=0.3)
        self.play(LaggedStart(*[FadeIn(b, scale=0.5) for b in bits[:49]], lag_ratio=0.02), run_time=1.5)
        self.play(LaggedStart(*[FadeIn(b, scale=0.5) for b in bits[49:]], lag_ratio=0.1), run_time=0.8)
        self.end_scene(sid)

    # 6. not_exact：0.1 ≠ 0.1
    def not_exact(self):
        sid = "not_exact"
        old = list(self.mobjects)
        left = mono("0.1", 80, MINT)
        eq = txt("=", 80, DIM)
        right = mono("0.1", 80, MINT)
        full = VGroup(left, eq, right).arrange(RIGHT, buff=0.5).move_to(ORIGIN)
        self.play(FadeOut(*old), FadeIn(full), run_time=0.5)
        # 等号变不等号
        slash = Line(UP * 0.5 + LEFT * 0.3, DOWN * 0.5 + RIGHT * 0.3, color=PINK, stroke_width=6)
        self.play(Create(slash), run_time=0.4)
        self.end_scene(sid)

    # 7. error_add：两个误差条相加
    def error_add(self):
        sid = "error_add"
        old = list(self.mobjects)
        bar1 = Rectangle(width=2, height=0.4, color=BLUE, fill_opacity=0.5).move_to(UP * 1)
        bar2 = Rectangle(width=2, height=0.4, color=BLUE, fill_opacity=0.5).move_to(DOWN * 0.5)
        plus = txt("+", 48, DIM).move_to(ORIGIN)
        result = Rectangle(width=4, height=0.4, color=PINK, fill_opacity=0.7).move_to(DOWN * 2)
        self.play(FadeOut(*old), FadeIn(bar1), FadeIn(bar2), FadeIn(plus), run_time=0.5)
        self.play(Transform(VGroup(bar1, bar2), result), run_time=0.8)
        self.end_scene(sid)

    # 8. finite：有限 vs 无限
    def finite(self):
        sid = "finite"
        old = list(self.mobjects)
        left = VGroup(
            txt("有限", 72, MINT, bold=True),
            txt("52 位", 48, DIM),
        ).arrange(DOWN, buff=0.2).move_to(LEFT * 2)
        vs = txt("VS", 60, PINK, bold=True).move_to(ORIGIN)
        right = VGroup(
            txt("无限", 72, PINK, bold=True),
            txt("", 48, DIM),
        ).arrange(DOWN, buff=0.2).move_to(RIGHT * 2)
        self.play(FadeOut(*old), FadeIn(left, shift=RIGHT * 0.3), run_time=0.5)
        self.play(FadeIn(right, shift=LEFT * 0.3), run_time=0.5)
        self.play(GrowFromCenter(vs), rate_func=rate_functions.ease_out_back, run_time=0.4)
        self.end_scene(sid)

    # 9. outro：IEEE 754 · DOUBLE PRECISION
    def outro(self):
        sid = "outro"
        old = list(self.mobjects)
        ieee = txt("IEEE 754", 60, DIM).move_to(UP * 1)
        dp = txt("DOUBLE PRECISION", 48, MINT, bold=True).move_to(DOWN * 0.5)
        self.play(FadeOut(*old), FadeIn(ieee, shift=UP * 0.3), run_time=0.5)
        self.play(FadeIn(dp, shift=UP * 0.3), run_time=0.5)
        self.end_scene(sid)
