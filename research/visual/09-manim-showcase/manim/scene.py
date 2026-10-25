"""Manim 炫技测试：展示所有能力

包含：
1. 3D 相机动画（环绕旋转）
2. 粒子系统（沿路径流动）
3. 复杂变形（morphing）
4. 数据可视化（动态函数图像）
5. 物理模拟（弹跳球）
6. 分形（递归生成）
7. 文字特效

用法：
    python -m manim render scene.py Showcase --format mp4
"""

import os
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
CYAN, MAGENTA, GOLD, PINK, GREEN = "#22d3ee", "#e879f9", "#fbbf24", "#f472b6", "#4ade80"
INK, DIM = "#f8fafc", "#6b7280"
FONT = "Microsoft YaHei"

def txt(s, fs, color=INK, bold=False):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL)


class Showcase(ThreeDScene):
    def construct(self):
        # 开场标题
        title = txt("Manim 能力展示", 72, CYAN, bold=True)
        self.play(FadeIn(title, scale=1.5), run_time=1.5)
        self.wait(1)
        self.play(FadeOut(title), run_time=0.5)
        
        # 1. 3D 相机动画
        self.camera_3d_demo()
        
        # 2. 粒子系统
        self.particle_system_demo()
        
        # 3. 复杂变形
        self.morphing_demo()
        
        # 4. 数据可视化
        self.data_viz_demo()
        
        # 5. 物理模拟
        self.physics_demo()
        
        # 6. 分形
        self.fractal_demo()
        
        # 7. 文字特效
        self.text_effect_demo()
        
        # 结尾
        end = txt("这就是代码的力量", 60, GOLD, bold=True)
        self.play(FadeIn(end, scale=1.3), run_time=1.5)
        self.wait(2)
    
    # 1. 3D 相机动画
    def camera_3d_demo(self):
        self.clear()
        label = txt("① 3D 相机动画", 48, CYAN).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 创建 3D 物体（环面）
        torus = Torus(major_radius=1.5, minor_radius=0.5, 
                     checkerboard_colors=[CYAN, MAGENTA],
                     resolution=(24, 12))
        torus.rotate(PI/4, axis=RIGHT)
        
        self.play(Create(torus), run_time=2.0)
        
        # 相机环绕旋转
        self.begin_ambient_camera_rotation(rate=0.5)
        self.wait(4)
        self.stop_ambient_camera_rotation()
        
        self.play(FadeOut(torus), FadeOut(label), run_time=0.5)
    
    # 2. 粒子系统
    def particle_system_demo(self):
        self.clear()
        label = txt("② 粒子系统", 48, MAGENTA).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 创建路径（螺旋）
        spiral = ParametricFunction(
            lambda t: np.array([
                2 * np.cos(t) * np.exp(-t/10),
                2 * np.sin(t) * np.exp(-t/10),
                0
            ]),
            t_range=[0, 6 * PI],
            color=DIM,
            stroke_width=2
        )
        self.play(Create(spiral), run_time=1.5)
        
        # 粒子沿路径流动
        num_particles = 50
        particles = VGroup(*[Dot(color=GOLD, radius=0.08) for _ in range(num_particles)])
        self.add(particles)
        
        def update_particles(mob, dt):
            for i, dot in enumerate(mob):
                t = (self.time + i * 0.1) % (6 * PI)
                point = spiral.function(t)
                dot.move_to(point)
        
        particles.add_updater(update_particles)
        self.wait(5)
        particles.clear_updaters()
        
        self.play(FadeOut(spiral), FadeOut(particles), FadeOut(label), run_time=0.5)
    
    # 3. 复杂变形
    def morphing_demo(self):
        self.clear()
        label = txt("③ 复杂变形", 48, GOLD).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 圆形 → 方形 → 三角形 → 星形
        circle = Circle(radius=1.5, color=CYAN, fill_opacity=0.3)
        square = Square(side_length=2.5, color=MAGENTA, fill_opacity=0.3)
        triangle = RegularPolygon(3, color=GOLD, fill_opacity=0.3).scale(1.5)
        star = Star(n=5, color=PINK, fill_opacity=0.3).scale(1.5)
        
        self.play(FadeIn(circle), run_time=0.5)
        self.play(Transform(circle, square), run_time=1.5)
        self.wait(0.5)
        self.play(Transform(circle, triangle), run_time=1.5)
        self.wait(0.5)
        self.play(Transform(circle, star), run_time=1.5)
        self.wait(1)
        
        self.play(FadeOut(circle), FadeOut(label), run_time=0.5)
    
    # 4. 数据可视化
    def data_viz_demo(self):
        self.clear()
        label = txt("④ 数据可视化", 48, GREEN).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 坐标轴
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            axis_config={"color": DIM},
        ).scale(0.8).shift(DOWN * 0.5)
        
        # 动态函数图像
        def func(x, t):
            return np.sin(x + t) * np.exp(-x**2 / 4)
        
        graph = axes.plot(lambda x: func(x, 0), color=CYAN, stroke_width=3)
        
        self.play(Create(axes), run_time=1.0)
        self.play(Create(graph), run_time=1.5)
        
        # 动画更新
        def update_graph(mob, dt):
            mob.become(axes.plot(lambda x: func(x, self.time), color=CYAN, stroke_width=3))
        
        graph.add_updater(update_graph)
        self.wait(5)
        graph.clear_updaters()
        
        self.play(FadeOut(axes), FadeOut(graph), FadeOut(label), run_time=0.5)
    
    # 5. 物理模拟
    def physics_demo(self):
        self.clear()
        label = txt("⑤ 物理模拟", 48, PINK).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 地面
        ground = Line(LEFT * 4, RIGHT * 4, color=DIM, stroke_width=4).shift(DOWN * 3)
        self.play(Create(ground), run_time=0.5)
        
        # 弹跳球
        ball = Circle(radius=0.3, color=GOLD, fill_opacity=0.8).shift(UP * 4)
        self.play(FadeIn(ball), run_time=0.3)
        
        # 物理参数
        y = 4.0
        vy = 0.0
        gravity = -9.8
        bounce = 0.7
        ground_y = -3 + 0.3  # 地面位置 + 球半径
        
        def update_ball(mob, dt):
            nonlocal y, vy
            vy += gravity * dt
            y += vy * dt
            if y < ground_y:
                y = ground_y
                vy = -vy * bounce
            mob.move_to([0, y, 0])
        
        ball.add_updater(update_ball)
        self.wait(5)
        ball.clear_updaters()
        
        self.play(FadeOut(ball), FadeOut(ground), FadeOut(label), run_time=0.5)
    
    # 6. 分形
    def fractal_demo(self):
        self.clear()
        label = txt("⑥ 分形", 48, CYAN).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 谢尔宾斯基三角形
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
        
        for level in range(5):
            tri = sierpinski(level, size=3.5)
            if level > 0:
                self.play(FadeOut(self.mobjects[-1]), run_time=0.3)
            self.play(FadeIn(tri, lag_ratio=0.1), run_time=1.0)
            self.wait(0.3)
        
        self.play(FadeOut(self.mobjects[-1]), FadeOut(label), run_time=0.5)
    
    # 7. 文字特效
    def text_effect_demo(self):
        self.clear()
        label = txt("⑦ 文字特效", 48, MAGENTA).shift(UP * 3.5)
        self.play(FadeIn(label), run_time=0.5)
        
        # 打字机效果
        text = "代码即艺术"
        chars = VGroup(*[txt(c, 80, GOLD, bold=True) for c in text])
        chars.arrange(RIGHT, buff=0.1)
        
        for char in chars:
            self.play(FadeIn(char, shift=UP * 0.3), run_time=0.2)
        
        self.wait(1)
        
        # 波浪动画
        def wave_animation(mob, dt):
            for i, char in enumerate(mob):
                char.shift(UP * 0.3 * np.sin(self.time * 3 + i * 0.5))
        
        chars.add_updater(wave_animation)
        self.wait(3)
        chars.clear_updaters()
        
        self.play(FadeOut(chars), FadeOut(label), run_time=0.5)
