"""Manim 模板库：读工程文件里的一个镜头，按模板布局、按词出场、按风格上色。

由 build.py 调用（每次渲染一个镜头），通过环境变量传参：
    VK_PROJECT  工程文件路径      VK_SCENE  镜头 id      VK_STYLE  风格文件（可选，覆盖工程里写的）
    PREVIEW=1   低清预览

模板只负责"布局 + 把元素按名字登记"，出场时机来自工程的 cues，颜色字号动画来自风格文件。
新增模板：写一个函数返回 (元素字典, 默认入场方式字典)，登记到 TEMPLATES，再在 project.py 的
TEMPLATE_PARAMS 里写上必填参数。
"""

import json
import os
import sys
from pathlib import Path

from manim import *

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from project import Project, resolve_color  # noqa: E402

PREVIEW = os.environ.get("PREVIEW") == "1"
config.pixel_width, config.pixel_height = (540, 960) if PREVIEW else (1080, 1920)
config.frame_rate = 15 if PREVIEW else 30
config.frame_width, config.frame_height = 9, 16
config.disable_caching = True

PROJ = Project(os.environ["VK_PROJECT"], os.environ.get("VK_STYLE") or None)
SID = os.environ["VK_SCENE"]
SPEC = next(s for s in PROJ.scenes if s["id"] == SID)
TLS = next(s for s in json.loads(PROJ.timeline_path.read_text(encoding="utf-8"))["scenes"] if s["id"] == SID)
ST = PROJ.style
config.background_color = ST["palette"]["bg"]

EASING = {"smooth": rate_functions.smooth, "snappy": rate_functions.ease_out_cubic,
          "bouncy": rate_functions.ease_out_back, "linear": rate_functions.linear}


# ---------- 小工具 ----------
def C(name):
    return resolve_color(ST, name)


def T(s, size, color="ink", bold=False):
    return Text(str(s), font=ST["font"]["family"], font_size=size, color=C(color), weight=BOLD if bold else NORMAL)


def fit(m, max_w=8.2):
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


def word_time(text, nth=1):
    words = TLS["words"]
    hits = [w for w in words if w["text"].strip() == text] or [w for w in words if text in w["text"]]
    if len(hits) < nth:
        raise KeyError(f"镜头 {SID} 的配音里找不到第 {nth} 个「{text}」（配音切出的词：{[w['text'] for w in words]}）")
    return hits[nth - 1]["start"]


def title_mob(text):
    return fit(T(text, ST["font"]["title_size"], "ink", bold=True)).move_to(UP * ST["layout"]["title_y"])


# ---------- 模板：返回 (元素字典, 默认入场方式) ----------
def title_card(p):
    cy = ST["layout"]["content_y"]
    els, anims = {}, {}
    if p.get("kicker"):
        els["kicker"] = T(p["kicker"], ST["font"]["body_size"] * 0.8, "dim")
    els["title"] = fit(T(p["title"], ST["font"]["title_size"] * 1.5, "ink", bold=True))
    els["rule"] = Line(LEFT * 1.6, RIGHT * 1.6, color=C(p.get("rule_color", "accent2")), stroke_width=6)
    if p.get("subtitle"):
        els["subtitle"] = fit(T(p["subtitle"], ST["font"]["body_size"] * 1.1, p.get("subtitle_color", "accent1")))
    VGroup(*els.values()).arrange(DOWN, buff=0.45).move_to(UP * (cy + 0.6))
    anims.update(rule="grow_h", title="write")
    return els, anims


def bar_compare(p):
    cy = ST["layout"]["content_y"]
    els, anims = {"title": title_mob(p["title"])}, {}
    bars = p["bars"]
    vmax = max(b["value"] for b in bars)
    height, width, gap = p.get("max_height", 4.0), 1.3, p.get("gap", 1.5)
    base = cy - 2.2
    xs = [(i - (len(bars) - 1) / 2) * (width + gap) for i in range(len(bars))]
    els["axis"] = Line([xs[0] - width, base, 0], [xs[-1] + width, base, 0], color=C("dim"), stroke_width=3)
    anims["axis"] = "fade"
    for x, b in zip(xs, bars):
        rect = Rectangle(width=width, height=max(0.02, height * b["value"] / vmax), stroke_width=0,
                         fill_color=C(b.get("color", "accent2")), fill_opacity=0.92)
        rect.move_to([x, base, 0], aligned_edge=DOWN)
        label = T(b.get("label", b["name"]), ST["font"]["body_size"] * 0.7, b.get("color", "accent2"), bold=True)
        fit(label, width + gap - 0.15).next_to(rect, DOWN, buff=0.18)                    # 标签不超过柱间距，避免互相压住
        value = T(b.get("value_label", f"{b['value']:g}"), ST["font"]["body_size"] * 0.8, "ink").next_to(rect, UP, buff=0.15)
        els[f"bars.{b['name']}"] = VGroup(rect, label, value)
        anims[f"bars.{b['name']}"] = "grow"
    if p.get("callout"):
        top = max((els[f"bars.{b['name']}"] for b in bars), key=lambda g: g[0].height)
        els["callout"] = T(p["callout"], ST["font"]["title_size"] * 1.05, p.get("callout_color", "accent1"), bold=True)
        els["callout"].next_to(top[0], RIGHT, buff=0.35).align_to(top[0], UP)
        anims["callout"] = "pop"
    if p.get("caption"):
        els["caption"] = fit(T(p["caption"], ST["font"]["body_size"] * 0.85, "dim")).move_to(UP * (cy + 3.3))
    return els, anims


def bullet_list(p):
    cy = ST["layout"]["content_y"]
    els, anims = {"title": title_mob(p["title"])}, {}
    accents = ["accent1", "accent2", "accent3"]
    rows = []
    for i, item in enumerate(p["items"]):
        dot = Dot(radius=0.12, color=C(accents[i % 3]))
        text = T(item, ST["font"]["body_size"], "ink")
        row = VGroup(dot, text).arrange(RIGHT, buff=0.35)
        rows.append(row)
        els[f"items.{i}"] = row
    group = VGroup(*rows).arrange(DOWN, buff=0.7, aligned_edge=LEFT)
    fit(group).move_to(UP * cy)
    return els, anims


TEMPLATES = {"title_card": title_card, "bar_compare": bar_compare, "bullet_list": bullet_list}


# ---------- 入场动画 ----------
def enter(m, kind, dur):
    rf = EASING.get(ST["motion"]["easing"], rate_functions.smooth)
    kw = dict(run_time=dur, rate_func=rf)
    if kind == "fade":
        return FadeIn(m, **kw)
    if kind == "pop":
        return GrowFromCenter(m, run_time=dur, rate_func=rate_functions.ease_out_back)
    if kind == "write":
        return Write(m, **kw)
    if kind == "grow_h":
        return GrowFromCenter(m, **kw)
    if kind == "grow":
        if isinstance(m, VGroup) and len(m) == 3 and isinstance(m[0], Rectangle):     # 柱子：柱身从底部长出，标签淡入
            return AnimationGroup(GrowFromEdge(m[0], DOWN, **kw), FadeIn(m[1], **kw), FadeIn(m[2], shift=UP * 0.2, **kw))
        return GrowFromEdge(m, DOWN, **kw)
    return FadeIn(m, shift=UP * 0.3, **kw)                                              # fade_up


class SpecScene(Scene):
    def wait_abs(self, t):
        fps = config.frame_rate
        n = round(t * fps) - self.f0 - round(self.renderer.time * fps)
        if n > 0:
            self.wait((n + 0.5) / fps, frozen_frame=True)
        elif n < 0:
            print(f"  [晚了] {SID}：想在 {t:.3f}s，镜头内已到 {self.renderer.time:.3f}s")

    def construct(self):
        self.f0 = round(TLS["start"] * config.frame_rate)
        bg = Rectangle(width=config.frame_width, height=config.frame_height, stroke_width=0)
        bg.set_fill([C("bg2"), C("bg")], opacity=1).set_sheen_direction(DOWN)                # 上 bg2 → 下 bg 的渐变
        self.add(bg)

        els, default_anims = TEMPLATES[SPEC["template"]](SPEC.get("params") or {})
        for name, o in (SPEC.get("overrides") or {}).items():                           # 精修：位置、缩放、颜色
            if name not in els:
                raise KeyError(f"镜头 {SID} 的 overrides 里没有元素「{name}」，可用：{list(els)}")
            els[name].shift(RIGHT * o.get("dx", 0) + UP * o.get("dy", 0))
            if "scale" in o:
                els[name].scale(o["scale"])
            if "color" in o:
                els[name].set_color(C(o["color"]))

        cues = SPEC.get("cues") or {}
        for name in cues:
            if name not in els:
                raise KeyError(f"镜头 {SID} 的 cues 里没有元素「{name}」，可用：{list(els)}")
        m = ST["motion"]
        t0 = TLS["start"] + 0.1
        schedule, k = [], 0
        for name, mob in els.items():
            cue = cues.get(name) or {}
            if cue.get("on"):
                t = word_time(cue["on"], cue.get("nth", 1)) + cue.get("offset", 0.0)
            else:
                t = t0 + m["stagger"] * k + cue.get("offset", 0.0)
                k += 1
            schedule.append((t, name, mob, cue.get("anim") or default_anims.get(name) or m["enter"]))
        # 时间上挨在一起（间隔小于一个入场时长）的元素合成一组同时播，组内按各自的延迟错开
        schedule.sort(key=lambda x: x[0])
        batches = []
        for item in schedule:
            if batches and item[0] - batches[-1][0][0] < m["duration"]:
                batches[-1].append(item)
            else:
                batches.append([item])
        for batch in batches:
            t_b = batch[0][0]
            self.wait_abs(t_b)
            parts = []
            for t, name, mob, kind in batch:
                a = enter(mob, kind, m["duration"])
                d = t - t_b
                parts.append(Succession(Wait(run_time=d), a) if d > 1e-3 else a)
            self.play(AnimationGroup(*parts))
        self.wait_abs(TLS["end"])
