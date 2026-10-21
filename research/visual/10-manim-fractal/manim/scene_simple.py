"""Manim 极限测试：简化版

先测试基础功能，确保能渲染成功。
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
CYAN, MAGENTA, GOLD, INK = "#22d3ee", "#e879f9", "#fbbf24", "#f8fafc"
FONT = "Microsoft YaHei"

def txt(s, fs, color=INK, bold=False):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL)


class FractalLimit(Scene):
    def construct(self):
        # 1. 标题
        title = txt("分形：有限面积，无限边界", 60, CYAN, bold=True).shift(UP * 3)
        self.play(FadeIn(title), run_time=1.0)
        
        # 2. 谢尔宾斯基三角形（简化版）
        def sierpinski(level, size=3):
            if level == 0:
                h = size * np.sqrt(3) / 2
                pts = np.array([[-size/2, -h/3, 0], [size/2, -h/3, 0], [0, 2*h/3, 0]])
                return Polygon(*pts, color=CYAN, fill_opacity=0.3, stroke_width=2)
            
            smaller = sierpinski(level - 1, size / 2)
            h = size * np.sqrt(3) / 2
            offsets = [
                np.array([-size/4, -h/6, 0]),
                np.array([size/4, -h/6, 0]),
                np.array([0, h/3, 0]),
            ]
            return VGroup(*[smaller.copy().shift(off) for off in offsets])
        
        self.wait(1)
        for level in range(4):
            tri = sierpinski(level, size=3.5)
            self.play(FadeOut(self.mobjects[-1]) if len(self.mobjects) > 1 else Animation(VGroup()), run_time=0.3)
            self.play(FadeIn(tri), run_time=1.5)
            self.wait(0.5)
        
        # 3. 科赫雪花（简化版）
        def koch_line(p1, p2, level):
            if level == 0:
                return Line(p1, p2, color=MAGENTA, stroke_width=3)
            
            v = p2 - p1
            p_a = p1 + v / 3
            p_b = p1 + 2 * v / 3
            
            # 旋转 60 度
            angle = np.pi / 3
            rot = np.array([[np.cos(angle), -np.sin(angle), 0], 
                           [np.sin(angle), np.cos(angle), 0],
                           [0, 0, 1]])
            p_tip = p_a + rot @ (p_b - p_a)
            
            return VGroup(
                koch_line(p1, p_a, level - 1),
                koch_line(p_a, p_tip, level - 1),
                koch_line(p_tip, p_b, level - 1),
                koch_line(p_b, p2, level - 1)
            )
        
        h = 3.5 * np.sqrt(3) / 2
        p1 = np.array([-3.5/2, -h/3, 0])
        p2 = np.array([3.5/2, -h/3, 0])
        p3 = np.array([0, 2*h/3, 0])
        
        self.wait(1)
        for level in range(4):
            snowflake = VGroup(
                koch_line(p1, p2, level),
                koch_line(p2, p3, level),
                koch_line(p3, p1, level)
            )
            self.play(FadeOut(self.mobjects[-1]) if len(self.mobjects) > 1 else Animation(VGroup()), run_time=0.3)
            self.play(Create(snowflake), run_time=2.0)
            self.wait(0.5)
        
        # 4. 结尾
        end_text = txt("1.58 维", 120, GOLD, bold=True)
        self.play(FadeOut(self.mobjects[-1]) if len(self.mobjects) > 1 else Animation(VGroup()), run_time=0.5)
        self.play(FadeIn(end_text), run_time=1.5)
        self.wait(2)
