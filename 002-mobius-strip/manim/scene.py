"""Manim 版本：莫比乌斯环——只有一个面的奇迹

竖屏科普动画（1080×1920），拓扑学几何连续变形。

用法：
    python -m manim render scene.py MobiusStrip --format mp4
    低清预览：先设环境变量 PREVIEW=1（540×960、15fps）
"""

import json
import os
from pathlib import Path

import numpy as np
from manim import *
from manim.mobject.three_d.three_dimensions import Surface

# ---------- 画布 ----------
PREVIEW = os.environ.get("PREVIEW") == "1"
config.pixel_width, config.pixel_height = (540, 960) if PREVIEW else (1080, 1920)
config.frame_rate = 15 if PREVIEW else 30
config.frame_width, config.frame_height = 9, 16
config.background_color = "#0a0e1a"
config.disable_caching = True

# ---------- 配色 / 字体 ----------
CYAN, MAGENTA, GOLD, INK, DIM = "#22d3ee", "#e879f9", "#fbbf24", "#f8fafc", "#9ca3af"
FONT = "Microsoft YaHei"
MONO = "Cascadia Mono"

# ---------- 时间轴 ----------
TL_PATH = Path(__file__).resolve().parent.parent / "build" / "mobius-strip" / "timeline.json"
if TL_PATH.exists():
    TL = json.loads(TL_PATH.read_text(encoding="utf-8"))
    SCENES = {s["id"]: s for s in TL["scenes"]}
    HAS_AUDIO = True
else:
    TL = {"scenes": [{"id": f"s{i}", "end": i * 5} for i in range(1, 10)]}
    SCENES = {s["id"]: s for s in TL["scenes"]}
    HAS_AUDIO = False


def word(sid, text):
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


# ---------- 莫比乌斯环参数方程 ----------
def mobius_surface(u, v):
    """u: 0→2π (绕环), v: -0.5→0.5 (宽度)"""
    R = 2.0  # 大半径
    r = 0.6  # 半宽
    x = (R + r * v * np.cos(u / 2)) * np.cos(u)
    y = (R + r * v * np.cos(u / 2)) * np.sin(u)
    z = r * v * np.sin(u / 2)
    return np.array([x, y, z])


def mobius_edge(u):
    """莫比乌斯环的边缘"""
    R = 2.0
    r = 0.6
    x = (R + r * np.cos(u / 2)) * np.cos(u)
    y = (R + r * np.cos(u / 2)) * np.sin(u)
    z = r * np.sin(u / 2)
    return np.array([x, y, z])


# ---------- 分镜 ----------
class MobiusStrip(Scene):
    def construct(self):
        for part in (self.hook, self.normal, self.twist, self.mobius, self.ant,
                     self.cut, self.cut2, self.application, self.outro):
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

    # 1. hook：一张纸条，几个面？
    def hook(self):
        sid = "hook"
        strip = Rectangle(width=4, height=0.8, color=CYAN, fill_opacity=0.3, stroke_width=4)
        qmark = txt("?", 120, MAGENTA, bold=True).shift(DOWN * 2)
        label = txt("几个面？", 60, INK, bold=True).shift(UP * 2.5)
        self.play(FadeIn(strip, scale=0.8), FadeIn(label), run_time=1.0)
        self.play(GrowFromCenter(qmark), rate_func=rate_functions.ease_out_back, run_time=0.8)
        self.end_scene(sid)

    # 2. normal：普通环，两个面
    def normal(self):
        sid = "normal"
        old = list(self.mobjects)
        # 普通环（圆环）
        ring = Annulus(inner_radius=1.2, outer_radius=1.8, color=CYAN, fill_opacity=0.3, stroke_width=3)
        # 内外标记
        inner_label = txt("内", 40, DIM).shift(LEFT * 0.5)
        outer_label = txt("外", 40, DIM).shift(RIGHT * 0.5)
        title = txt("普通环：两个面", 56, INK, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        self.play(Create(ring), run_time=1.0)
        self.play(FadeIn(inner_label), FadeIn(outer_label), run_time=0.6)
        self.end_scene(sid)

    # 3. twist：扭转 180°
    def twist(self):
        sid = "twist"
        old = list(self.mobjects)
        strip = Rectangle(width=4, height=0.8, color=CYAN, fill_opacity=0.3, stroke_width=4)
        arrow = CurvedArrow(LEFT * 1.5, RIGHT * 1.5, angle=PI, color=MAGENTA, stroke_width=4)
        label = txt("扭转 180°", 60, MAGENTA, bold=True).shift(DOWN * 2)
        
        self.play(FadeOut(*old), FadeIn(strip), run_time=0.5)
        self.play(Create(arrow), FadeIn(label), run_time=1.2)
        # 纸条扭转动画
        self.play(Rotate(strip, angle=PI, axis=RIGHT), run_time=1.5)
        self.end_scene(sid)

    # 4. mobius：莫比乌斯环，一个面
    def mobius(self):
        sid = "mobius"
        old = list(self.mobjects)
        # 用 ParametricSurface 创建莫比乌斯环
        mobius = Surface(
            mobius_surface,
            u_range=[0, 2 * PI],
            v_range=[-0.5, 0.5],
            resolution=(32, 8),
            fill_color=CYAN,
            fill_opacity=0.4,
            stroke_color=CYAN,
            stroke_width=2,
        ).scale(0.8).shift(DOWN * 0.5)
        
        title = txt("莫比乌斯环：一个面", 56, MAGENTA, bold=True).shift(UP * 3)
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        self.play(Create(mobius), run_time=2.0)
        self.mobius_obj = mobius
        self.end_scene(sid)

    # 5. ant：蚂蚁爬行
    def ant(self):
        sid = "ant"
        old = list(self.mobjects)
        # 重新创建莫比乌斯环
        mobius = Surface(
            mobius_surface,
            u_range=[0, 2 * PI],
            v_range=[-0.5, 0.5],
            resolution=(32, 8),
            fill_color=CYAN,
            fill_opacity=0.3,
            stroke_color=CYAN,
            stroke_width=2,
        ).scale(0.8).shift(DOWN * 0.5)
        
        # 蚂蚁（小圆点）沿边缘移动
        ant = Dot(color=GOLD, radius=0.15).shift(RIGHT * 2 + DOWN * 0.5)
        path = ParametricFunction(
            lambda t: np.array([
                (2.0 + 0.6 * np.cos(t / 2)) * np.cos(t) * 0.8,
                (2.0 + 0.6 * np.cos(t / 2)) * np.sin(t) * 0.8,
                0.6 * np.sin(t / 2) * 0.8 - 0.5
            ]),
            t_range=[0, 4 * PI],  # 绕两圈回到起点
        )
        
        title = txt("蚂蚁可以爬遍整个面", 56, INK, bold=True).shift(UP * 3)
        self.play(FadeOut(*old), FadeIn(title), FadeIn(mobius), run_time=0.8)
        self.play(FadeIn(ant), run_time=0.3)
        self.play(MoveAlongPath(ant, path), run_time=3.0)
        self.end_scene(sid)

    # 6. cut：沿中线剪开
    def cut(self):
        sid = "cut"
        old = list(self.mobjects)
        # 剪开后的更大环（用两个环表示）
        big_ring = Annulus(inner_radius=1.5, outer_radius=2.2, color=CYAN, fill_opacity=0.3, stroke_width=3)
        scissors = txt("", 80, MAGENTA).shift(RIGHT * 2.5)
        title = txt("剪开：一个更大的环", 56, INK, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        self.play(Create(big_ring), run_time=1.5)
        self.play(FadeIn(scissors), run_time=0.5)
        self.play(scissors.animate.shift(LEFT * 5), run_time=1.0)
        self.end_scene(sid)

    # 7. cut2：再剪，两个套在一起的环
    def cut2(self):
        sid = "cut2"
        old = list(self.mobjects)
        # 两个套在一起的环
        ring1 = Annulus(inner_radius=1.0, outer_radius=1.4, color=CYAN, fill_opacity=0.3, stroke_width=3).shift(LEFT * 0.8)
        ring2 = Annulus(inner_radius=1.0, outer_radius=1.4, color=MAGENTA, fill_opacity=0.3, stroke_width=3).shift(RIGHT * 0.8)
        title = txt("再剪：两个套在一起的环", 56, INK, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        self.play(Create(ring1), Create(ring2), run_time=1.5)
        self.end_scene(sid)

    # 8. application：应用
    def application(self):
        sid = "application"
        old = list(self.mobjects)
        # 传送带示意图
        belt = Rectangle(width=5, height=1.2, color=GOLD, fill_opacity=0.3, stroke_width=3)
        arrow1 = Arrow(LEFT * 2, RIGHT * 2, color=INK, stroke_width=3).shift(UP * 0.3)
        arrow2 = Arrow(RIGHT * 2, LEFT * 2, color=INK, stroke_width=3).shift(DOWN * 0.3)
        label = txt("磨损均匀，寿命翻倍", 56, GOLD, bold=True).shift(DOWN * 2.5)
        title = txt("应用：传送带 / 打印机色带", 56, INK, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        self.play(Create(belt), run_time=0.8)
        self.play(Create(arrow1), Create(arrow2), run_time=0.8)
        self.play(FadeIn(label), run_time=0.6)
        self.end_scene(sid)

    # 9. outro：拓扑学的魔法
    def outro(self):
        sid = "outro"
        old = list(self.mobjects)
        # 莫比乌斯环 + 文字
        mobius = Surface(
            mobius_surface,
            u_range=[0, 2 * PI],
            v_range=[-0.5, 0.5],
            resolution=(32, 8),
            fill_color=CYAN,
            fill_opacity=0.4,
            stroke_color=CYAN,
            stroke_width=2,
        ).scale(0.6).shift(DOWN * 0.5)
        
        title = txt("拓扑学的魔法", 60, MAGENTA, bold=True).shift(UP * 2.5)
        subtitle = txt("改变连接方式，就能改变本质", 48, DIM).shift(DOWN * 2.5)
        
        self.play(FadeOut(*old), FadeIn(mobius), run_time=1.0)
        self.play(FadeIn(title), run_time=0.8)
        self.play(FadeIn(subtitle), run_time=0.8)
        self.end_scene(sid)
