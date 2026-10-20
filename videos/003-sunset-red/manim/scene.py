"""003《夕阳为什么是红的》里用 Manim 讲原理的两段。

    Physics：white → molecule → scatter → ratio（白光、分子、瑞利散射、蓝光约 6 倍）
    SunsetPath：path → lose_blue（傍晚斜穿的大气路程长、蓝光一路被散射掉）

每段单独渲染成一个片段，帧数按 timeline.json 精确计算，和着色器段、风景段拼起来正好等于配音长度。

用法（在 003-sunset-red 目录里）:
    uv run python -m manim render manim/scene.py Physics --format mp4
    uv run python -m manim render manim/scene.py SunsetPath --format mp4
    低清预览：先设环境变量 PREVIEW=1
"""

import json
import os
from pathlib import Path

import numpy as np
from manim import *

PREVIEW = os.environ.get("PREVIEW") == "1"
config.pixel_width, config.pixel_height = (540, 960) if PREVIEW else (1080, 1920)
config.frame_rate = 15 if PREVIEW else 30
config.frame_width, config.frame_height = 9, 16
config.background_color = "#070b16"
config.disable_caching = True

INK, DIM, PINK, GOLD = "#f8fafc", "#9ca3af", "#fb7185", "#fbbf24"
SPECTRUM = ["#ef4444", "#f97316", "#facc15", "#22c55e", "#3b82f6", "#8b5cf6"]   # 红 橙 黄 绿 蓝 紫
SKY_BLUE = "#60a5fa"
FONT = "Microsoft YaHei"

TL = json.loads((Path(__file__).resolve().parent.parent / "build" / "sunset-red" / "timeline.json").read_text(encoding="utf-8"))
SCENES = {s["id"]: s for s in TL["scenes"]}


def word(sid, text, nth=1):
    words = SCENES[sid]["words"]
    hits = [w for w in words if w["text"].strip() == text] or [w for w in words if text in w["text"]]
    if len(hits) < nth:
        raise KeyError(f"分镜 {sid} 里找不到第 {nth} 个「{text}」")
    return hits[nth - 1]["start"]


def txt(s, fs, color=INK, bold=False):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL)


def fit(m, max_w=8.2):
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


def wave(x0, x1, y, wavelength, amp, color, width=6):
    return FunctionGraph(lambda x: y + amp * np.sin(TAU * (x - x0) / wavelength), x_range=[x0, x1, 0.02],
                         color=color, stroke_width=width)


class Segment(Scene):
    """按绝对时间轴对齐的一段：FIRST、LAST 是这一段包含的首尾分镜"""
    FIRST = LAST = None

    def setup(self):
        self.f0 = round(SCENES[self.FIRST]["start"] * config.frame_rate)
        self.title_mob = None

    def wait_abs(self, t):
        fps = config.frame_rate
        n = round(t * fps) - self.f0 - round(self.renderer.time * fps)
        if n > 0:
            self.wait((n + 0.5) / fps, frozen_frame=True)
        elif n < 0:
            print(f"  [晚了] 想在 {t:.3f}s，片段内已到 {self.renderer.time:.3f}s")

    def at(self, sid, text, nth=1):
        self.wait_abs(word(sid, text, nth))

    def end_scene(self, sid):
        self.wait_abs(SCENES[sid]["end"])
        print(f"  {sid:<10} 结束：片段内 {self.renderer.time:.3f}s")

    def title(self, s, color=INK):
        new = fit(txt(s, 54, color, bold=True)).move_to(UP * 5.6)
        anims = [FadeIn(new, shift=DOWN * 0.2)]
        if self.title_mob is not None:
            anims.append(FadeOut(self.title_mob))
        self.title_mob = new
        return anims

    def clear_except_title(self):
        return [FadeOut(m) for m in self.mobjects if m is not self.title_mob]


class Physics(Segment):
    FIRST, LAST = "white", "ratio"

    def construct(self):
        self.white()
        self.molecule()
        self.scatter()
        self.ratio()

    # 白光其实是所有颜色混在一起：三棱镜分光
    def white(self):
        sid = "white"
        self.play(*self.title("白光 = 所有颜色"), run_time=0.3)
        self.at(sid, "太阳")
        sun = VGroup(*[Circle(radius=0.55 + 0.18 * k, stroke_width=0, fill_color="#fff7d6", fill_opacity=0.9 / (1 + 2.5 * k))
                       for k in range(4)]).move_to([-3.2, 3.6, 0])
        self.play(FadeIn(sun, scale=0.6), run_time=0.5)
        prism = Polygon([-0.9, 0.4, 0], [0.9, 0.4, 0], [0, 2.0, 0], stroke_color=INK, stroke_width=4,
                        fill_color="#93c5fd", fill_opacity=0.15)
        entry, exitp = np.array([-0.45, 1.2, 0]), np.array([0.42, 1.25, 0])
        self.at(sid, "白色")
        beam = Line(sun.get_center(), entry, color=WHITE, stroke_width=12)
        self.play(FadeIn(prism), Create(beam), run_time=0.6)
        inner = Line(entry, exitp, color=WHITE, stroke_width=8, stroke_opacity=0.8)
        rays = VGroup(*[Line(exitp, [4.4, 2.3 - 0.75 * k, 0], color=c, stroke_width=10) for k, c in enumerate(SPECTRUM)])
        names = VGroup(*[txt(n, 30, c, bold=True).move_to([3.7, 2.3 - 0.75 * k + 0.3, 0])
                         for k, (n, c) in enumerate(zip("红橙黄绿蓝紫", SPECTRUM))])
        self.at(sid, "彩虹")
        self.play(Create(inner), LaggedStart(*[Create(r) for r in rays], lag_ratio=0.12), run_time=0.9)
        self.play(FadeIn(names), run_time=0.3)
        self.at(sid, "混")
        note = txt("这些颜色混在一起，就是白光", 40, INK).move_to(DOWN * 1.6)
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.4)
        self.end_scene(sid)

    # 分子比光的波长小得多
    def molecule(self):
        sid = "molecule"
        self.play(*self.clear_except_title(), *self.title("分子比光的波长小一千多倍"), run_time=0.4)
        self.at(sid, "大气")
        rng = np.random.default_rng(3)
        dots = VGroup(*[Dot([x, y, 0], radius=0.035, color=DIM) for x, y in
                        zip(rng.uniform(-4.0, 4.0, 70), rng.uniform(-1.8, 4.4, 70))])
        self.play(FadeIn(dots, lag_ratio=0.02), run_time=0.8)
        self.at(sid, "分子")
        mol = VGroup(Dot([0.0, 0.0, 0], radius=0.06, color=SKY_BLUE), Dot([0.1, 0.0, 0], radius=0.06, color=SKY_BLUE))
        mol.move_to([0, 0.4, 0])
        ring = Circle(radius=0.35, color=SKY_BLUE, stroke_width=4).move_to(mol)
        mlab = txt("氮气、氧气分子：约 0.3 纳米", 34, SKY_BLUE).next_to(ring, DOWN, buff=0.25)
        self.play(dots.animate.set_opacity(0.25), FadeIn(mol), Create(ring), FadeIn(mlab), run_time=0.5)
        self.at(sid, "波长")
        w = wave(-4.2, 4.2, 3.0, 2.8, 0.7, GOLD)
        b = BraceBetweenPoints([-4.2 + 0.7, 3.95, 0], [-4.2 + 0.7 + 2.8, 3.95, 0], direction=UP, color=GOLD)
        wlab = txt("可见光的一个波长：400–700 纳米", 34, GOLD).move_to([0, 4.55, 0])
        self.play(Create(w), GrowFromCenter(b), FadeIn(wlab), run_time=0.7)
        self.at(sid, "小")
        big = txt("小一千多倍", 72, PINK, bold=True).move_to(DOWN * 1.4)
        self.play(FadeIn(big, scale=1.3), run_time=0.4)
        self.end_scene(sid)

    # 瑞利散射：光被小分子弹向四面八方
    def scatter(self):
        sid = "scatter"
        self.play(*self.clear_except_title(), *self.title("瑞利散射"), run_time=0.3)
        center = np.array([0.6, 1.4, 0])
        self.at(sid, "光")
        beam = Line([-4.6, 1.4, 0], center + LEFT * 0.3, color=WHITE, stroke_width=12)
        self.play(Create(beam), run_time=0.4)
        self.at(sid, "小分子")
        mol = VGroup(Dot(radius=0.16, color=SKY_BLUE), Dot(RIGHT * 0.26, radius=0.16, color=SKY_BLUE)).move_to(center)
        self.play(GrowFromCenter(mol), run_time=0.3)
        self.at(sid, "弹向")
        arrows = VGroup(*[Arrow(center, center + 2.1 * np.array([np.cos(a), np.sin(a), 0]), buff=0.35,
                                color=SKY_BLUE if k % 2 == 0 else WHITE, stroke_width=6, max_tip_length_to_length_ratio=0.15)
                          for k, a in enumerate(np.linspace(0, TAU, 14, endpoint=False))])
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.06), run_time=1.0)
        self.at(sid, "瑞利")
        lab = txt("瑞利散射", 72, SKY_BLUE, bold=True).move_to(DOWN * 1.5)
        self.play(FadeIn(lab, scale=1.2), run_time=0.4)
        self.end_scene(sid)

    # 波长越短散射越强：蓝光约为红光 6 倍
    def ratio(self):
        sid = "ratio"
        self.play(*self.clear_except_title(), *self.title("蓝光散射约为红光的 6 倍"), run_time=0.3)
        self.at(sid, "波长")
        wb = wave(-2.0, 4.2, 4.2, 0.9, 0.32, SPECTRUM[4])
        wr = wave(-2.0, 4.2, 3.2, 0.9 * 700 / 450, 0.32, SPECTRUM[0])
        lb = txt("蓝光\n450 纳米", 28, SPECTRUM[4], bold=True).move_to([-3.2, 4.2, 0])
        lr = txt("红光\n700 纳米", 28, SPECTRUM[0], bold=True).move_to([-3.2, 3.2, 0])
        self.play(Create(wb), Create(wr), FadeIn(lb), FadeIn(lr), run_time=0.45)
        self.at(sid, "短")
        self.play(Indicate(wb, color=SKY_BLUE, scale_factor=1.05), run_time=0.5)
        self.at(sid, "散射")
        law = txt("散射强度 ∝ 1 / 波长⁴", 44, INK, bold=True).move_to([0, 2.0, 0])
        self.play(FadeIn(law, shift=UP * 0.2), run_time=0.4)
        base = -1.6
        unit = 2.6 / ((700 / 450) ** 4)          # 红光柱的高度；蓝光柱是它的 (700/450)^4 ≈ 5.86 倍
        bar_b = Rectangle(width=1.3, height=unit * (700 / 450) ** 4, stroke_width=0, fill_color=SPECTRUM[4], fill_opacity=0.9)
        bar_r = Rectangle(width=1.3, height=unit, stroke_width=0, fill_color=SPECTRUM[0], fill_opacity=0.9)
        bar_b.move_to([-1.2, base, 0], aligned_edge=DOWN)
        bar_r.move_to([1.2, base, 0], aligned_edge=DOWN)
        axis = Line([-2.6, base, 0], [2.6, base, 0], color=DIM, stroke_width=3)
        nb = txt("蓝光", 30, SPECTRUM[4], bold=True).next_to(bar_b, DOWN, buff=0.15)
        nr = txt("红光", 30, SPECTRUM[0], bold=True).next_to(bar_r, DOWN, buff=0.15)
        self.at(sid, "蓝光")
        self.play(Create(axis), GrowFromEdge(bar_b, DOWN), FadeIn(nb), run_time=0.7)
        self.at(sid, "红光")
        self.play(GrowFromEdge(bar_r, DOWN), FadeIn(nr), run_time=0.4)
        self.at(sid, "六")
        times = txt("≈ 5.9 倍", 56, PINK, bold=True).next_to(bar_b, RIGHT, buff=0.35).shift(UP * 0.6)
        self.play(FadeIn(times, scale=1.3), run_time=0.4)
        self.end_scene(sid)


class SunsetPath(Segment):
    FIRST, LAST = "path", "lose_blue"

    EARTH_C = np.array([2.4, -14.0, 0])
    R_EARTH, R_ATM = 13.0, 14.6

    def construct(self):
        self.path()
        self.lose_blue()

    # 傍晚阳光斜穿大气，路程比头顶直射长几十倍
    def path(self):
        sid = "path"
        obs = self.EARTH_C + UP * self.R_EARTH                     # 观察者站在地球顶上
        self.obs = obs
        self.play(*self.title("傍晚：阳光穿过的大气长几十倍"), run_time=0.3)
        earth = Circle(radius=self.R_EARTH, stroke_color="#4ade80", stroke_width=4, fill_color="#0f2a1c",
                       fill_opacity=1).move_to(self.EARTH_C)
        atm = Annulus(inner_radius=self.R_EARTH, outer_radius=self.R_ATM, fill_color=SKY_BLUE, fill_opacity=0.16,
                      stroke_width=0).move_to(self.EARTH_C)
        atm_edge = Circle(radius=self.R_ATM, stroke_color=SKY_BLUE, stroke_width=2, stroke_opacity=0.6).move_to(self.EARTH_C)
        person = VGroup(Dot(obs + UP * 0.32, radius=0.09, color=INK),
                        Line(obs + UP * 0.22, obs, color=INK, stroke_width=5))
        note = txt("示意图：大气厚度已放大", 26, DIM).move_to([-2.2, -2.0, 0])
        alab = txt("大气层", 30, SKY_BLUE).move_to([-1.0, 0.9, 0])
        self.at(sid, "傍晚")
        self.play(FadeIn(earth), FadeIn(atm), FadeIn(atm_edge), FadeIn(person), FadeIn(note), FadeIn(alab), run_time=0.35)
        # 傍晚：太阳在地平线方向，光水平射来，在大气里走很长
        exit_x = obs[0] - np.sqrt(self.R_ATM ** 2 - self.R_EARTH ** 2)
        sun_low = VGroup(*[Circle(radius=0.32 + 0.12 * k, stroke_width=0, fill_color="#fb923c", fill_opacity=0.9 / (1 + 2.5 * k))
                           for k in range(3)]).move_to([exit_x - 0.05, obs[1] + 0.32, 0])
        self.sun_low = sun_low
        self.at(sid, "太阳")
        self.play(FadeIn(sun_low, scale=0.6), run_time=0.4)
        long_path = Line([exit_x, obs[1] + 0.32, 0], obs + UP * 0.32, color="#fb923c", stroke_width=10)
        self.long_path = long_path
        self.at(sid, "斜")
        self.play(Create(long_path), run_time=0.8)
        llab = txt("傍晚：路程长", 32, "#fb923c", bold=True).next_to(long_path, UP, buff=0.18).shift(LEFT * 1.0)
        self.play(FadeIn(llab), run_time=0.3)
        # 头顶：光竖直射来，在大气里只走一小段
        self.at(sid, "头顶")
        sun_high = Circle(radius=0.3, stroke_width=0, fill_color="#fff7d6", fill_opacity=1).move_to(obs + UP * 3.4)
        short_path = Line(obs + UP * (self.R_ATM - self.R_EARTH), obs + UP * 0.42, color="#fde68a", stroke_width=10)
        slab = txt("头顶：路程短", 32, "#fde68a", bold=True).next_to(short_path, LEFT, buff=0.2).shift(UP * 0.55)
        self.play(FadeIn(sun_high), Create(short_path), FadeIn(slab), run_time=0.5)
        self.at(sid, "几十")
        big = txt("真实比例：最长约 38 倍", 46, PINK, bold=True).move_to([0, 3.6, 0])
        self.play(FadeIn(big, scale=1.2), run_time=0.4)
        self.path_extra = VGroup(sun_high, short_path, slab, llab, big)
        self.end_scene(sid)

    # 沿途蓝光被散射掉，剩下红橙光
    def lose_blue(self):
        sid = "lose_blue"
        self.play(FadeOut(self.path_extra), FadeOut(self.long_path), *self.title("一路上，蓝光被散射光了"), run_time=0.3)
        x0, x1 = self.long_path.get_start()[0], self.long_path.get_end()[0]
        y = self.obs[1] + 0.32
        n = 32
        xs = np.linspace(x0, x1, n + 1)
        stripes = VGroup()
        keep = {0: 1.0, 1: 1.0, 2: 0.75, 3: 0.35, 4: 0.0, 5: 0.0}     # 走到终点时各色还剩多少（示意）
        for k, c in enumerate(SPECTRUM):
            yy = y + (2.5 - k) * 0.11
            stripes.add(VGroup(*[Line([xs[i], yy, 0], [xs[i + 1], yy, 0], color=c, stroke_width=7) for i in range(n)]))
        self.at(sid, "一路上")
        self.play(LaggedStart(*[Create(s) for s in stripes], lag_ratio=0.05), run_time=0.7)
        self.at(sid, "蓝光")
        # 每一小段按"走过的距离"衰减：蓝紫最快，红橙几乎不减
        fades = []
        for k, s in enumerate(stripes):
            for i, seg in enumerate(s):
                frac = (i + 0.5) / n
                fades.append(seg.animate.set_stroke(opacity=1.0 - (1.0 - keep[k]) * frac))
        rng = np.random.default_rng(1)
        lost = VGroup(*[Arrow([x, y, 0], [x + rng.uniform(-0.3, 0.3), y + rng.choice([-1, 1]) * rng.uniform(0.8, 1.4), 0],
                              buff=0, color=SKY_BLUE if rng.random() < 0.7 else SPECTRUM[5], stroke_width=4,
                              max_tip_length_to_length_ratio=0.25)
                        for x in np.linspace(x0 + 0.3, x1 - 0.6, 12)])
        self.play(*fades, LaggedStart(*[GrowArrow(a) for a in lost], lag_ratio=0.08), run_time=1.6)
        self.at(sid, "最后")
        glow = VGroup(*[Circle(radius=0.2 + 0.14 * k, stroke_width=0, fill_color="#f97316", fill_opacity=0.8 / (1 + 2 * k))
                        for k in range(3)]).move_to(self.obs + UP * 0.32)
        self.play(FadeOut(lost), FadeIn(glow, scale=0.5),
                  *[c.animate.set_fill("#ef4444") for c in self.sun_low], run_time=0.6)
        self.at(sid, "红光")
        lab = txt("到达眼睛：主要是红光和橙光", 40, "#fb923c", bold=True).move_to([0, 3.3, 0])
        self.play(FadeIn(lab, shift=UP * 0.2), run_time=0.4)
        self.end_scene(sid)
