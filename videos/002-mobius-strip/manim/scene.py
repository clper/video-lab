"""Manim 版本：莫比乌斯环——只有一个面的奇迹

竖屏科普动画（1080×1920），真 3D：纸条平放、翻面、弯成环、扭转、粘合，全程是同一条连续变形的带子。

用法：
    python -m manim render scene.py MobiusStrip --format mp4
    低清预览：先设环境变量 PREVIEW=1（540×960、15fps）

依赖：
    先跑 vlab-tts 生成 build/mobius-strip/timeline.json，画面按配音里每个词的时间点出现。
    没有时间轴时退回无配音模式，动作之间只隔固定时长，用来快速看画面。

几何约定：
    带子中线参数 u ∈ [0, 2π]，宽度参数 v ∈ [-HALF, HALF]。
    平放时带子躺在 xy 平面，宽度沿 y；弯曲时两端向 +z 卷起，粘成立在 x-z 平面里的环，接缝在环顶。
    扭转角沿中线均匀分布，twist=1 就是半圈（180°），首尾正好反向相接，就是莫比乌斯环。
    带子画成正反两层（沿法向各偏一点），两层分别上色，"正面/反面"才看得见。
    u 超过 2π 时公式自然接到反面，所以蚂蚁走 u ∈ [0, 4π] 就是在同一个面上走两圈。
"""

import json
import os
from pathlib import Path

import numpy as np
from manim import *
from manim.mobject.three_d.three_dimensions import ThreeDVMobject

# ---------- 画布 ----------
PREVIEW = os.environ.get("PREVIEW") == "1"
config.pixel_width, config.pixel_height = (540, 960) if PREVIEW else (1080, 1920)
config.frame_rate = 15 if PREVIEW else 30
config.frame_width, config.frame_height = 9, 16
config.background_color = "#0a0e1a"
config.disable_caching = True

# ---------- 配色 / 字体 ----------
CYAN, MAGENTA, GOLD, INK, DIM, PINK = "#22d3ee", "#e879f9", "#fbbf24", "#f8fafc", "#9ca3af", "#fb7185"
GOLD_DARK = "#b45309"
FONT = "Microsoft YaHei"
RGB = {c: np.array(color_to_rgb(c)) for c in (CYAN, MAGENTA, GOLD, GOLD_DARK)}

# ---------- 时间轴 ----------
TL_PATH = Path(__file__).resolve().parent.parent / "build" / "mobius-strip" / "timeline.json"
HAS_AUDIO = TL_PATH.exists()
SCENES = {s["id"]: s for s in json.loads(TL_PATH.read_text(encoding="utf-8"))["scenes"]} if HAS_AUDIO else {}


def word(sid, text, nth=1):
    """查分镜 sid 里第 nth 次出现的词的开始时间（先精确匹配，再包含匹配）"""
    words = SCENES[sid]["words"]
    hits = [w for w in words if w["text"].strip() == text] or [w for w in words if text in w["text"]]
    if len(hits) < nth:
        raise KeyError(f"分镜 {sid} 里找不到第 {nth} 个「{text}」")
    return hits[nth - 1]["start"]


# ---------- 文字（都固定在屏幕上，不跟 3D 相机转） ----------
def txt(s, fs, color=INK, bold=False):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL)


def fit(m, max_w=8.2):
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


# ---------- 几何 ----------
R, HALF, EPS, ZUP = 1.2, 0.5, 0.012, 0.2   # 环半径、带子半宽、正反两层间距、整体抬高（避开底部字幕）
BELT_A, BELT_R, BELT_HALF = 1.6, 0.7, 0.45   # 传送带：直线段半长、滚轮处半径、带子半宽
Y_HAT = np.array([0.0, 1.0, 0.0])


def _stack(x, y, z):
    return np.stack(np.broadcast_arrays(x, y, z), axis=-1)


def ring_frame(U, bend, radius):
    """中线：bend=0 是长 2πR 的直线，bend=1 是半径 R 的整圆，中间保持长度不变地弯过去。
    返回中线位置 C、切向 T、指向圆心的法向 Nb。"""
    U = np.asarray(U, dtype=float)
    zero = np.zeros_like(U)
    if bend < 1e-4:
        return _stack(radius * (U - PI), zero, zero), _stack(1 + zero, zero, zero), _stack(zero, zero, 1 + zero)
    rb = radius / bend
    ph = bend * (U - PI)
    zc = rb * (1 - np.cos(bend * PI)) / 2           # 让弯好的形状上下居中
    C = _stack(rb * np.sin(ph), zero, rb * (1 - np.cos(ph)) - zc)
    T = _stack(np.cos(ph), zero, np.sin(ph))
    Nb = _stack(-np.sin(ph), zero, np.cos(ph))
    return C, T, Nb


def belt_frame(U):
    """传送带中线：两段直线 + 两个半圆（套在两个滚轮上）。半圈扭转全部放在下面那段直线里。"""
    a, r = BELT_A, BELT_R
    U = np.asarray(U, dtype=float)
    L = 4 * a + 2 * PI * r
    s = U / TAU * L                                   # 从顶边中点出发，先往左走
    th1, th2 = (s - a) / r, (s - 3 * a - PI * r) / r
    conds = [s < a, s < a + PI * r, s < 3 * a + PI * r, s < 3 * a + 2 * PI * r]
    one, zero = np.ones_like(s), np.zeros_like(s)
    Cx = np.select(conds, [-s, -a - r * np.sin(th1), s - 2 * a - PI * r, a + r * np.sin(th2)], L - s)
    Cz = np.select(conds, [r * one, r * np.cos(th1), -r * one, -r * np.cos(th2)], r * one)
    Tx = np.select(conds, [-one, -np.cos(th1), one, np.cos(th2)], -one)
    Tz = np.select(conds, [zero, -np.sin(th1), zero, np.sin(th2)], zero)
    C, T, Nb = _stack(Cx, zero, Cz), _stack(Tx, zero, Tz), _stack(-Tz, zero, Tx)
    beta = PI / 2 * (1 + np.clip((s - L / 2) / a, -1, 1))   # 下面那段直线里从 0 转到 π
    return C, T, Nb, beta


def surf(U, V, eps=0.0, kind="ring", bend=1.0, twist=1.0, flip=0.0, radius=R):
    """带子上 (u, v) 处的点，eps 沿法向偏移（正反两层、蚂蚁都靠它）。"""
    if kind == "belt":
        C, T, Nb, ang = belt_frame(U)
    else:
        C, T, Nb = ring_frame(U, bend, radius)
        ang = twist * (np.asarray(U, dtype=float) - PI) / 2
    ang = np.asarray(ang)[..., None]
    W = np.cos(ang) * Y_HAT + np.sin(ang) * Nb       # 宽度方向：绕切向转 ang
    n = np.cross(T, W)
    if flip:                                          # 绕 x 轴翻面
        c, s = np.cos(flip), np.sin(flip)
        rot = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        C, W, n = C @ rot.T, W @ rot.T, n @ rot.T
    P = C + np.asarray(V, dtype=float)[..., None] * W + eps * n
    P[..., 2] += ZUP
    return P


def grid(u0, u1, nu, v0, v1, nv):
    Uv, Vv = np.linspace(u0, u1, nu + 1), np.linspace(v0, v1, nv + 1)
    UU, VV = np.meshgrid(Uv, Vv, indexing="ij")
    return UU, VV, (Uv[:-1] + Uv[1:]) / 2


def curve(points, color=PINK, width=7):
    return VMobject().set_points_smoothly(points).set_stroke(color, width)


NU, NV = (48, 4) if PREVIEW else (72, 6)
ZOOM_FLAT, ZOOM_RING, ZOOM_BIG, ZOOM_BELT = 1.0, 1.6, 1.0, 1.4   # 纸条要平放下整条，成环后推近


class Band(VGroup):
    """自己管理面片的带子。build() 每帧返回每层的 (顶点网格, 面片颜色)，这里只改顶点和颜色，不重建对象。"""

    def __init__(self, nu, nv, layers, build):
        super().__init__()
        self.nu, self.nv, self.build = nu, nv, build
        self.op = ValueTracker(1.0)                   # 整体不透明度，淡入淡出用它，别用 FadeIn
        self.layer_faces = [[ThreeDVMobject() for _ in range(nu * nv)] for _ in range(layers)]
        for faces in self.layer_faces:
            self.add(*faces)
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def refresh(self):
        op = self.op.get_value()
        for faces, (P, rgb) in zip(self.layer_faces, self.build()):
            k = 0
            for i in range(self.nu):
                for j in range(self.nv):
                    f = faces[k]
                    k += 1
                    f.set_points_as_corners([P[i, j], P[i + 1, j], P[i + 1, j + 1], P[i, j + 1], P[i, j]])
                    c = ManimColor.from_rgb(rgb[i, j])
                    f.set_fill(c, op)
                    f.set_stroke(c, 0.8, op)
        return self


# ---------- 分镜 ----------
class MobiusStrip(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-90 * DEGREES)
        # 主带子的形状参数
        self.bend, self.twist, self.flip = ValueTracker(0), ValueTracker(0), ValueTracker(0)
        self.blend = ValueTracker(0)      # 反面颜色向正面靠拢：0 品红，1 青色
        self.paint = ValueTracker(0)      # 蚂蚁走过的长度（u 单位，满 4π 涂满）
        self.ant_start = PI               # 从环底部的正面出发
        self.strip = Band(NU, NV, 2, self.build_strip)
        self.title_mob, self.labels = None, []
        for part in (self.hook, self.normal, self.twist_scene, self.mobius, self.ant,
                     self.cut, self.cut2, self.application, self.outro):
            part()

    # ----- 带子的每帧形状 -----
    def build_strip(self):
        kw = dict(bend=self.bend.get_value(), twist=self.twist.get_value(), flip=self.flip.get_value())
        UU, VV, Uc = grid(0, TAU, NU, -HALF, HALF, NV)
        k, p = self.blend.get_value(), self.paint.get_value()
        back = (1 - k) * RGB[MAGENTA] + k * RGB[CYAN]
        out = []
        for sgn, base, off in ((1, RGB[CYAN], 0.0), (-1, back, TAU)):
            rgb = np.tile(base, (NU, NV, 1))
            if p > 0:   # 正面第 i 块在蚂蚁路程里的位置是 u，反面是 u + 2π
                rgb[np.mod(Uc + off - self.ant_start, 2 * TAU) < p] = RGB[GOLD]
            out.append((surf(UU, VV, eps=sgn * EPS, **kw), rgb))
        return out

    def build_cut(self):
        """沿中线剪开：剩下的是 u ∈ [0, 4π]、v ∈ [0.03, HALF] 的一整条带子，morph 把它展开成大环（两整圈扭转）。"""
        m = self.morph.get_value()
        nv = max(2, NV // 2)
        UU, VV, _ = grid(0, 2 * TAU, 2 * NU, 0.03, HALF, nv)
        out = []
        for sgn in (1, -1):
            A = surf(UU, VV, eps=sgn * EPS)
            B = surf(UU / 2, VV - (0.03 + HALF) / 2, eps=sgn * EPS, radius=2 * R, twist=4)
            out.append(((1 - m) * A + m * B, np.tile(RGB[GOLD], (2 * NU, nv, 1))))
        return out

    def build_halves(self):
        """大环再沿中线剪开：两半各自闭合，彼此缠在一起。"""
        g = self.gap.get_value()
        w = (HALF - 0.03) / 2
        out = []
        for (v0, v1), col, d in (((-w, -0.02), CYAN, -1), ((0.02, w), MAGENTA, 1)):
            UU, VV, _ = grid(0, TAU, NU, v0, v1, 2)
            for sgn in (1, -1):
                P = surf(UU, VV + d * 0.08 * g, eps=sgn * EPS, radius=2 * R, twist=4)
                out.append((P, np.tile(RGB[col], (NU, 2, 1))))
        return out

    def build_belt(self):
        ph = self.phase.get_value()
        nb = NU + 24
        UU, VV, Uc = grid(0, TAU, nb, -BELT_HALF, BELT_HALF, NV)
        out = []
        for sgn, off in ((1, 0.0), (-1, TAU)):
            stripe = (np.floor(np.mod(Uc + off - ph, 2 * TAU) / (2 * TAU / 20)) % 2).astype(bool)
            rgb = np.where(stripe[:, None, None], RGB[GOLD], RGB[GOLD_DARK]) * np.ones((nb, NV, 3))
            out.append((surf(UU, VV, eps=sgn * EPS, kind="belt"), rgb))
        return out

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
        print(f"  {sid:<12} 结束：实际 {self.renderer.time:.3f}s")

    # ----- 屏幕文字 -----
    def hud(self, m):
        self.add_fixed_in_frame_mobjects(m)
        return m

    def title_anims(self, s, color=INK):
        new = self.hud(fit(txt(s, 54, color, bold=True)).move_to(UP * 5.6))
        anims = [FadeIn(new, shift=DOWN * 0.2)]
        if self.title_mob is not None:
            anims.append(FadeOut(self.title_mob))
        self.title_mob = new
        return anims

    def label(self, s, color, pos, fs=48, bold=True):
        m = self.hud(fit(txt(s, fs, color, bold=bold)).move_to(pos))
        self.labels.append(m)
        return m

    def clear_labels(self):
        old, self.labels = self.labels, []
        return [FadeOut(m) for m in old]

    def zoom_to(self, z):
        """相机推拉（只影响 3D 物体，屏幕文字不受影响）"""
        return self.camera.zoom_tracker.animate.set_value(z)

    def start_rock(self, amp=28 * DEGREES, period=10.0):
        """相机左右来回摆，3D 感更强；不整圈转，因为环立着，转到侧面会看成一条线。"""
        tr = self.camera.theta_tracker
        clock = {"t": 0.0}

        def upd(m, dt):
            clock["t"] += dt
            ramp = min(1.0, clock["t"] / 2.0)
            m.set_value(-90 * DEGREES + ramp * amp * np.sin(TAU * clock["t"] / period))

        tr.add_updater(upd)
        self.add(tr)

    # 1. hook：一张纸条，几个面？
    def hook(self):
        sid = "hook"
        self.strip.op.set_value(0)
        self.add(self.strip)
        self.play(*self.title_anims("一张纸条，几个面？"), run_time=0.4)
        self.at(sid, "纸条")
        self.play(self.strip.op.animate.set_value(1), run_time=0.6)
        self.at(sid, "几个")
        q = self.label("?", MAGENTA, UP * 3.4, fs=110)
        self.play(GrowFromCenter(q), rate_func=rate_functions.ease_out_back, run_time=0.5)
        self.end_scene(sid)

    # 2. normal：正面、反面；粘成环还是两个面
    def normal(self):
        sid = "normal"
        self.play(*self.clear_labels(), *self.title_anims("普通纸条：两个面"), run_time=0.4)
        self.at(sid, "正面")
        self.play(FadeIn(self.label("正面", CYAN, LEFT * 1.6 + UP * 3.4)), run_time=0.3)
        self.at(sid, "反面")
        self.play(self.flip.animate.set_value(PI), FadeIn(self.label("反面", MAGENTA, RIGHT * 1.6 + UP * 3.4)),
                  run_time=0.6)
        self.at(sid, "把")
        self.play(self.flip.animate.set_value(TAU), *self.clear_labels(), run_time=0.24)
        self.flip.set_value(0)
        self.at(sid, "粘")
        self.play(self.bend.animate.set_value(1), self.zoom_to(ZOOM_RING), run_time=1.0)
        self.at(sid, "还是")
        self.play(*self.title_anims("粘成环：还是两个面"), run_time=0.4)
        self.at(sid, "里面")
        self.play(FadeIn(self.label("里面", CYAN, LEFT * 1.6 + UP * 3.6)), run_time=0.3)
        self.at(sid, "外面")
        self.play(FadeIn(self.label("外面", MAGENTA, RIGHT * 1.6 + UP * 3.6)), run_time=0.3)
        self.end_scene(sid)

    # 3. twist：拉直、扭转 180°、再粘合
    def twist_scene(self):
        sid = "twist"
        self.play(*self.clear_labels(), run_time=0.3)
        self.at(sid, "但")
        self.play(self.bend.animate.set_value(0), self.zoom_to(ZOOM_FLAT), *self.title_anims("先扭转 180°，再粘合"),
                  run_time=0.8)
        self.at(sid, "扭转")
        self.play(self.twist.animate.set_value(1), FadeIn(self.label("180°", MAGENTA, UP * 3.4, fs=72)),
                  run_time=1.0)
        self.at(sid, "粘合")
        self.play(self.bend.animate.set_value(1), self.zoom_to(ZOOM_RING), *self.clear_labels(), run_time=1.2)
        self.end_scene(sid)

    # 4. mobius：正面接上了反面，只有一个面
    def mobius(self):
        sid = "mobius"
        self.start_rock()
        self.at(sid, "奇迹")
        self.play(*self.title_anims("莫比乌斯环", MAGENTA), run_time=0.4)
        self.at(sid, "只有")
        self.play(self.blend.animate.set_value(1), FadeIn(self.label("正面接上了反面：只有一个面", CYAN, UP * 3.9, fs=44)),
                  run_time=1.0)
        self.end_scene(sid)

    # 5. ant：蚂蚁不跨边缘，走两圈涂满整个面
    def ant(self):
        sid = "ant"
        self.play(*self.clear_labels(), *self.title_anims("蚂蚁可以爬遍整个面"), run_time=0.3)
        ant_pos = lambda: surf(self.ant_start + self.paint.get_value(), 0.0, eps=0.09)
        self.ant_dot = Dot3D(ant_pos(), radius=0.08, color=WHITE, resolution=(8, 8))
        self.ant_dot.add_updater(lambda m: m.move_to(ant_pos()))
        self.at(sid, "蚂蚁")
        self.play(FadeIn(self.ant_dot), run_time=0.3)
        self.at(sid, "出发")
        t0 = self.renderer.time
        dur = (word(sid, "表面") + 0.45 - t0) if HAS_AUDIO else 3.0
        speed = 2 * TAU / dur

        def crawl(m, dt):
            m.set_value(min(2 * TAU, m.get_value() + speed * dt))

        self.paint.add_updater(crawl)
        self.add(self.paint)
        self.at(sid, "边缘")
        edge = curve(surf(np.linspace(0, 2 * TAU, 241), HALF))   # 只有一条边，绕两圈才闭合
        self.play(Create(edge), FadeIn(self.label("不跨这条边", PINK, UP * 3.9, fs=44)), run_time=0.5)
        self.at(sid, "就")
        self.play(FadeOut(edge), *self.clear_labels(), run_time=0.2)
        self.at(sid, "爬遍")
        self.play(FadeIn(self.label("走两圈，正反两色全涂满", GOLD, UP * 3.9, fs=44)), run_time=0.4)
        self.end_scene(sid)
        self.paint.clear_updaters()
        self.paint.set_value(2 * TAU)

    # 6. cut：沿中线剪开，得到一个更大的环
    def cut(self):
        sid = "cut"
        self.play(*self.clear_labels(), FadeOut(self.ant_dot), run_time=0.3)
        self.at(sid, "沿")
        self.play(*self.title_anims("沿中线剪开"), run_time=0.2)
        self.at(sid, "中线")
        mid = curve(surf(np.linspace(0, TAU, 121), 0.0, eps=0.03))
        self.play(Create(mid), run_time=0.9)
        self.at(sid, "不会")
        self.play(FadeIn(self.label("变成两个环？", DIM, UP * 3.9, fs=44)), run_time=0.3)
        self.at(sid, "而是")
        self.morph = ValueTracker(0)
        self.cut_band = Band(2 * NU, max(2, NV // 2), 2, self.build_cut)
        self.remove(self.strip)
        self.add(self.cut_band)
        self.play(self.morph.animate.set_value(1), self.zoom_to(ZOOM_BIG), FadeOut(mid), *self.clear_labels(),
                  *self.title_anims("剪开：一个更大的环"), run_time=1.3)
        self.end_scene(sid)

    # 7. cut2：大环再剪一次，变成两个套在一起的环
    def cut2(self):
        sid = "cut2"
        self.at(sid, "再沿")
        self.play(*self.title_anims("再沿中线剪一次"), run_time=0.3)
        self.at(sid, "中线")
        mid = curve(surf(np.linspace(0, TAU, 161), 0.0, eps=0.03, radius=2 * R, twist=4))
        self.play(Create(mid), run_time=0.8)
        self.at(sid, "变成")
        self.gap = ValueTracker(0)
        self.halves = Band(NU, 2, 4, self.build_halves)
        self.remove(self.cut_band)
        self.add(self.halves)
        self.play(self.gap.animate.set_value(1), FadeOut(mid), run_time=0.5)
        self.at(sid, "套")
        self.play(*self.title_anims("两个套在一起的环"), run_time=0.4)
        self.end_scene(sid)

    # 8. application：莫比乌斯传送带
    def application(self):
        sid = "application"
        self.at(sid, "这个")
        self.phase = ValueTracker(0)
        self.phase.add_updater(lambda m, dt: m.increment_value(1.6 * dt))
        self.belt = Band(NU + 24, NV, 2, self.build_belt)
        self.belt.op.set_value(0)
        self.pulleys = VGroup(*[
            Cylinder(radius=BELT_R - 0.1, height=2 * BELT_HALF + 0.3, direction=Y_AXIS, resolution=(2, 24),
                     fill_color="#475569", fill_opacity=1, stroke_width=0, checkerboard_colors=False)
            .move_to([x, 0, ZUP]) for x in (-BELT_A, BELT_A)
        ])
        self.add(self.phase, self.belt)
        self.play(self.halves.op.animate.set_value(0), self.belt.op.animate.set_value(1), FadeIn(self.pulleys),
                  self.zoom_to(ZOOM_BELT), run_time=0.8)
        self.remove(self.halves)
        self.at(sid, "传送带")
        self.play(*self.title_anims("莫比乌斯传送带"), run_time=0.4)
        self.at(sid, "打印")
        self.play(*self.title_anims("传送带 · 打印机色带"), run_time=0.4)
        self.at(sid, "磨损")
        self.play(FadeIn(self.label("两面轮流受力，磨损均匀", INK, UP * 3.9, fs=44, bold=False)), run_time=0.4)
        self.at(sid, "寿命")
        self.play(FadeIn(self.label("寿命翻倍", GOLD, UP * 3.1, fs=60)), run_time=0.4)
        self.end_scene(sid)

    # 9. outro：拓扑学的魔法
    def outro(self):
        sid = "outro"
        self.paint.set_value(0)
        self.strip.op.set_value(0)
        self.add(self.strip)
        self.play(self.belt.op.animate.set_value(0), self.strip.op.animate.set_value(1), FadeOut(self.pulleys),
                  self.zoom_to(ZOOM_RING), *self.clear_labels(), run_time=0.7)
        self.remove(self.belt, self.phase)
        self.at(sid, "拓")
        self.play(*self.title_anims("拓扑学的魔法", MAGENTA), run_time=0.5)
        self.at(sid, "改变")
        self.play(FadeIn(self.label("改变连接方式，就能改变本质", INK, UP * 3.9, fs=44, bold=False)), run_time=0.5)
        self.end_scene(sid)
