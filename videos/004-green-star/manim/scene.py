"""004《为什么没有绿色的恒星》用 Manim 讲原理的部分（16 镜，横屏）。

分成五段，每段一个 Scene 类，各渲染成一个片段：
    Intro      s03                   光谱带展开，绿色在哪
    Temp       s04–s08               温度决定颜色；OBAFGKM 从蓝到红，中间没有绿
    Reveal     s09–s10、s12          维恩规律 → 反推绿色对应的温度 → 太阳峰值在绿色
    Principle  s14–s18               峰值≠颜色；普朗克曲线；0.99:1.00:0.88；三色混成白
    Closing    s22–s23               绿最强时红蓝也强；永远无法只偏绿

帧数按 timeline.json 精确计算，和着色器段拼起来正好等于配音长度。
画面元素绑定到配音里的词（word 函数），不写死秒数。

用法（在 videos/004-green-star 目录里）:
    uv run python -m manim render manim/scene.py Temp --format mp4
    低清快速预览：先设 PREVIEW=1
"""

import colorsys
import json
import os
from pathlib import Path

import numpy as np
from manim import *

from vlab import fonts

PREVIEW = os.environ.get("PREVIEW") == "1"
config.pixel_width, config.pixel_height = (960, 540) if PREVIEW else (1920, 1080)
config.frame_rate = 15 if PREVIEW else 30
config.frame_width, config.frame_height = 16, 9          # 横屏
config.background_color = "#070b16"
config.disable_caching = True

INK, DIM, GOLD = "#f1f3fa", "#9199b4", "#ffcd64"
GREEN, RED, BLUE = "#4ade80", "#f87171", "#60a5fa"
FONT = fonts.register_manim()          # 思源黑体，随仓库入库（微软雅黑不能商用发布）

TL = json.loads((Path(__file__).resolve().parent.parent / "build" / "green-star" / "timeline.json").read_text(encoding="utf-8"))
SCENES = {s["id"]: s for s in TL["scenes"]}
FPS = TL["fps"]


def word(sid, text, nth=1):
    """词的绝对开始时间。Edge TTS 分词和直觉不同，找不到会报错并列出可用的词。"""
    words = SCENES[sid]["words"]
    hits = [w for w in words if w["text"].strip() == text] or [w for w in words if text in w["text"]]
    if len(hits) < nth:
        raise KeyError(f"{sid} 里找不到第 {nth} 个「{text}」；可用：{[w['text'] for w in words]}")
    return hits[nth - 1]["start"]


def txt(s, fs, color=INK, bold=False):
    return Text(s, font=FONT, font_size=fs, color=color, weight=BOLD if bold else NORMAL)


def fit(m, max_w=14.5):
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


def _bb_raw(t):
    """Tanner Helland 的黑体近似，白点约 6500K。上限提到 40000K，否则 O 型星和 B 型星算出来一样。"""
    t = min(max(t, 1000.0), 40000.0) / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = (99.4708025861 * np.log(t) - 161.1195681661) if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * np.log(t - 10) - 305.0447927307)
    return [min(max(v, 0.0), 255.0) for v in (r, g, b)]


_A_WHITE = _bb_raw(8500)          # 天文学惯例：A 型星（约 8500K）算"白"


def blackbody_rgb(t, sat=1.35):
    """色温 → (r, g, b)，按天文学惯用叫法着色：以 A 型为白，这样 F 型是黄白、G 型是黄、K 型是橙，
    色块和它的标签才对得上。

    注意这和 sun.frag 故意不同：那边白点约 6500K，太阳在大气外看就是白的，那是片子要讲的事实；
    这里的色块讲的是"天文学家怎么叫"，两者的差距正是 s19–s21 要解释的东西。
    """
    raw = _bb_raw(t)
    c = [raw[i] / _A_WHITE[i] for i in range(3)]
    m = max(c)
    c = [v / m * 255.0 for v in c]
    mean = sum(c) / 3
    return tuple(int(min(max(mean + (v - mean) * sat, 0.0), 255.0)) for v in c)


def blackbody(t, sat=1.35):
    return "#%02x%02x%02x" % blackbody_rgb(t, sat)


def conventional_rgb(t, hue_deg=None):
    """按天文学惯用叫法着色。hue_deg 给了就把色相改到那个角度，饱和度和明度不动。

    只有 M 型用到：黑体在恒星温度范围内色相一直停在橙（约 32°，从 4200K 到 2400K 几乎不变，
    只差饱和度），算不出"红"。而"红巨星"的"红"是惯例叫法，和把太阳叫"黄"一样，
    所以 M 块单独推到红橙，让色块对得上它的标签和旁白里的"暗红"。
    """
    c = blackbody_rgb(t)
    if hue_deg is None:
        return c
    _, sat, val = colorsys.rgb_to_hsv(*[x / 255 for x in c])
    r, g, b = colorsys.hsv_to_rgb(hue_deg / 360, sat, val)
    return tuple(int(round(x * 255)) for x in (r, g, b))


# 普朗克定律，和 content/verify.py 用的是同一套公式
H_P, C_L, K_B = 6.62607015e-34, 2.99792458e8, 1.380649e-23


def planck(lam_nm, T):
    l = lam_nm * 1e-9
    return (2 * H_P * C_L ** 2) / l ** 5 / (np.exp(H_P * C_L / (l * K_B * T)) - 1)


class Segment(Scene):
    """按 timeline 精确对齐的基类：wait_to 补到某个绝对时间点。"""

    ids: list[str] = []

    @property
    def t0(self):
        return SCENES[self.ids[0]]["start"]

    def wait_to(self, abs_t, frozen=False):
        """补帧到绝对时间 abs_t。冻结帧和逐帧动画的取整方式不同，必须分开算。"""
        target = abs_t - self.t0
        now = self.renderer.time
        d = target - now
        if d <= 0:
            return
        frames = int(d * FPS) if frozen else int(np.ceil(d * FPS - 1e-9))
        if frames > 0:
            self.wait(frames / FPS)

    def finish(self):
        """补到本段最后一镜结束，保证片段长度和配音一致。"""
        end = SCENES[self.ids[-1]]["end"]
        n_target = round(end * FPS) - round(self.t0 * FPS)
        now_frames = round(self.renderer.time * FPS)
        if n_target > now_frames:
            self.wait((n_target - now_frames) / FPS)


def spectrum_bar(width=11.0, height=0.9, n=240):
    """连续可见光谱带：380–700 纳米按波长上真实颜色排列"""
    bar = VGroup()
    for i in range(n):
        f = i / (n - 1)
        lam = 380 + f * 320
        bar.add(Rectangle(width=width / n + 0.01, height=height, fill_opacity=1, stroke_width=0,
                          fill_color=wavelength_color(lam)))
    bar.arrange(RIGHT, buff=0)
    return bar


def wavelength_color(lam):
    """波长（纳米）→ 近似可见色。标准的 CIE 简化近似。"""
    if lam < 440:
        r, g, b = -(lam - 440) / 60, 0.0, 1.0
    elif lam < 490:
        r, g, b = 0.0, (lam - 440) / 50, 1.0
    elif lam < 510:
        r, g, b = 0.0, 1.0, -(lam - 510) / 20
    elif lam < 580:
        r, g, b = (lam - 510) / 70, 1.0, 0.0
    elif lam < 645:
        r, g, b = 1.0, -(lam - 645) / 65, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    if lam > 700:
        s = max(0.3, 1.0 - (lam - 700) / 100)
    elif lam < 420:
        s = max(0.3, 0.3 + 0.7 * (lam - 380) / 40)
    else:
        s = 1.0
    c = [int(255 * ((v * s) ** 0.8)) for v in (r, g, b)]
    return "#%02x%02x%02x" % tuple(c)


class Intro(Segment):
    """s03：恒星什么颜色都在发，绿色就在红和蓝中间，为什么偏偏没有"""

    ids = ["s03_why"]

    def construct(self):
        sid = "s03_why"
        bar = spectrum_bar().move_to(ORIGIN)
        frame = SurroundingRectangle(bar, color=DIM, stroke_width=2, buff=0.06)
        self.wait_to(word(sid, "恒星") - 0.3, frozen=True)
        self.play(Create(frame, run_time=0.5), FadeIn(bar, run_time=0.8))

        # 绿色区段高亮：500–565 纳米在 380–700 带子上的位置
        x0 = bar.get_left()[0] + bar.width * (500 - 380) / 320
        x1 = bar.get_left()[0] + bar.width * (565 - 380) / 320
        box = Rectangle(width=x1 - x0, height=bar.height + 0.5, color=GREEN, stroke_width=5)
        box.move_to([(x0 + x1) / 2, bar.get_center()[1], 0])
        tag = txt("绿色", 38, GREEN, bold=True).next_to(box, UP, buff=0.3)

        self.wait_to(word(sid, "绿色") - 0.2)
        self.play(Create(box, run_time=0.5), FadeIn(tag, shift=DOWN * 0.2, run_time=0.5))

        q = txt("为什么偏偏没有？", 58, INK, bold=True).next_to(bar, DOWN, buff=1.0)
        self.wait_to(word(sid, "为什么") - 0.2)
        self.play(FadeIn(q, shift=UP * 0.25, run_time=0.6))
        self.finish()


class Temp(Segment):
    """s04–s08：颜色来自温度，从蓝到红排一遍，中间没有绿"""

    ids = ["s04_temp", "s05_iron", "s06_class", "s07_class2", "s08_gap"]

    def construct(self):
        # 开场不留白：标题在第一个词之前就淡入
        title = txt("星星的颜色，来自温度", 72, INK, bold=True).move_to(UP * 2.9)
        self.play(FadeIn(title, shift=UP * 0.25, run_time=0.7))

        # s05 铁块加热：横屏放大，温度数字跟着走
        bar_w, bar_h = 4.6, 2.6
        block = RoundedRectangle(width=bar_w, height=bar_h, corner_radius=0.12,
                                 fill_opacity=1, stroke_width=0, fill_color=blackbody(1100))
        block.move_to(LEFT * 3.4 + DOWN * 0.5)
        glow = RoundedRectangle(width=bar_w + 0.5, height=bar_h + 0.5, corner_radius=0.2,
                                fill_opacity=0.18, stroke_width=0, fill_color=blackbody(1100))
        glow.move_to(block.get_center())
        temp_t = ValueTracker(1100)
        block.add_updater(lambda m: m.set_fill(blackbody(temp_t.get_value())))
        glow.add_updater(lambda m: m.set_fill(blackbody(temp_t.get_value())))
        num = always_redraw(lambda: txt(f"{int(temp_t.get_value()):,}", 104, GOLD, bold=True)
                            .move_to(RIGHT * 3.3 + DOWN * 0.3))
        unit = txt("度", 44, DIM).move_to(RIGHT * 3.3 + DOWN * 1.65)
        hint = txt("一块铁，烧得越热", 34, DIM).move_to(LEFT * 3.4 + DOWN * 2.6)

        self.wait_to(word("s05_iron", "铁") - 0.35)
        self.play(FadeIn(glow, run_time=0.4), FadeIn(block, run_time=0.4),
                  FadeIn(num, run_time=0.4), FadeIn(unit, run_time=0.4), FadeIn(hint, run_time=0.4))
        rt = max(1.2, word("s05_iron", "刺眼") - self.t0 - self.renderer.time + 0.4)
        self.play(temp_t.animate.set_value(12500), run_time=rt, rate_func=rate_functions.ease_in_out_sine)
        for m in (block, glow):
            m.clear_updaters()

        self.wait_to(SCENES["s06_class"]["start"] - 0.25)
        self.play(*[FadeOut(m, run_time=0.45) for m in (block, glow, num, unit, hint, title)])

        # s06、s07 光谱型色带：七块铺满横屏
        # 最后一项是色相覆盖：只有 M 用（黑体算不出"红"，见 conventional_rgb 的说明），其余保持纯黑体色
        classes = [("O", 35000, "蓝", None), ("B", 15000, "蓝白", None), ("A", 8500, "白", None),
                   ("F", 6800, "黄白", None), ("G", 5500, "黄", None), ("K", 4200, "橙", None),
                   ("M", 3000, "红", 15)]
        blocks = VGroup()
        for ch, T, name, hue in classes:
            r_, g_, b_ = conventional_rgb(T, hue)
            col = "#%02x%02x%02x" % (r_, g_, b_)
            dark = (0.299 * r_ + 0.587 * g_ + 0.114 * b_) < 175   # 按实际亮度决定字用亮色还是深色
            ink = INK if dark else "#1a1d2b"
            dim = "#cbd5e1" if dark else "#3f4659"
            cell = VGroup(
                Rectangle(width=2.0, height=3.4, fill_opacity=1, stroke_width=0, fill_color=col),
                txt(ch, 56, ink, bold=True),
                txt(name, 36, ink),
                txt(f"{T:,}°", 26, dim),
            )
            cell[1].move_to(cell[0].get_center() + UP * 1.05)
            cell[2].move_to(cell[0].get_center() + DOWN * 0.1)
            cell[3].move_to(cell[0].get_center() + DOWN * 1.15)
            blocks.add(cell)
        blocks.arrange(RIGHT, buff=0.16).move_to(DOWN * 0.35)
        for cell in blocks:                    # 先全部藏起来，逐个淡入时才显形，否则会留黑块占位
            cell.set_opacity(0)

        head = txt("天文学家把恒星按温度排了序", 46, DIM).move_to(UP * 3.0)
        self.play(FadeIn(head, run_time=0.4))

        def show(cell):
            """淡入一块：从半透明、略低的位置升上来"""
            cell.set_opacity(1).shift(DOWN * 0.35)
            return AnimationGroup(cell.animate.shift(UP * 0.35), FadeIn(cell, run_time=0.45))

        cues6 = [word("s06_class", "蓝色"), word("s06_class", "蓝白"), word("s06_class", "白色")]
        cues7 = [word("s07_class2", "黄白"), word("s07_class2", "黄"),
                 word("s07_class2", "橙"), word("s07_class2", "暗红")]
        for i, c in enumerate(cues6 + cues7):
            self.wait_to(c - 0.3)
            self.play(show(blocks[i]), run_time=0.45)

        note = fit(txt("恒星光谱型 OBAFGKM · 颜色按天文学惯例，以 A 型为白 · 温度边界各来源略有差异", 24, DIM), 14.0)
        note.next_to(blocks, DOWN, buff=0.4)
        self.play(FadeIn(note, run_time=0.4))

        # s08 从蓝到红扫一遍，再指出绿色的缺口
        sweep = Arrow(blocks[0].get_top() + UP * 0.35 + LEFT * 0.2,
                      blocks[-1].get_top() + UP * 0.35 + RIGHT * 0.2,
                      buff=0, color=DIM, stroke_width=4, max_tip_length_to_length_ratio=0.04)
        self.wait_to(word("s08_gap", "从") - 0.25)
        self.play(Create(sweep, run_time=min(1.8, max(0.6, word("s08_gap", "红") - word("s08_gap", "从")))))

        gap = Rectangle(width=2.0, height=3.4, color=GREEN, stroke_width=6).move_to(blocks[4].get_center())
        qmark = txt("绿？", 62, GREEN, bold=True).move_to(gap.get_center())
        # 缺口和"绿？"跟着"这一整串颜色里"出，结论跟着"没有"出。
        # 原来三样都挤在"没有"之后，结论标题完整显示只有 0.6 秒就切镜了。
        self.wait_to(word("s08_gap", "整") - 0.3)
        self.play(blocks[4].animate.set_opacity(0.14), Create(gap, run_time=0.5))
        self.play(FadeIn(qmark, scale=0.65, run_time=0.4))
        self.wait_to(word("s08_gap", "没有") - 0.3)
        self.play(FadeOut(head, run_time=0.3),
                  FadeIn(txt("这一整串颜色里，没有绿", 58, GOLD, bold=True).move_to(UP * 3.0),
                         shift=DOWN * 0.2, run_time=0.5))
        self.finish()


class Reveal(Segment):
    """s09–s10、s12：温度越高波长越短 → 反推绿色对应的温度 → 太阳的峰值就在绿色"""

    ids = ["s09_wien", "s10_calc"]

    def construct(self):
        # 波长轴（380–700 纳米），下面压一条真实颜色的光谱带
        ax_w = 12.0
        axis = NumberLine(x_range=[380, 700, 40], length=ax_w, include_numbers=False,
                          color=DIM, stroke_width=3).move_to(DOWN * 1.2)
        bar = spectrum_bar(width=ax_w, height=0.55).move_to(axis.get_center() + DOWN * 0.55)
        lab_l = txt("380 纳米", 24, DIM).next_to(bar, LEFT, buff=0.25)
        lab_r = txt("700 纳米", 24, DIM).next_to(bar, RIGHT, buff=0.25)

        head = txt("温度越高，发光最强的波长越短", 54, INK, bold=True).move_to(UP * 3.0)
        self.play(FadeIn(head, run_time=0.6))
        self.wait_to(word("s09_wien", "规律") - 0.3)
        self.play(Create(axis, run_time=0.5), FadeIn(bar, run_time=0.5),
                  FadeIn(lab_l, run_time=0.4), FadeIn(lab_r, run_time=0.4))

        def x_of(lam):
            return axis.n2p(lam)[0]

        # 峰值标记随温度移动：温度升高，标记向短波（左）走
        T = ValueTracker(3000)
        B_WIEN = 2.897771955e-3

        def peak_nm(t):
            return B_WIEN / t * 1e9

        marker = always_redraw(lambda: VGroup(
            Line([x_of(np.clip(peak_nm(T.get_value()), 380, 700)), bar.get_bottom()[1] - 0.15, 0],
                 [x_of(np.clip(peak_nm(T.get_value()), 380, 700)), axis.get_center()[1] + 1.6, 0],
                 color=GOLD, stroke_width=5),
            txt(f"{int(T.get_value()):,} 度", 40, GOLD, bold=True)
            .move_to([np.clip(x_of(np.clip(peak_nm(T.get_value()), 380, 700)), -6.4, 6.4),
                      axis.get_center()[1] + 2.1, 0]),
        ))
        self.wait_to(word("s09_wien", "温度", nth=2) - 0.3)
        self.play(FadeIn(marker, run_time=0.4))
        rt = max(1.0, word("s09_wien", "短") - self.t0 - self.renderer.time + 0.3)
        self.play(T.animate.set_value(11000), run_time=rt, rate_func=rate_functions.ease_in_out_sine)
        marker.clear_updaters()
        self.play(FadeOut(marker, run_time=0.4))

        # s10 反推：绿色区间 → 温度区间
        self.wait_to(word("s10_calc", "倒") - 0.3)
        self.play(FadeOut(head, run_time=0.4))
        head2 = txt("反过来问：峰值落在绿色，要多少度？", 50, INK, bold=True).move_to(UP * 3.0)
        self.play(FadeIn(head2, run_time=0.5))

        gx0, gx1 = x_of(500), x_of(565)
        gbox = Rectangle(width=gx1 - gx0, height=bar.height + 1.5, color=GREEN, stroke_width=6)
        gbox.move_to([(gx0 + gx1) / 2, bar.get_center()[1] + 0.45, 0])
        gtag = txt("绿色 500–565 纳米", 32, GREEN, bold=True).next_to(gbox, UP, buff=0.25)
        self.wait_to(word("s10_calc", "绿色") - 0.3)
        self.play(Create(gbox, run_time=0.5), FadeIn(gtag, run_time=0.5))

        ans = txt("5100 – 5800 度", 92, GOLD, bold=True).move_to(UP * 1.2)
        self.wait_to(word("s10_calc", "五千一百度") - 0.3)
        self.play(FadeIn(ans, scale=0.8, run_time=0.6))
        self.finish()


class Sun(Segment):
    """s12：太阳的峰值就在绿色，它本该是一颗绿色的恒星"""

    ids = ["s12_peak"]

    def construct(self):
        ax_w = 12.0
        axis = NumberLine(x_range=[380, 700, 40], length=ax_w, color=DIM, stroke_width=3).move_to(DOWN * 1.4)
        bar = spectrum_bar(width=ax_w, height=0.55).move_to(axis.get_center() + DOWN * 0.55)
        self.play(FadeIn(axis, run_time=0.4), FadeIn(bar, run_time=0.4))

        x_peak = axis.n2p(502)[0]
        line = Line([x_peak, bar.get_bottom()[1] - 0.2, 0], [x_peak, 1.4, 0], color=GOLD, stroke_width=6)
        dot = Dot([x_peak, 1.4, 0], radius=0.12, color=GOLD)
        lab = VGroup(txt("太阳的峰值", 40, GOLD, bold=True), txt("502 纳米", 34, INK)).arrange(DOWN, buff=0.18)
        lab.move_to([x_peak, 2.4, 0])
        self.wait_to(word("s12_peak", "波长") - 0.3)
        self.play(Create(line, run_time=0.5), FadeIn(dot, run_time=0.3), FadeIn(lab, run_time=0.5))

        box = Rectangle(width=axis.n2p(565)[0] - axis.n2p(500)[0], height=bar.height + 0.4,
                        color=GREEN, stroke_width=5)
        box.move_to([(axis.n2p(565)[0] + axis.n2p(500)[0]) / 2, bar.get_center()[1], 0])
        self.wait_to(word("s12_peak", "绿色") - 0.25)
        self.play(Create(box, run_time=0.45))

        concl = txt("它本该是一颗绿色的恒星", 62, GREEN, bold=True).move_to(UP * 3.1)
        self.wait_to(word("s12_peak", "本该") - 0.3)
        self.play(FadeIn(concl, shift=DOWN * 0.2, run_time=0.6))
        self.finish()


class Principle(Segment):
    """s14–s18：峰值不等于颜色 → 普朗克曲线 → 0.99:1.00:0.88 → 三色混成白"""

    ids = ["s14_wrong", "s15_curve", "s16_data", "s17_equal", "s18_mix"]

    def construct(self):
        T_SUN = 5772
        peak_val = planck(502, T_SUN)

        # s14 那个错误的假设
        eq = VGroup(txt("发光最强的颜色", 54, INK, bold=True),
                    txt("＝", 54, DIM),
                    txt("我们看到的颜色", 54, INK, bold=True)).arrange(RIGHT, buff=0.5).move_to(UP * 0.4)
        tag = txt("一开始的假设", 34, DIM).next_to(eq, UP, buff=0.6)
        self.wait_to(word("s14_wrong", "假设") - 0.4)
        self.play(FadeIn(tag, run_time=0.4), FadeIn(eq, run_time=0.6))

        cross = Line(eq.get_corner(UL) + RIGHT * 0.3, eq.get_corner(DR) + LEFT * 0.3,
                     color="#ef4444", stroke_width=9)
        wrong = txt("这个假设是错的", 58, "#ef4444", bold=True).next_to(eq, DOWN, buff=1.0)
        self.wait_to(word("s14_wrong", "错") - 0.35)
        self.play(Create(cross, run_time=0.45), FadeIn(wrong, run_time=0.45))
        self.wait_to(SCENES["s15_curve"]["start"] - 0.3)
        self.play(*[FadeOut(m, run_time=0.45) for m in (eq, tag, cross, wrong)])

        # s15 普朗克曲线：峰值只是最强的，不是唯一的
        ax = Axes(x_range=[380, 700, 50], y_range=[0, 1.18, 0.5], x_length=11.5, y_length=5.0,
                  axis_config={"color": DIM, "stroke_width": 3, "include_ticks": False},
                  tips=False).move_to(DOWN * 0.6)
        curve = ax.plot(lambda x: planck(x, T_SUN) / peak_val, x_range=[380, 700, 2],
                        color=GOLD, stroke_width=7)
        area = ax.get_area(curve, x_range=[380, 700], color=GOLD, opacity=0.13)
        band = spectrum_bar(width=11.5, height=0.4).move_to(ax.c2p(540, 0) + DOWN * 0.42)
        xlab = txt("波长（纳米）", 26, DIM).next_to(band, DOWN, buff=0.28)

        head = txt("太阳在整个可见光范围里都在发光", 50, INK, bold=True).move_to(UP * 3.1)
        self.play(FadeIn(head, run_time=0.5))
        self.wait_to(word("s15_curve", "整个") - 0.35)
        self.play(Create(ax, run_time=0.5), FadeIn(band, run_time=0.5), FadeIn(xlab, run_time=0.4))
        self.play(Create(curve, run_time=0.9), FadeIn(area, run_time=0.7))

        pk = DashedLine(ax.c2p(502, 0), ax.c2p(502, 1.0), color=INK, stroke_width=4, dash_length=0.12)
        pklab = txt("峰值 502", 28, INK).next_to(pk, UP, buff=0.1)
        self.wait_to(word("s15_curve", "峰值") - 0.3)
        self.play(Create(pk, run_time=0.4), FadeIn(pklab, run_time=0.4))
        # 曲线这么平不是画错了，正是这一段要讲的：整个可见光范围都差不多强
        flat = txt("纵轴从 0 开始：整条曲线都很高，峰值并不突出", 26, DIM).next_to(ax, DOWN, buff=0.95)
        self.play(FadeIn(flat, run_time=0.45))

        # s16 三段强度：蓝 450、绿 550、红 650
        self.wait_to(SCENES["s16_data"]["start"] - 0.3)
        self.play(FadeOut(head, run_time=0.4), FadeOut(pk, run_time=0.4),
                  FadeOut(pklab, run_time=0.4), FadeOut(flat, run_time=0.4))
        head2 = txt("太阳在三段的实际强度", 50, INK, bold=True).move_to(UP * 3.1)
        self.play(FadeIn(head2, run_time=0.45))

        bands = [(450, BLUE, "蓝光", "0.99"), (550, GREEN, "绿光", "1.00"), (650, RED, "红光", "0.88")]
        marks = VGroup()
        for lam, col, name, val in bands:
            y = planck(lam, T_SUN) / peak_val
            marks.add(VGroup(Line(ax.c2p(lam, 0), ax.c2p(lam, y), color=col, stroke_width=16),
                             Dot(ax.c2p(lam, y), radius=0.1, color=col)))

        cues = [word("s16_data", "蓝光"), word("s16_data", "绿"), word("s16_data", "红光")]
        for i, c in enumerate(cues):
            self.wait_to(c - 0.3)
            self.play(FadeIn(marks[i], run_time=0.4))

        # 数值跟着念出来落定
        vals = VGroup()
        for lam, col, name, val in bands:
            y = planck(lam, T_SUN) / peak_val
            vals.add(txt(val, 44, col, bold=True).move_to(ax.c2p(lam, y) + UP * 0.55))
        nums = [word("s16_data", "零点九九"), word("s16_data", "一点零零"), word("s16_data", "零点八八")]
        for i, c in enumerate(nums):
            self.wait_to(c - 0.3)
            self.play(FadeIn(vals[i], shift=UP * 0.2, run_time=0.4))

        # s17 三者几乎相等：换成并排柱子，差距一眼可见
        self.wait_to(SCENES["s17_equal"]["start"] - 0.3)
        self.play(*[FadeOut(m, run_time=0.5) for m in (ax, curve, area, band, xlab, marks, vals, head2)])

        chart = VGroup()
        for lam, col, name, val in bands:
            y = planck(lam, T_SUN) / peak_val
            r = Rectangle(width=1.5, height=y * 3.4, fill_opacity=1, stroke_width=0, fill_color=col)
            g = VGroup(r, txt(val, 52, col, bold=True), txt(name, 32, DIM))
            g[1].next_to(r, UP, buff=0.25)
            g[2].next_to(r, DOWN, buff=0.25)
            chart.add(g)
        chart.arrange(RIGHT, buff=1.6, aligned_edge=DOWN).move_to(DOWN * 0.7)

        head3 = txt("几乎一样多", 70, INK, bold=True).move_to(UP * 3.0)
        self.play(FadeIn(head3, run_time=0.4),
                  *[FadeIn(g, shift=UP * 0.3, run_time=0.5) for g in chart])
        top = max(g[0].get_top()[1] for g in chart)
        level = DashedLine([chart[0].get_left()[0] - 0.4, top, 0],
                           [chart[2].get_right()[0] + 0.4, top, 0],
                           color=DIM, stroke_width=3, dash_length=0.12)
        self.wait_to(word("s17_equal", "一点点") - 0.5)
        self.play(Create(level, run_time=0.5))
        note = txt("450 / 550 / 650 纳米处的相对强度，由普朗克定律算出", 24, DIM).move_to(DOWN * 3.4)
        self.play(FadeIn(note, run_time=0.4))

        # s18 三色混成白
        self.wait_to(SCENES["s18_mix"]["start"] - 0.3)
        self.play(*[FadeOut(m, run_time=0.45) for m in (chart, level, head3, note)])
        # 加法混色：三个圆都用亮色、高不透明度，看着像光而不是颜料
        R_ = 1.7
        circles = VGroup(
            Circle(radius=R_, fill_opacity=0.72, stroke_width=0, fill_color="#ff5a5a").move_to(UP * 1.0),
            Circle(radius=R_, fill_opacity=0.72, stroke_width=0, fill_color="#4ade80").move_to(DOWN * 0.55 + LEFT * 1.45),
            Circle(radius=R_, fill_opacity=0.72, stroke_width=0, fill_color="#5aa9ff").move_to(DOWN * 0.55 + RIGHT * 1.45),
        )
        self.wait_to(word("s18_mix", "当红") - 0.35)
        for c in circles:
            self.play(FadeIn(c, scale=0.7, run_time=0.3))
        white = Circle(radius=0.8, fill_opacity=1, stroke_width=0, fill_color="#ffffff").move_to(UP * 0.0)
        wlab = txt("白色", 54, "#12151f", bold=True).move_to(white.get_center())
        self.wait_to(word("s18_mix", "白色") - 0.4)
        self.play(FadeIn(white, scale=0.6, run_time=0.5), FadeIn(wlab, run_time=0.5))
        self.finish()


class Closing(Segment):
    """s22–s23：绿色最强时红蓝也强；一颗恒星永远无法只偏绿"""

    ids = ["s22_answer", "s23_never"]

    def construct(self):
        T_SUN = 5772
        peak_val = planck(502, T_SUN)
        ax = Axes(x_range=[380, 700, 50], y_range=[0, 1.2, 0.5], x_length=11.0, y_length=3.6,
                  axis_config={"color": DIM, "stroke_width": 3, "include_ticks": False},
                  tips=False).move_to(DOWN * 0.55)
        curve = ax.plot(lambda x: planck(x, T_SUN) / peak_val, x_range=[380, 700, 2],
                        color=GOLD, stroke_width=6)
        band = spectrum_bar(width=11.0, height=0.4).move_to(ax.c2p(540, 0) + DOWN * 0.42)
        self.play(Create(ax, run_time=0.5), Create(curve, run_time=0.8), FadeIn(band, run_time=0.5))

        head = txt("不是绿色缺席了", 56, INK, bold=True).move_to(UP * 3.2)
        self.wait_to(word("s22_answer", "缺席") - 0.4)
        self.play(FadeIn(head, run_time=0.5))

        cols = [(450, BLUE), (550, GREEN), (650, RED)]
        lines = VGroup(*[Line(ax.c2p(l, 0), ax.c2p(l, planck(l, T_SUN) / peak_val), color=c, stroke_width=16)
                         for l, c in cols])
        self.wait_to(word("s22_answer", "绿色", nth=2) - 0.3)
        self.play(FadeIn(lines[1], run_time=0.35))
        self.wait_to(word("s22_answer", "红光") - 0.25)
        self.play(FadeIn(lines[0], run_time=0.35), FadeIn(lines[2], run_time=0.35))

        concl = txt("绿色最强时，红光和蓝光一定也很强", 46, GOLD, bold=True).move_to(UP * 2.4)
        self.play(FadeIn(concl, run_time=0.5))
        dot = Dot(ax.c2p(540, 1.12), radius=0.2, color="#ffffff")
        self.wait_to(word("s22_answer", "白色") - 0.35)
        self.play(FadeIn(dot, scale=0.5, run_time=0.45))

        # s23 红、蓝两条曲线各自存在，绿色单峰画不出来
        self.wait_to(SCENES["s23_never"]["start"] - 0.3)
        self.play(*[FadeOut(m, run_time=0.45) for m in (head, concl, dot, lines, curve)])
        final = txt("一颗恒星可以偏红，可以偏蓝", 50, INK, bold=True).move_to(UP * 3.2)
        self.play(FadeIn(final, run_time=0.5))

        c_red = ax.plot(lambda x: planck(x, 3300) / planck(700, 3300) * 0.92, x_range=[380, 700, 2],
                        color=RED, stroke_width=5)
        c_blue = ax.plot(lambda x: planck(x, 13000) / planck(380, 13000) * 0.92, x_range=[380, 700, 2],
                         color=BLUE, stroke_width=5)
        self.wait_to(word("s23_never", "偏红") - 0.3)
        self.play(Create(c_red, run_time=0.5))
        self.wait_to(word("s23_never", "偏蓝") - 0.3)
        self.play(Create(c_blue, run_time=0.5))

        # 色带在 ax 下方 0.42，这句要再往下让开，否则压在色带上看不清
        never = txt("但永远没办法只偏绿", 58, GREEN, bold=True).move_to(DOWN * 3.75)
        self.wait_to(word("s23_never", "永远") - 0.35)
        self.play(FadeIn(never, shift=UP * 0.2, run_time=0.6))
        self.finish()
