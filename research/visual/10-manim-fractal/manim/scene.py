"""Manim 极限测试：分形——有限面积，无限边界

展示 Manim 的高级功能：
- 递归分形生成（谢尔宾斯基三角形、科赫雪花）
- 3D 相机动画
- 粒子沿路径流动
- 复杂几何变形
- 自定义 UpdateFromAlphaFunc

用法：
    python -m manim render scene.py FractalLimit --format mp4
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

# ---------- 配色 ----------
CYAN, MAGENTA, GOLD, INK, DIM = "#22d3ee", "#e879f9", "#fbbf24", "#f8fafc", "#9ca3af"
FONT = "Microsoft YaHei"

# ---------- 时间轴 ----------
TL_PATH = Path(__file__).resolve().parent.parent / "build" / "fractal-limit" / "timeline.json"
if TL_PATH.exists():
    TL = json.loads(TL_PATH.read_text(encoding="utf-8"))
    SCENES = {s["id"]: s for s in TL["scenes"]}
    HAS_AUDIO = True
else:
    TL = {"scenes": [{"id": f"s{i}", "end": i * 5} for i in range(1, 7)]}
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


def txt(s, fs, color=INK, bold=False):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL)


# ---------- 分形生成 ----------
def sierpinski_triangles(level, size=3):
    """生成谢尔宾斯基三角形的所有小三角形"""
    if level == 0:
        h = size * np.sqrt(3) / 2
        pts = np.array([[-size/2, -h/3], [size/2, -h/3], [0, 2*h/3]])
        return [Polygon(*pts, color=CYAN, fill_opacity=0.3, stroke_width=2)]
    
    smaller = sierpinski_triangles(level - 1, size / 2)
    h = size * np.sqrt(3) / 2
    offsets = [
        np.array([-size/4, -h/6]),
        np.array([size/4, -h/6]),
        np.array([0, h/3]),
    ]
    result = []
    for tri in smaller:
        for offset in offsets:
            result.append(tri.copy().shift(offset))
    return result


def koch_curve(p1, p2, level):
    """生成科赫曲线的一段"""
    if level == 0:
        return [Line(p1, p2, color=MAGENTA, stroke_width=3)]
    
    v = p2 - p1
    p_a = p1 + v / 3
    p_b = p1 + 2 * v / 3
    # 旋转 60 度得到顶点
    angle = np.pi / 3
    rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    p_tip_2d = p_a[:2] + rot @ (p_b[:2] - p_a[:2])
    p_tip = np.array([p_tip_2d[0], p_tip_2d[1], 0])
    
    result = []
    result.extend(koch_curve(p1, p_a, level - 1))
    result.extend(koch_curve(p_a, p_tip, level - 1))
    result.extend(koch_curve(p_tip, p_b, level - 1))
    result.extend(koch_curve(p_b, p2, level - 1))
    return result


def koch_snowflake(level, size=3):
    """生成科赫雪花"""
    h = size * np.sqrt(3) / 2
    p1 = np.array([-size/2, -h/3, 0])
    p2 = np.array([size/2, -h/3, 0])
    p3 = np.array([0, 2*h/3, 0])
    
    lines = []
    lines.extend(koch_curve(p1, p2, level))
    lines.extend(koch_curve(p2, p3, level))
    lines.extend(koch_curve(p3, p1, level))
    return VGroup(*lines)


# ---------- 粒子系统 ----------
class ParticleFlow(UpdateFromAlphaFunc):
    """粒子沿路径流动"""
    def __init__(self, path, num_particles=20, color=GOLD, **kw):
        self.path = path
        self.num_particles = num_particles
        self.color = color
        self.particles = VGroup(*[Dot(color=color, radius=0.08) for _ in range(num_particles)])
        super().__init__(self.particles, self.update_particles, **kw)
    
    def update_particles(self, mob, alpha):
        for i, dot in enumerate(mob):
            t = (alpha + i / self.num_particles) % 1.0
            point = self.path.point_from_proportion(t)
            dot.move_to(point)


# ---------- 分镜 ----------
class FractalLimit(Scene):
    def construct(self):
        for part in (self.hook, self.sierpinski, self.koch, self.dimension, self.nature, self.outro):
            part()

    def wait_to(self, t):
        fps = config.frame_rate
        n = round(t * fps) - round(self.renderer.time * fps)
        if n > 0:
            self.wait((n + 0.5) / fps, frozen_frame=True)

    def at(self, sid, text):
        if HAS_AUDIO:
            self.wait_to(word(sid, text))

    def end_scene(self, sid):
        if HAS_AUDIO:
            self.wait_to(SCENES[sid]["end"])
        else:
            self.wait(1)

    # 1. hook：一个三角形，能有多复杂？
    def hook(self):
        sid = "hook"
        tri = Polygon(
            np.array([-2, -1, 0]),
            np.array([2, -1, 0]),
            np.array([0, 2, 0]),
            color=CYAN, fill_opacity=0.3, stroke_width=4
        )
        qmark = txt("?", 120, MAGENTA, bold=True).shift(DOWN * 2.5)
        title = txt("一个三角形，能有多复杂？", 56, INK, bold=True).shift(UP * 3)
        
        self.play(FadeIn(title), run_time=0.8)
        self.play(Create(tri), run_time=1.2)
        self.play(GrowFromCenter(qmark), rate_func=rate_functions.ease_out_back, run_time=0.8)
        self.end_scene(sid)

    # 2. 谢尔宾斯基三角形
    def sierpinski(self):
        sid = "sierpinski"
        old = list(self.mobjects)
        title = txt("谢尔宾斯基三角形", 56, CYAN, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        
        # 递归生成，逐级显示
        for level in range(5):
            tris = sierpinski_triangles(level, size=3.5)
            group = VGroup(*tris)
            self.play(FadeOut(self.mobjects[-1] if len(self.mobjects) > 1 else VGroup()), run_time=0.3)
            self.play(FadeIn(group, lag_ratio=0.1), run_time=1.5)
            self.wait(0.5)
        
        self.end_scene(sid)

    # 3. 科赫雪花
    def koch(self):
        sid = "koch"
        old = list(self.mobjects)
        title = txt("科赫雪花", 56, MAGENTA, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        
        # 递归生成
        for level in range(5):
            snowflake = koch_snowflake(level, size=3.5)
            self.play(FadeOut(self.mobjects[-1] if len(self.mobjects) > 1 else VGroup()), run_time=0.3)
            self.play(Create(snowflake, lag_ratio=0.05), run_time=2.0)
            self.wait(0.5)
        
        self.end_scene(sid)

    # 4. 分形维数
    def dimension(self):
        sid = "dimension"
        old = list(self.mobjects)
        
        # 显示维数
        dim_text = VGroup(
            txt("维数 =", 60, INK),
            txt("1.58", 120, GOLD, bold=True),
        ).arrange(RIGHT, buff=0.3).shift(UP * 1)
        
        # 对比：1D 线、2D 面、1.58D 分形
        line_1d = Line(LEFT * 3, RIGHT * 3, color=DIM, stroke_width=4).shift(DOWN * 1.5)
        label_1d = txt("1D 线", 40, DIM).next_to(line_1d, DOWN)
        
        square_2d = Square(side_length=2, color=DIM, fill_opacity=0.2, stroke_width=4).shift(DOWN * 1.5 + RIGHT * 3)
        label_2d = txt("2D 面", 40, DIM).next_to(square_2d, DOWN)
        
        # 分形（谢尔宾斯基）
        fractal = VGroup(*sierpinski_triangles(4, size=2)).shift(DOWN * 1.5 + LEFT * 3)
        label_fractal = txt("1.58D", 40, GOLD, bold=True).next_to(fractal, DOWN)
        
        title = txt("不是整数维", 56, INK, bold=True).shift(UP * 3)
        
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        self.play(FadeIn(dim_text), run_time=1.0)
        self.play(Create(line_1d), FadeIn(label_1d), run_time=0.8)
        self.play(Create(square_2d), FadeIn(label_2d), run_time=0.8)
        self.play(FadeIn(fractal), FadeIn(label_fractal), run_time=1.2)
        self.end_scene(sid)

    # 5. 自然界中的分形
    def nature(self):
        sid = "nature"
        old = list(self.mobjects)
        
        # 用文字 + 简单图形表示
        items = [
            ("️ 雪花", CYAN),
            ("🌿 蕨类", "#22c55e"),
            ("🏔️ 海岸线", "#60a5fa"),
            ("🫁 肺", "#f472b6"),
        ]
        
        title = txt("自然界中的分形", 56, INK, bold=True).shift(UP * 3)
        self.play(FadeOut(*old), FadeIn(title), run_time=0.5)
        
        for i, (name, color) in enumerate(items):
            y = 1.5 - i * 1.2
            item = txt(name, 48, color).shift(DOWN * (2 - i * 0.8))
            self.play(FadeIn(item, shift=RIGHT * 0.5), run_time=0.6)
        
        self.end_scene(sid)

    # 6. outro：有限面积，无限边界
    def outro(self):
        sid = "outro"
        old = list(self.mobjects)
        
        # 科赫雪花
        snowflake = koch_snowflake(3, size=3)
        
        title = txt("有限面积", 60, CYAN, bold=True).shift(UP * 2.5)
        subtitle = txt("无限边界", 60, MAGENTA, bold=True).shift(DOWN * 2.5)
        
        self.play(FadeOut(*old), run_time=0.5)
        self.play(Create(snowflake), run_time=2.0)
        self.play(FadeIn(title), FadeIn(subtitle), run_time=1.0)
        
        self.end_scene(sid)
