"""做法③：用 Manim 做竖屏科普动画（蜂巢为什么是六边形）。

先配音、后做画面：读 ../build/hexagon/timeline.json，每个分镜按“词”的时间点出元素，
分镜末尾补齐到 timeline 里的 end。配音和字幕最后由 shared/finalize.py 合成。

用法（在 3_manim 目录）:
    uv run --frozen manim render scene.py Hexagon --format mp4
    低清预览：先设环境变量 PREVIEW=1（540×960、15fps，几何和时间轴不变）
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
config.frame_width, config.frame_height = 9, 16  # 120 像素/单位，y 从 +8 到 −8
config.background_color = "#15110E"
config.disable_caching = True  # 命中缓存时 renderer.time 按名义时长累加，会和真实帧数对不上

# ---------- 配色 / 字体 ----------
AMBER, CREAM, MUTED, CARD_BG = "#F5A524", "#FFF4E0", "#B8A890", "#261C13"
COLORS = {"tri": "#6C8CFF", "sq": "#34C3A0", "hex": "#F5A524"}
KINDS = ["tri", "sq", "hex"]
KIND_NAME = {"tri": "三角形", "sq": "正方形", "hex": "六边形"}
FONT = "Microsoft YaHei"

# ---------- 版面（Manim 坐标） ----------
TITLE_Y, SAFE_W = 5.17, 7.6  # 标题区中心（像素 240–440）；左右各留 80px
GRAPH_Y = 0.585  # 图形区（像素 520–1260，即 y +3.67 ~ −2.5）的中心；y < −2.5 留给字幕

# ---------- 数学：面积 = 1 时的边长（六边形=外接圆半径）和周长 ----------
UNIT = {"tri": np.sqrt(4 / np.sqrt(3)), "sq": 1.0, "hex": np.sqrt(2 / (3 * np.sqrt(3)))}  # 1.5197 / 1 / 0.6204
PERIM = {"tri": 3 * UNIT["tri"], "sq": 4.0, "hex": 6 * UNIT["hex"]}  # 4.559 / 4 / 3.722

# ---------- 时间轴 ----------
TL = json.loads((Path(__file__).resolve().parent.parent / "build/hexagon/timeline.json").read_text(encoding="utf-8"))
SCENES = {s["id"]: s for s in TL["scenes"]}
# 标题里高亮成琥珀色的词（纯风格选择，换题目时改这里）
HIGHLIGHT = {
    "hook": ["六边形"],
    "tiling": ["3 种"],
    "question": ["最短"],
    "perimeter": ["周长"],
    "wax": ["蜂蜡"],
    "proof": ["1999"],
    "outro": ["最少", "最大"],
}


def word(sid, text):
    """按文字查某个词的开始时间（整片绝对秒数）：优先完全相同，其次包含"""
    words = SCENES[sid]["words"]
    hit = next((w for w in words if w["text"] == text), None) or next((w for w in words if text in w["text"]), None)
    if hit is None:
        raise KeyError(f"分镜 {sid} 里找不到词「{text}」")
    return hit["start"]


def kind_of(label):
    """从“比正方形”“正六边形”这类文字里认出是哪种图形"""
    return next(k for k in KINDS if KIND_NAME[k] in label)


# ---------- 文字 ----------
def txt(s, fs, color=CREAM, bold=False, **kw):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL, **kw)


def make_title(sid):
    """分镜标题：一行放不下（要缩到 0.8 倍以下）就在逗号处拆成两行"""
    s = SCENES[sid]["headline"]
    t2c = {k: AMBER for k in HIGHLIGHT.get(sid, [])}
    t = txt(s, 56, bold=True, t2c=t2c)
    if t.width * 0.8 > SAFE_W and "，" in s:
        t = VGroup(*[txt(p, 56, bold=True, t2c=t2c) for p in s.split("，", 1)]).arrange(DOWN, buff=0.16)
    if t.width > SAFE_W:
        t.scale_to_fit_width(SAFE_W)
    return t.move_to([0, TITLE_Y, 0])


# ---------- 几何 ----------
def poly_pts(kind, size):
    """正多边形顶点：左下角在原点、底边水平、逆时针。size 是边长（正六边形的边长 = 外接圆半径）"""
    h = np.sqrt(3) / 2 * size
    pts = {
        "tri": [(0, 0), (size, 0), (size / 2, h)],
        "sq": [(0, 0), (size, 0), (size, size), (0, size)],
        "hex": [(0, 0), (size, 0), (1.5 * size, h), (size, 2 * h), (0, 2 * h), (-size / 2, h)],
    }[kind]
    return np.array([[x, y, 0.0] for x, y in pts])


def cell_pts(kind, size, at):
    """同上，但把中心放到 at（顶点顺序不变，Transform 时不会拧）"""
    p = poly_pts(kind, size)
    return p - p.mean(axis=0) + np.asarray(at, dtype=float)


def hex_centers(r, rings=2):
    """平顶六边形簇的格子中心（rings=2 时 19 格），按离中心由近到远排序"""
    cs = [
        np.array([1.5 * r * q, np.sqrt(3) * r * (s + q / 2), 0.0])
        for q in range(-rings, rings + 1)
        for s in range(-rings, rings + 1)
        if abs(q + s) <= rings
    ]
    return sorted(cs, key=lambda c: (round(np.linalg.norm(c), 2), np.arctan2(c[1], c[0])))


def clip_below(pts, y):
    """凸多边形与半平面 {y' ≤ y} 求交（Sutherland–Hodgman 的单边版）"""
    out = []
    for p, q in zip(pts, pts[1:] + pts[:1]):
        if p[1] <= y:
            out.append(p)
        if (p[1] <= y) != (q[1] <= y):
            out.append(p + (y - p[1]) / (q[1] - p[1]) * (q - p))
    return out


class Honey(VMobject):
    """格子里的蜂蜜：set_level(0→1) 液面从底往上涨"""

    def __init__(self, pts, level=0.0, **kw):
        super().__init__(stroke_width=0, fill_color=AMBER, fill_opacity=0.72, **kw)
        self.pts = [np.asarray(p, dtype=float) for p in pts]
        self.set_level(level)

    def set_level(self, level):
        ys = [p[1] for p in self.pts]
        poly = clip_below(self.pts, min(ys) + level * (max(ys) - min(ys))) if level > 1e-3 else []
        if len(poly) < 3:  # 空格子：退化成一个点
            poly = [self.pts[0]] * 3
        self.set_points_as_corners([*poly, poly[0]])
        return self


def fill_up(honey, level=1.0):
    return UpdateFromAlphaFunc(honey, lambda m, a: m.set_level(level * a))


def make_comb(r=0.68):
    """19 格蜂巢：蜡壁（琥珀描边）+ 每格一块蜂蜜（初始为空）"""
    cs = [c + [0, GRAPH_Y, 0] for c in hex_centers(r)]
    walls = VGroup(*[Polygon(*cell_pts("hex", r, c), color=AMBER, stroke_width=5) for c in cs])
    honey = [Honey(cell_pts("hex", r * 0.84, c)) for c in cs]
    return walls, honey


def unroll(bar, verts):
    """把多边形轮廓“滚”成一条直线：第 k 条边的角度匀速减小，减到 0 就贴地不动。
    等价于多边形在地面上滚一圈，留下的线长 = 周长。bar 是一条空 VMobject。"""
    v = np.array(verts)
    edges = np.roll(v, -1, axis=0) - v
    lengths = np.linalg.norm(edges, axis=1)
    angles = np.unwrap(np.arctan2(edges[:, 1], edges[:, 0]))  # 0, 2π/n, 4π/n, ...

    def update(m, a):
        pts = [v[0]]
        for length, ang in zip(lengths, np.maximum(angles - a * angles[-1], 0)):
            pts.append(pts[-1] + length * np.array([np.cos(ang), np.sin(ang), 0]))
        m.set_points_as_corners(pts)

    return UpdateFromAlphaFunc(bar, update)


# ---------- 分镜 2：密铺小块 ----------
ROW_Y = {"tri": 2.745, "sq": 0.585, "hex": -1.575}  # 三行的中心
PATCH_X, PATCH_W, PATCH_H, LABEL_X = -1.6, 4.3, 1.8, 0.95
CELL = {"tri": 0.62, "sq": 0.56, "hex": 0.34}  # 六边形取 0.34：框高 1.8 里各列 3/2 格交错，不会像有缝
TILE_TEXT = {"tri": ("三角形", "60° × 6 = 360°"), "sq": ("正方形", "90° × 4 = 360°"), "hex": ("正六边形", "120° × 3 = 360°")}


def patch(kind):
    """一小块密铺：只取完整落在框里的格子，按离中心由近到远排序（第 0 格在正中），越靠边越淡"""
    c, size = np.array([PATCH_X, ROW_Y[kind], 0.0]), CELL[kind]
    if kind == "tri":
        h = np.sqrt(3) / 2 * size
        o = c - [size / 2, h / 3, 0]  # 让正中那个尖朝上的三角形重心落在 c

        def P(i, j):
            return o + [i * size + j * size / 2, j * h, 0]

        cells = []
        for i in range(-12, 12):
            for j in range(-4, 5):
                cells += [[P(i, j), P(i + 1, j), P(i, j + 1)], [P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]]
    elif kind == "sq":
        cells = [cell_pts("sq", size, c + [i * size, j * size, 0]) for i in range(-8, 9) for j in range(-4, 5)]
    else:
        cells = [cell_pts("hex", size, c + p) for p in hex_centers(size, rings=8)]
    inside = [p for p in cells if all(abs(x - c[0]) <= PATCH_W / 2 + 1e-6 and abs(y - c[1]) <= PATCH_H / 2 + 1e-6 for x, y, _ in p)]
    inside.sort(key=lambda p: np.linalg.norm(np.mean(p, axis=0) - c))
    dmax = np.linalg.norm(np.mean(inside[-1], axis=0) - c)
    color, mobs = COLORS[kind], VGroup()
    for p in inside:
        f = 1 - 0.7 * (np.linalg.norm(np.mean(p, axis=0) - c) / dmax) ** 2
        mobs.add(Polygon(*p, color=color, stroke_width=3, stroke_opacity=f).set_fill(color, 0.14 * f))
    return mobs


def lineup_poly(n, r, at):
    """3~8 边正多边形（外接圆半径 r，外心在 at）；3/4/6 边用和后面一致的顶点顺序"""
    if n in (3, 4, 6):
        kind = {3: "tri", 4: "sq", 6: "hex"}[n]
        return Polygon(*cell_pts(kind, {3: r * np.sqrt(3), 4: r * np.sqrt(2), 6: r}[n], at))
    return RegularPolygon(n, radius=r, start_angle=PI / 2 if n % 2 else PI / n).shift(at)


def cross_mark(at, s=0.38):
    at = np.asarray(at, dtype=float)
    return VGroup(Line(at + s * (LEFT + UP), at + s * (RIGHT + DOWN)), Line(at + s * (RIGHT + UP), at + s * (LEFT + DOWN))).set_stroke(CREAM, 6)


# ---------- 分镜 3~5：等面积图形 / 周长条 ----------
K_Q = 1.5  # 分镜 3 里 1 个数学单位 = 1.5 个画面单位
Q_X, Q_BASE = {"tri": -2.55, "sq": 0.0, "hex": 2.55}, 0.9
K_P, BAR_X0 = 1.3, -3.0  # 分镜 4：图形缩到 1.3，左下角对齐到 x = −3
BAR_Y = {"tri": 1.75, "sq": -0.2, "hex": -2.05}  # 行距按“滚动时最高点”留够，不会扫到上一行
WAX_Y, WAX_ROW_Y = {"tri": 3.1, "sq": 2.4, "hex": 1.7}, [0.3, -1.5]  # 分镜 5：条形图上移收紧 + 两行大数据


class Hexagon(Scene):
    def construct(self):
        self.title = VGroup()
        for part in (self.hook, self.tiling, self.question, self.perimeter, self.wax, self.proof, self.outro):
            part()

    # ---------- 时间对齐 ----------
    def wait_to(self, t):
        """静止等到整片时间 t（按帧取整）。冻结帧按 int() 截断，所以多给半帧"""
        fps = config.frame_rate
        n = round(t * fps) - round(self.renderer.time * fps)
        if n > 0:
            self.wait((n + 0.5) / fps, frozen_frame=True)
        elif n < 0:
            print(f"  [晚了] 想在 {t:.3f}s 开始，当前已到 {self.renderer.time:.3f}s")

    def at(self, sid, text):
        self.wait_to(word(sid, text))

    def end_scene(self, sid):
        self.wait_to(SCENES[sid]["end"])
        print(f"  {sid:<10} 结束：应在 {SCENES[sid]['end']:.3f}s，实际 {self.renderer.time:.3f}s")

    def new_title(self, sid):
        """换标题：旧的先上移淡出，新的再上移淡入，两行字不叠在一起（返回动画列表，和别的动画一起 play）"""
        old, self.title = self.title, make_title(sid)
        return [AnimationGroup(FadeOut(old, shift=UP * 0.3), FadeIn(self.title, shift=UP * 0.3), lag_ratio=1)]

    def everything_but_title(self):
        return Group(*[m for m in self.mobjects if m is not self.title])

    # ---------- 1. hook：一簇蜂巢 ----------
    def hook(self):
        sid = "hook"
        self.title = make_title(sid)
        self.add(self.title)
        walls, honey = make_comb()
        self.play(LaggedStart(*[GrowFromCenter(w) for w in walls], lag_ratio=0.08), run_time=1.2)
        picks = {0: 1.0, 2: 0.75, 4: 1.0, 5: 0.5, 8: 1.0, 10: 0.65, 13: 0.9, 15: 1.0, 17: 0.55}  # 格子序号: 蜂蜜高度
        filled = [honey[i] for i in picks]
        self.bring_to_back(*filled)
        self.play(LaggedStart(*[fill_up(honey[i], lv) for i, lv in picks.items()], lag_ratio=0.2), run_time=1.3)
        self.comb = VGroup(walls, *filled)
        self.end_scene(sid)

    # ---------- 2. tiling：只有三种正多边形能密铺 ----------
    def tiling(self):
        sid = "tiling"
        self.play(*self.new_title(sid), FadeOut(self.comb, scale=0.85), run_time=0.6)

        # 3~8 边一字排开
        xs = dict(zip(range(3, 9), np.linspace(-3.15, 3.15, 6)))
        polys = {n: lineup_poly(n, 0.5, [x, GRAPH_Y, 0]).set_stroke(MUTED, 4) for n, x in xs.items()}
        tags = {n: txt(f"{n} 边", 26, MUTED).move_to([x, GRAPH_Y - 0.85, 0]) for n, x in xs.items()}
        self.play(LaggedStart(*[AnimationGroup(Create(polys[n]), FadeIn(tags[n])) for n in xs], lag_ratio=0.3), run_time=2.0)

        # “只有三种选择”：5、7、8 边打叉
        self.at(sid, "只有")
        bad = [5, 7, 8]
        crosses = VGroup(*[cross_mark([xs[n], GRAPH_Y, 0]) for n in bad])
        self.play(*[Create(c) for c in crosses], *[polys[n].animate.set_stroke(opacity=0.3) for n in bad], run_time=0.45)

        # 能铺的三个飞到各自那一行，变成“种子格”
        patches = {k: patch(k) for k in KINDS}
        seeds = {k: patches[k][0].set_stroke(opacity=0.7).set_fill(opacity=0) for k in KINDS}
        self.play(
            FadeOut(VGroup(*[polys[n] for n in bad], crosses, *tags.values())),
            *[ReplacementTransform(polys[n], seeds[k]) for n, k in zip((3, 4, 6), KINDS)],
            run_time=0.6,
        )

        # 念到哪个就铺开哪个
        self.labels = VGroup()
        for k in KINDS:
            self.at(sid, KIND_NAME[k])
            name, formula = TILE_TEXT[k]
            lab = VGroup(txt(name, 40, COLORS[k], bold=True), txt(formula, 26, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
            lab.move_to([LABEL_X, ROW_Y[k], 0], aligned_edge=LEFT)
            self.labels.add(lab)
            self.play(
                seeds[k].animate.set_stroke(opacity=1, width=4).set_fill(COLORS[k], 0.5),
                LaggedStart(*[GrowFromCenter(c) for c in patches[k][1:]], lag_ratio=0.04),
                FadeIn(lab, shift=RIGHT * 0.3),
                run_time=0.8,
            )
        self.patches = patches
        self.end_scene(sid)

    # ---------- 3. question：面积一样，谁的边最短 ----------
    def question(self):
        sid = "question"
        self.big = {}
        for k in KINDS:
            size = UNIT[k] * K_Q
            pts = poly_pts(k, size) + [Q_X[k] - size / 2, Q_BASE, 0]  # 底边中点对齐到 (Q_X, Q_BASE)
            self.big[k] = Polygon(*pts, color=COLORS[k], stroke_width=6).set_fill(COLORS[k], 0.25)
        others = VGroup(*[c for k in KINDS for c in self.patches[k][1:]])
        self.play(
            *self.new_title(sid),
            FadeOut(others),
            FadeOut(self.labels),
            *[ReplacementTransform(self.patches[k][0], self.big[k]) for k in KINDS],
            run_time=0.9,
        )
        self.at(sid, "面积")
        self.area_tags = VGroup(*[txt("面积 = 1", 30, MUTED).move_to([Q_X[k], Q_BASE - 0.45, 0]) for k in KINDS])
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.2) for t in self.area_tags], lag_ratio=0.2), run_time=0.6)

        self.at(sid, "谁")
        self.qmark = txt("?", 190, AMBER, bold=True).move_to([0, -1.3, 0])
        self.play(GrowFromCenter(self.qmark), rate_func=rate_functions.ease_out_back, run_time=0.5)

        self.at(sid, "边")  # 一道光沿着三个轮廓跑一圈
        flashes = [ShowPassingFlash(self.big[k].copy().set_fill(opacity=0).set_stroke(CREAM, 10), time_width=0.5) for k in KINDS]
        self.play(*flashes, run_time=1.0)
        self.end_scene(sid)

    # ---------- 4. perimeter：轮廓滚成直线，排成条形图 ----------
    def perimeter(self):
        sid = "perimeter"
        moves = []
        for k in KINDS:
            v0 = self.big[k].get_vertices()[0]
            moves.append(self.big[k].animate.scale(K_P / K_Q, about_point=v0).shift([BAR_X0, BAR_Y[k], 0] - v0))
        self.play(*self.new_title(sid), FadeOut(self.qmark), FadeOut(self.area_tags), *moves, run_time=0.9)

        self.bars, self.values = {}, {}
        dur = {"tri": 1.0, "sq": 0.6, "hex": 0.85}  # 都要在念到数字之前滚完
        for d in SCENES[sid]["data"]:
            k = kind_of(d["label"])
            self.at(sid, KIND_NAME[k])
            verts = self.big[k].get_vertices()
            bar = VMobject(stroke_color=COLORS[k], stroke_width=10, joint_type=LineJointType.ROUND).set_cap_style(CapStyleType.ROUND)
            self.bars[k] = bar
            self.play(unroll(bar, verts), self.big[k].animate.set_stroke(opacity=0.25), run_time=dur[k])

            self.at(sid, f"{d['value']:g}")  # 念到“4.56”“4”“3.72”时出数字
            end = verts[0] + [PERIM[k] * K_P, 0, 0]
            self.values[k] = txt(f"{d['value']:.2f}", 44, COLORS[k], bold=True).next_to(end, UP, buff=0.2, aligned_edge=RIGHT)
            self.play(FadeIn(self.values[k], shift=UP * 0.2), run_time=0.4)
        self.end_scene(sid)

    # ---------- 5. wax：标出差值，两行大数据 ----------
    def wax(self):
        sid = "wax"
        anims = []
        for k in KINDS:  # 条形图保持比例、上移收紧；数值淡出；图形缩成小图标放在条左边
            start, new_start = self.bars[k].get_start(), np.array([BAR_X0, WAX_Y[k], 0])
            anims += [
                self.bars[k].animate.shift(new_start - start),
                FadeOut(self.values[k]),
                self.big[k].animate.set_stroke(opacity=1, width=3).scale_to_fit_height(0.42).move_to(new_start + [-0.45, 0, 0]),
            ]
        self.play(*self.new_title(sid), *anims, run_time=0.6)

        hx = BAR_X0 + PERIM["hex"] * K_P  # 六边形那条的终点
        self.at(sid, "短")
        guide = DashedLine([hx, WAX_Y["tri"] + 0.35, 0], [hx, WAX_Y["hex"] - 0.35, 0], dash_length=0.12).set_stroke(AMBER, 4)
        self.play(Create(guide), run_time=0.4)
        self.at(sid, "蜂蜡")
        self.play(ShowPassingFlash(self.bars["hex"].copy().set_stroke(CREAM, 12), time_width=0.6), run_time=0.8)

        for d, y in zip(SCENES[sid]["data"], WAX_ROW_Y):
            k = kind_of(d["label"])
            self.at(sid, KIND_NAME[k])  # 念到“比正方形/比三角形”：多出来的那截亮起来
            extra = Line([hx, WAX_Y[k], 0], [BAR_X0 + PERIM[k] * K_P, WAX_Y[k], 0]).set_stroke(CREAM, 10).set_cap_style(CapStyleType.ROUND)
            self.play(Create(extra), run_time=0.4)

            self.at(sid, d["value"].lstrip("-"))  # 念到“7%/18%”：大号数据
            row = VGroup(
                txt(d["label"], 48, CREAM, t2c={KIND_NAME[k]: COLORS[k]}),
                txt(d["value"].replace("-", "−"), 110, AMBER, bold=True),
            ).arrange(RIGHT, buff=0.35, aligned_edge=DOWN)
            row.move_to([0, y, 0])
            self.play(FadeIn(row[0], shift=UP * 0.2), GrowFromCenter(row[1]), rate_func=rate_functions.ease_out_back, run_time=0.5)
        self.end_scene(sid)

    # ---------- 6. proof：1999，黑尔斯证明 ----------
    def proof(self):
        sid = "proof"
        d = SCENES[sid]["data"]
        old = self.everything_but_title()
        self.play(*self.new_title(sid), FadeOut(old), run_time=0.33)

        self.at(sid, d["year"])
        year = txt(d["year"], 190, AMBER, bold=True).move_to([0, 2.35, 0])
        self.play(Write(year), run_time=0.9)

        self.at(sid, "托马斯")
        cn, en = d["person"].rstrip("）").split("（")
        name = VGroup(txt(cn, 56, bold=True), txt(en, 34, MUTED)).arrange(DOWN, buff=0.22).move_to([0, 0.3, 0])
        self.play(FadeIn(name, shift=UP * 0.3), run_time=0.5)

        self.at(sid, "把")
        a, b = d["claim"].split("，", 1)
        lines = VGroup(txt(a + "，", 42), txt(b, 42, t2c={"正六边形": AMBER, "最短": AMBER})).arrange(DOWN, buff=0.18)
        box = RoundedRectangle(corner_radius=0.25, width=lines.width + 0.9, height=lines.height + 0.5)
        box.set_stroke(AMBER, 3).set_fill(CARD_BG, 1)
        VGroup(box, lines).move_to([0, -1.55, 0])
        self.play(FadeIn(box, scale=0.95), FadeIn(lines, shift=UP * 0.2), run_time=0.7)

        self.at(sid, "六边形")
        self.play(Indicate(lines[1][0:4], color=AMBER, scale_factor=1.15), run_time=0.6)
        self.at(sid, "总")  # 给“总周长最短”画下划线
        seg = lines[1][5:10]
        underline = Line(seg.get_corner(DL), seg.get_corner(DR)).shift(DOWN * 0.1).set_stroke(AMBER, 5)
        self.play(Create(underline), run_time=0.5)
        self.end_scene(sid)

    # ---------- 7. outro：蜂巢逐格灌满蜂蜜 ----------
    def outro(self):
        sid = "outro"
        old = self.everything_but_title()
        walls, honey = make_comb()
        self.play(*self.new_title(sid), FadeOut(old), run_time=0.4)
        # 念“用最少的蜂蜡”时一格格画出蜡壁，念完正好画完
        self.play(LaggedStart(*[Create(w) for w in walls], lag_ratio=0.05), run_time=word(sid, "围出") - self.renderer.time - 0.3)

        self.at(sid, "最大")  # 逐格灌蜂蜜（从中心往外）
        self.bring_to_back(*honey)
        self.play(LaggedStart(*[fill_up(h) for h in honey], lag_ratio=0.12), run_time=1.8)

        self.at(sid, "秘密")
        comb = VGroup(walls, *honey)
        self.play(comb.animate.scale(1.05), rate_func=there_and_back, run_time=0.8)

        # 最后一帧补到 ≥ 配音总长（finalize 会按 duration 截齐）
        self.wait_to(np.ceil(TL["duration"] * config.frame_rate) / config.frame_rate)
        print(f"  {sid:<10} 结束：应在 {SCENES[sid]['end']:.3f}s，实际 {self.renderer.time:.3f}s")
