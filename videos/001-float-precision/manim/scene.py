"""Manim 版本：0.1 + 0.2 为什么不等于 0.3

竖屏科普动画（1080×1920），数字排版 + 尾数格子。

用法：
    python -m manim render scene.py FloatPrecision --format mp4
    低清预览：先设环境变量 PREVIEW=1（540×960、15fps）

依赖：
    先跑 vlab-tts 生成 build/float-precision/timeline.json，画面按配音里每个词的时间点出现。
    没有时间轴时退回无配音模式，动作之间只隔固定时长，用来快速看画面。

画面里的数字都是真实的双精度值（由 Python 的 struct / Decimal 算出），不是示意。
"""

import json
import os
import struct
from decimal import Decimal
from pathlib import Path

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

# ---------- 真实数值 ----------
MANTISSA_01 = format(struct.unpack(">Q", struct.pack(">d", 0.1))[0] & ((1 << 52) - 1), "052b")  # 存下来的 52 位
TRUE_BITS = "1001" * 13                       # 0.1 = 1.1001 1001 1001… × 2^-4，不舍入时的前 52 位
STORED_01 = str(Decimal(0.1))[:21]            # 0.1000000000000000055
STORED_02 = str(Decimal(0.2))[:21]            # 0.2000000000000000111
EXACT_SUM = str(Decimal(0.1) + Decimal(0.2))[:21]   # 0.3000000000000000166（两个近似值的精确和）
assert MANTISSA_01 == TRUE_BITS[:48] + "1010"  # 末四位 1001 被就近舍入成 1010

# ---------- 时间轴 ----------
TL_PATH = Path(__file__).resolve().parent.parent / "build" / "float-precision" / "timeline.json"
HAS_AUDIO = TL_PATH.exists()
SCENES = {s["id"]: s for s in json.loads(TL_PATH.read_text(encoding="utf-8"))["scenes"]} if HAS_AUDIO else {}


def word(sid, text, nth=1):
    """查分镜 sid 里第 nth 次出现的词的开始时间（先精确匹配，再包含匹配）"""
    words = SCENES[sid]["words"]
    hits = [w for w in words if w["text"].strip() == text] or [w for w in words if text in w["text"]]
    if len(hits) < nth:
        raise KeyError(f"分镜 {sid} 里找不到第 {nth} 个「{text}」")
    return hits[nth - 1]["start"]


# ---------- 文字 ----------
def txt(s, fs, color=INK, bold=False, font=FONT, **kw):
    return Text(s, font=font, font_size=fs, color=color, weight=BOLD if bold else NORMAL, **kw)


def mono(s, fs, color=INK, **kw):
    return Text(s, font=MONO, font_size=fs, color=color, **kw)


def fit(m, max_w=8.2):
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


def first_error_digit(s):
    """近似值里第一个"多出来"的数字的位置（跳过 0.x 后面那串 0）"""
    return next(i for i in range(3, len(s)) if s[i] != "0")


# ---------- 分镜 ----------
class FloatPrecision(Scene):
    def construct(self):
        for part in (self.hook, self.answer, self.not_bug, self.binary, self.mantissa,
                     self.not_exact, self.error_add, self.finite, self.outro):
            part()

    # ----- 时间对齐 -----
    def wait_to(self, t):
        """等到时间轴上的 t 秒。按帧数补齐，两种等待的取整方式不同，分开算。"""
        fps = config.frame_rate
        n = round(t * fps) - round(self.renderer.time * fps)
        if n > 0:
            if any(m.has_time_based_updater() for m in self.get_mobject_family_members()):
                self.wait((n - 0.5) / fps, frozen_frame=False)   # 逐帧：帧数 = ceil(时长×fps)
            else:
                self.wait((n + 0.5) / fps, frozen_frame=True)    # 冻结：帧数 = int(时长×fps)
        elif n < 0:
            print(f"  [晚了] 想在 {t:.3f}s 开始，当前已到 {self.renderer.time:.3f}s")

    def at(self, sid, text, nth=1):
        if HAS_AUDIO:
            self.wait_to(word(sid, text, nth))
        else:
            self.wait(0.3)

    def end_scene(self, sid):
        if HAS_AUDIO:
            self.wait_to(SCENES[sid]["end"])
        else:
            self.wait(0.6)
        print(f"  {sid:<10} 结束：实际 {self.renderer.time:.3f}s")

    def fade_all(self):
        return [FadeOut(m) for m in self.mobjects]

    # 1. hook：0.1 + 0.2 = ?
    def hook(self):
        sid = "hook"
        eq = VGroup(mono("0.1", 80, MINT), txt("+", 80, DIM), mono("0.2", 80, MINT), txt("=", 80, DIM))
        eq.arrange(RIGHT, buff=0.3)
        q = txt("?", 120, PINK, bold=True)
        fit(VGroup(eq, q).arrange(RIGHT, buff=0.4)).move_to(UP * 1.2)
        self.at(sid, "等于多少")
        self.play(Write(eq), run_time=1.2)
        self.play(GrowFromCenter(q), rate_func=rate_functions.ease_out_back, run_time=0.6)
        self.hook_eq, self.hook_q = eq, q
        self.end_scene(sid)

    # 2. answer：直觉 0.3，计算机 0.30000000000000004（只有末尾的 4 标红）
    def answer(self):
        sid = "answer"
        self.play(FadeOut(self.hook_q), self.hook_eq.animate.scale(0.6).move_to(UP * 4.4), run_time=0.3)
        self.at(sid, "直觉")
        row1 = VGroup(txt("直觉", 40, DIM), mono("0.3", 88, MINT)).arrange(DOWN, buff=0.25).move_to(UP * 2.5)
        self.play(FadeIn(row1, shift=UP * 0.2), run_time=0.4)
        self.at(sid, "计算机")
        label2 = txt("计算机", 40, DIM).move_to(UP * 0.7)
        self.play(FadeIn(label2), run_time=0.3)
        self.at(sid, "0.30000000000000004")
        num = fit(mono("0.30000000000000004", 64, INK)).next_to(label2, DOWN, buff=0.35)
        num[-1].set_color(PINK)
        self.play(Write(num), run_time=0.9)
        self.play(Create(SurroundingRectangle(num[-1], color=PINK, buff=0.08)), run_time=0.3)
        self.end_scene(sid)

    # 3. not_bug：这不是 bug + 打勾
    def not_bug(self):
        sid = "not_bug"
        self.play(*self.fade_all(), run_time=0.3)
        text = txt("这不是 bug", 88, MINT, bold=True).move_to(UP * 2.0)
        self.at(sid, "这")
        self.play(FadeIn(text, shift=UP * 0.3), run_time=0.35)
        self.at(sid, "bug")
        circle = Circle(radius=0.75, color=MINT, stroke_width=8).move_to(UP * 0.1)
        check = VMobject(color=MINT, stroke_width=10).set_points_as_corners(
            [LEFT * 0.35 + UP * 0.05, DOWN * 0.28, RIGHT * 0.42 + UP * 0.38]).move_to(circle)
        self.play(Create(circle), Create(check), run_time=0.6)
        self.end_scene(sid)

    # 4. binary：0.1 写成二进制，0011 无限循环
    def binary(self):
        sid = "binary"
        self.play(*self.fade_all(), run_time=0.3)
        self.at(sid, "0.1")
        dec = mono("0.1", 110, MINT).move_to(UP * 3.6)
        self.play(FadeIn(dec, scale=0.8), run_time=0.4)
        self.at(sid, "二进制")
        arrow = Arrow(UP * 2.8, UP * 1.6, color=DIM, buff=0, stroke_width=6)
        lab = txt("转成二进制", 36, DIM).next_to(arrow, RIGHT, buff=0.3)
        self.play(GrowArrow(arrow), FadeIn(lab), run_time=0.4)
        head = mono("0.0", 56, DIM)
        groups = [mono("0011", 56, BLUE if i % 2 == 0 else "#93c5fd") for i in range(4)]
        dots = mono("…", 56, DIM)
        row = fit(VGroup(head, *groups, dots).arrange(RIGHT, buff=0.2)).move_to(UP * 0.8)
        self.at(sid, "无限循环")
        inf = txt("无限循环小数", 48, PINK, bold=True).move_to(DOWN * 1.3)
        self.play(FadeIn(inf, shift=UP * 0.2), run_time=0.4)
        self.at(sid, "0.0001100110011")
        self.play(FadeIn(head), run_time=0.25)
        self.play(LaggedStart(*[FadeIn(g, shift=LEFT * 0.3) for g in groups], lag_ratio=0.6), run_time=1.6)
        brace = Brace(groups[0], DOWN, color=BLUE, buff=0.12)
        blab = txt("循环节 0011", 30, BLUE).next_to(brace, DOWN, buff=0.1)
        self.play(FadeIn(dots), GrowFromCenter(brace), FadeIn(blab), run_time=0.5)
        self.end_scene(sid)

    # 5. mantissa：64 位里只有 52 位尾数，装不下无限循环，只能截断
    def mantissa(self):
        sid = "mantissa"
        self.play(*self.fade_all(), run_time=0.3)
        self.at(sid, "双精度")
        segs = VGroup(*[
            Rectangle(width=8.0 * n / 64, height=0.5, stroke_color=c, stroke_width=2, fill_color=c, fill_opacity=0.25)
            for n, c in ((1, DIM), (11, BLUE), (52, MINT))
        ]).arrange(RIGHT, buff=0).move_to(UP * 4.6)
        seg_labels = VGroup(
            txt("符号 1 · 指数 11", 26, BLUE).next_to(segs[:2], DOWN, buff=0.12).align_to(segs, LEFT),
            txt("尾数 52", 26, MINT).next_to(segs[2], DOWN, buff=0.12),
        )
        title = txt("双精度浮点数：64 位", 40, INK, bold=True).next_to(segs, UP, buff=0.25)
        self.play(FadeIn(title), FadeIn(segs), FadeIn(seg_labels), run_time=0.5)

        cells = VGroup()
        for i, b in enumerate(TRUE_BITS):
            sq = Square(side_length=0.56, color=MINT, stroke_width=2, fill_color=MINT, fill_opacity=0.08)
            bit = mono(b, 28, INK).move_to(sq)
            cells.add(VGroup(sq, bit))
        cells.arrange_in_grid(rows=4, cols=13, buff=0.04).move_to(UP * 1.6)
        self.at(sid, "52 位")
        self.play(Indicate(segs[2], color=MINT), LaggedStart(*[FadeIn(c, scale=0.6) for c in cells], lag_ratio=0.03),
                  run_time=1.0)
        self.at(sid, "无限循环")
        tail = mono("1001 1001 1001 1001 …", 34, DIM).next_to(cells, DOWN, buff=0.5).align_to(cells, LEFT)
        more = txt("后面还有无穷多位", 28, DIM).next_to(tail, DOWN, buff=0.15).align_to(cells, LEFT)
        self.play(FadeIn(tail, shift=LEFT * 0.6), FadeIn(more), run_time=0.6)
        self.at(sid, "截断")
        y = (cells.get_bottom()[1] + tail.get_top()[1]) / 2
        cut = DashedLine([cells.get_left()[0], y, 0], [cells.get_right()[0], y, 0], color=PINK, stroke_width=5)
        self.play(Create(cut), run_time=0.3)
        self.play(FadeOut(tail, shift=DOWN * 0.6), FadeOut(more, shift=DOWN * 0.6), run_time=0.45)
        new_bits = [mono(b, 28, PINK).move_to(c[1]) for b, c in zip(MANTISSA_01[48:], cells[48:])]
        note = txt("末四位按就近舍入：1001 存成 1010", 28, PINK).next_to(cut, DOWN, buff=0.35)
        self.play(*[Transform(c[1], nb) for c, nb in zip(cells[48:], new_bits)],
                  *[c[0].animate.set_stroke(PINK) for c in cells[48:]], FadeIn(note), run_time=0.4)
        self.end_scene(sid)

    # 6. not_exact：你写的 0.1 ≠ 计算机里存的 0.1000000000000000055511…
    def not_exact(self):
        sid = "not_exact"
        self.at(sid, "所以")
        self.play(*self.fade_all(), run_time=0.3)
        self.at(sid, "0.1")
        top = VGroup(txt("你写的", 36, DIM), mono("0.1", 96, MINT)).arrange(DOWN, buff=0.2).move_to(UP * 3.5)
        self.play(FadeIn(top, shift=UP * 0.2), run_time=0.4)
        self.at(sid, "计算机")
        stored = str(Decimal(0.1))[:25] + "…"
        val = fit(mono(stored, 48, INK))
        val[first_error_digit(stored):].set_color(PINK)
        bot = VGroup(txt("计算机里存的", 36, DIM), val).arrange(DOWN, buff=0.2).move_to(DOWN * 0.2)
        self.play(FadeIn(bot, shift=UP * 0.2), run_time=0.5)
        self.at(sid, "不是")
        neq = mono("≠", 96, PINK).move_to(UP * 1.55)
        self.play(GrowFromCenter(neq), run_time=0.4)
        self.end_scene(sid)

    # 7. error_add：两个近似值相加，误差也跟着相加
    def error_add(self):
        sid = "error_add"
        self.play(*self.fade_all(), run_time=0.3)
        nums = [mono(s + "…", 46, INK) for s in (STORED_01, STORED_02, EXACT_SUM)]
        signs = [mono(s, 46, DIM) for s in ("+", "+", "=")]
        signs[0].set_opacity(0)   # 第一行只占位，让三行数字左边对齐
        rows = VGroup(*[VGroup(sg, n).arrange(RIGHT, buff=0.3) for sg, n in zip(signs, nums)])
        rows.arrange(DOWN, buff=0.45, aligned_edge=RIGHT)
        fit(rows).move_to(UP * 1.8)
        line = Line(rows[1].get_corner(DL) + DOWN * 0.22, rows[1].get_corner(DR) + DOWN * 0.22, color=DIM)
        head = txt("两个近似值", 40, DIM).next_to(rows, UP, buff=0.5)
        self.at(sid, "两个")
        self.play(FadeIn(nums[0]), FadeIn(nums[1]), FadeIn(head), run_time=0.4)
        self.at(sid, "相加")
        self.play(FadeIn(signs[1]), Create(line), run_time=0.3)
        self.at(sid, "误差")
        tails = [n[first_error_digit(s):] for n, s in zip(nums[:2], (STORED_01, STORED_02))]
        self.play(*[t.animate.set_color(PINK) for t in tails], run_time=0.4)
        self.at(sid, "相加", nth=2)
        nums[2][first_error_digit(EXACT_SUM):].set_color(PINK)
        self.play(FadeIn(signs[2]), FadeIn(nums[2], shift=DOWN * 0.2), run_time=0.4)
        note = VGroup(txt("再舍入成最近的 double", 30, DIM), mono("0.30000000000000004", 40, PINK))
        note.arrange(DOWN, buff=0.15).next_to(rows, DOWN, buff=0.6)
        self.play(FadeIn(note), run_time=0.4)
        self.end_scene(sid)

    # 8. finite：有限 VS 无限
    def finite(self):
        sid = "finite"
        self.play(*self.fade_all(), run_time=0.3)
        self.at(sid, "有限")
        left = VGroup(txt("有限", 80, MINT, bold=True), txt("52 位", 56, DIM)).arrange(DOWN, buff=0.35)
        left.move_to(LEFT * 2.3 + UP * 1.5)
        self.play(FadeIn(left, shift=RIGHT * 0.3), run_time=0.4)
        self.at(sid, "无限")
        right = VGroup(txt("无限", 80, PINK, bold=True), mono("∞", 120, PINK)).arrange(DOWN, buff=0.3)
        right.move_to(RIGHT * 2.3 + UP * 1.5)
        vs = txt("VS", 56, DIM, bold=True).move_to(UP * 1.5)
        self.play(FadeIn(right, shift=LEFT * 0.3), GrowFromCenter(vs), run_time=0.4)
        self.end_scene(sid)

    # 9. outro：IEEE 754 · DOUBLE PRECISION
    def outro(self):
        sid = "outro"
        self.play(*self.fade_all(), run_time=0.3)
        self.at(sid, "IEEE")
        ieee = txt("IEEE 754", 84, INK, bold=True).move_to(UP * 2.8)
        self.play(FadeIn(ieee, shift=UP * 0.3), run_time=0.4)
        self.at(sid, "精度")
        dp = txt("DOUBLE PRECISION", 52, MINT, bold=True).move_to(UP * 1.6)
        self.play(FadeIn(dp, shift=UP * 0.3), run_time=0.4)
        self.at(sid, "真相")
        final = mono("0.1 + 0.2 ≠ 0.3", 56, DIM, t2c={"≠": PINK}).move_to(UP * 0.1)
        self.play(FadeIn(final), run_time=0.5)
        self.end_scene(sid)
