"""timeline.json → HyperFrames 合成（index.html + 素材），做法②：HTML + GSAP。

画面全由时间轴驱动：每个分镜是一个 clip，关键元素在念到对应的词时出现；
字幕也是 HTML（逐条弹入、正在念的词高亮）；配音用 <audio> 放进合成，
HyperFrames 用 Chrome 逐帧截图，直接出带声音的成片。

用法（在 video-lab 目录下）:
    uv run --frozen python 2_hyperframes/build.py [id]            # 只生成，默认 hexagon
    uv run --frozen python 2_hyperframes/build.py [id] --render   # 生成 + lint + 渲染
产物:  2_hyperframes/index.html、2_hyperframes/assets/
       out/<id>_2_hyperframes.mp4（--render 时）

换稿子：重跑 shared/tts.py 得到新的 timeline.json，再跑本脚本即可。
带 data 的分镜按数据形状自动选画面（数字列表 → 条形图，文字列表 → 大号数据卡，
{year, person, claim} → 年份/人物/结论）；hook/tiling/question/outro 是本题专属插画，
换题目时要换成新的插画函数（没有对应插画的分镜会退回通用画面）。
"""

import html
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# 配色（统一视觉规范）
BG, AMBER, CREAM, MUTED = "#15110E", "#F5A524", "#FFF4E0", "#B8A890"
TRI, SQR, HEX = "#6C8CFF", "#34C3A0", "#F5A524"
COLOR = {"tri": TRI, "sqr": SQR, "hex": HEX, None: CREAM}

# 图形区（像素）：x 80–1000，y 520–1260；标题区 240–440；字幕区约 1300–1480
STAGE_W, STAGE_H = 920, 740

# 面积 = 1 时三种正多边形的边长
SIDE = {"tri": 1.5197, "sqr": 1.0, "hex": 0.6204}


# ---------- 小工具 ----------


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def num(x: float) -> str:
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def js(v) -> str:
    """Python 值 → JS 字面量（键不加引号）。"""
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {js(x)}" for k, x in v.items()) + " }"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return num(v)
    return json.dumps(v, ensure_ascii=False)


class Timeline:
    """收集 GSAP 调用，全部按整片的绝对时间（秒）摆放。"""

    def __init__(self):
        self.lines: list[str] = []

    def note(self, text: str):
        self.lines.append(f"\n// {text}")

    def fromto(self, sel: str, a: dict, b: dict, t: float):
        self.lines.append(f'tl.fromTo("{sel}", {js(a)}, {js(b)}, {num(t)});')

    def to(self, sel: str, b: dict, t: float):
        self.lines.append(f'tl.to("{sel}", {js(b)}, {num(t)});')

    def set(self, sel: str, b: dict, t: float):
        self.lines.append(f'tl.set("{sel}", {js(b)}, {num(t)});')


def when(sc: dict, match, after: float | None = None, default: float | None = None, what: str = "") -> float:
    """按文字在分镜的词里找关键词，返回念到它的时刻；找不到就退回 default。"""
    after = sc["start"] if after is None else after
    for w in sc["words"]:
        if w["start"] >= after - 1e-6 and match(w["text"]):
            return w["start"]
    t = sc["voice_start"] if default is None else default
    print(f"  [提示] 分镜 {sc['id']} 没找到「{what}」，改用 {t:.2f}s")
    return t


def text_em(s: str) -> float:
    """粗估一行字的宽度（单位：字号）。汉字和全角标点算 1，其余算 0.6。"""
    return sum(0.3 if ch == " " else 1.0 if ord(ch) > 0x2E7F else 0.6 for ch in s)


def shape_of(label: str):
    for key, kind in (("三角", "tri"), ("方", "sqr"), ("六边", "hex")):
        if key in label:
            return kind
    return None


# ---------- 几何 ----------


def pts(points) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def regular(cx, cy, r, n, rot=-90.0):
    """正 n 边形顶点（外接圆半径 r；rot 是第一个顶点的角度，-90 = 尖朝上）。"""
    return [
        (cx + r * math.cos(math.radians(rot + 360 * k / n)), cy + r * math.sin(math.radians(rot + 360 * k / n)))
        for k in range(n)
    ]


def perimeter(points) -> float:
    return sum(math.dist(points[k], points[(k + 1) % len(points)]) for k in range(len(points)))


def dash(length: float, width: float):
    """「描边」动画的虚线参数：空白段比整条线还长，起始偏移再多让出半个线宽，
    这样圆头线帽不会在开画前就露出一个点。返回 (stroke-dasharray, 起始 dashoffset)。"""
    return f"{length:.1f} {length + 2 * width:.1f}", length + width


def origin(**kw) -> dict:
    """SVG 元素缩放用的变换原点。起止两头都要写，并关掉 smoothOrigin：
    否则 GSAP 在元素缩放为 0 时才切换原点，会补一个位移，整组图形跑偏。"""
    return {**kw, "smoothOrigin": False}


def icon(kind, size=56) -> str:
    """小图标：三角形 / 正方形 / 正六边形。"""
    if kind is None:
        return ""
    p = {"tri": regular(50, 58, 46, 3), "sqr": regular(50, 50, 50, 4, -45), "hex": regular(50, 50, 47, 6, 0)}[kind]
    c = COLOR[kind]
    return (
        f'<svg class="icon" width="{size}" height="{size}" viewBox="0 0 100 100">'
        f'<polygon points="{pts(p)}" fill="{c}" fill-opacity="0.25" stroke="{c}" stroke-width="7" stroke-linejoin="round"/></svg>'
    )


def hex_cluster(cx, cy, r, rings=2):
    """六边形簇（尖顶朝上的格子，rings=2 时 19 格），按「由内向外、顺时针」排好。"""
    cells = []
    for q in range(-rings, rings + 1):
        for row in range(max(-rings, -q - rings), min(rings, -q + rings) + 1):
            x = cx + r * math.sqrt(3) * (q + row / 2)
            y = cy + r * 1.5 * row
            ring = max(abs(q), abs(row), abs(q + row))
            angle = math.atan2(x - cx, cy - y) % (2 * math.pi)  # 从正上方起顺时针
            cells.append((ring, round(angle, 6), x, y))
    cells.sort()
    return [(x, y) for _, _, x, y in cells]


def comb_svg(prefix, cells, rc, honey_ids) -> str:
    """蜂巢簇 SVG。每格 = 深色底 + 蜂蜜（裁在格子里，靠平移往上涨）+ 琥珀色壁。"""
    defs, body = [], []
    for i, (x, y) in enumerate(cells):
        cell = pts(regular(x, y, rc, 6))
        honey = ""
        if i in honey_ids:
            defs.append(f'<clipPath id="{prefix}-k{i}"><polygon points="{pts(regular(x, y, rc - 3, 6))}"/></clipPath>')
            box = f'x="{x - rc:.1f}" y="{y - rc:.1f}" width="{2 * rc:.1f}"'
            honey = (
                f'<g clip-path="url(#{prefix}-k{i})"><g id="{prefix}-h{i}">'
                f'<rect {box} height="{2 * rc:.1f}" fill="url(#honey)"/>'
                f'<rect {box} height="7" fill="#FFE3A0" opacity="0.85"/></g></g>'
            )
        body.append(f'<g id="{prefix}-c{i}"><polygon class="cell-bg" points="{cell}"/>{honey}<polygon class="cell-wall" points="{cell}"/></g>')
    return (
        f'<svg class="stage-svg" width="{STAGE_W}" height="{STAGE_H}" viewBox="0 0 {STAGE_W} {STAGE_H}">'
        f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>'
    )


def tiles(kind, w, h):
    """在 w×h 的面板里铺满一种正多边形；按到中心的距离排序，动画就会由内向外长出来。"""
    cx, cy = w / 2, h / 2
    polys = []
    if kind == "tri":
        s = 84
        th = s * math.sqrt(3) / 2
        n, m = int(w / s) + 2, int(h / th / 2) + 2
        for j in range(-m, m + 1):
            yt, yb = cy + (j - 0.5) * th, cy + (j + 0.5) * th
            for k in range(-n, n + 1):
                ax = cx + k * s + (j % 2) * s / 2
                polys.append([(ax, yt), (ax + s / 2, yb), (ax - s / 2, yb)])  # 尖朝上
                polys.append([(ax, yt), (ax + s, yt), (ax + s / 2, yb)])  # 尖朝下
    elif kind == "sqr":
        s = 76
        n, m = int(w / s / 2) + 2, int(h / s / 2) + 2
        for j in range(-m, m + 1):
            for k in range(-n, n + 1):
                x, y = cx + k * s, cy + j * s
                polys.append([(x - s / 2, y - s / 2), (x + s / 2, y - s / 2), (x + s / 2, y + s / 2), (x - s / 2, y + s / 2)])
    else:
        r = 46
        dx, dy = r * math.sqrt(3), r * 1.5
        n, m = int(w / dx / 2) + 2, int(h / dy / 2) + 2
        for j in range(-m, m + 1):
            for k in range(-n, n + 1):
                polys.append(regular(cx + (k + (j % 2) / 2) * dx, cy + j * dy, r, 6))

    def inside(p):
        xs, ys = [x for x, _ in p], [y for _, y in p]
        return max(xs) > 1 and min(xs) < w - 1 and max(ys) > 1 and min(ys) < h - 1

    def dist(p):
        return math.hypot(sum(x for x, _ in p) / len(p) - cx, sum(y for _, y in p) / len(p) - cy)

    return sorted((p for p in polys if inside(p)), key=dist)


# ---------- 各分镜画面（返回图形区的 HTML，同时往时间线里加动画） ----------


def scene_hook(sc, sid, tl, tlj):
    """开场：一簇蜂巢，格子由内向外弹出；念到「六边形」时部分格子灌上蜂蜜。"""
    t0 = sc["start"]
    r = 84
    rc = r * 0.93  # 格子之间留点缝
    cells = hex_cluster(STAGE_W / 2, STAGE_H / 2, r)
    honey = {0: 1.0, 2: 0.8, 5: 0.6, 7: 0.9, 10: 0.5, 13: 0.75, 15: 0.65, 18: 0.85}  # 格子序号: 蜂蜜高度
    svg = comb_svg(sid, cells, rc, honey)
    for i, (x, y) in enumerate(cells):
        o = origin(svgOrigin=f"{x:.1f} {y:.1f}")
        tl.fromto(f"#{sid}-c{i}", {"scale": 0, "opacity": 0, **o},
                  {"scale": 1, "opacity": 1, "duration": 0.5, "ease": "back.out(1.7)", **o}, t0 + 0.1 + i * 0.045)
    t = when(sc, lambda w: "六边形" in w, what="六边形")
    for k, (i, level) in enumerate(honey.items()):
        tl.fromto(f"#{sid}-h{i}", {"y": 2 * rc}, {"y": (1 - level) * 2 * rc, "duration": 0.9, "ease": "power2.out"}, t + k * 0.07)
    tl.fromto(f"#{sid}-stage", {"scale": 0.95}, {"scale": 1.03, "duration": sc["end"] - t0, "ease": "sine.inOut"}, t0)
    return svg


TILING = [("tri", "三角形", "三角形"), ("sqr", "正方形", "正方形"), ("hex", "正六边形", "六边形")]  # 形状, 标签, 念到哪个词


def scene_tiling(sc, sid, tl, tlj):
    """能密铺的三种正多边形：先摆三个空面板，念到哪个就铺满哪个。"""
    t0 = sc["start"]
    pw, ph, gap = 280, 440, 40
    top = (STAGE_H - ph - 84) / 2
    parts, cursor, t = [], t0, t0
    for i, (kind, label, key) in enumerate(TILING):
        x = i * (pw + gap)
        polys = "".join(f'<polygon points="{pts(p)}"/>' for p in tiles(kind, pw, ph))
        parts.append(
            f'<div class="panel" id="{sid}-p{i}" style="left:{x}px; top:{top:.0f}px; width:{pw}px; height:{ph}px; --c:{COLOR[kind]}">'
            f'<svg width="{pw}" height="{ph}" viewBox="0 0 {pw} {ph}">{polys}</svg>'
            f'<div class="panel-q" id="{sid}-q{i}">?</div></div>'
            f'<div class="panel-label" id="{sid}-l{i}" style="left:{x}px; top:{top + ph + 22:.0f}px; width:{pw}px; color:{COLOR[kind]}">{label}</div>'
        )
        tl.fromto(f"#{sid}-p{i}", {"opacity": 0, "y": 50}, {"opacity": 1, "y": 0, "duration": 0.5, "ease": "power3.out"}, t0 + 0.3 + i * 0.12)
        t = when(sc, lambda w, k=key: k in w, after=cursor, default=cursor + 1, what=key)
        cursor = t
        tl.to(f"#{sid}-q{i}", {"opacity": 0, "scale": 0.4, "duration": 0.25, "ease": "power2.in"}, t)
        o = origin(transformOrigin="50% 50%")
        tl.fromto(f"#{sid}-p{i} polygon", {"scale": 0, "opacity": 0, **o},
                  {"scale": 1, "opacity": 1, "duration": 0.4, "ease": "back.out(2)", "stagger": 0.007, **o}, t)
        tl.fromto(f"#{sid}-l{i}", {"opacity": 0, "y": 24}, {"opacity": 1, "y": 0, "duration": 0.4, "ease": "power2.out"}, t + 0.15)
    # 六边形那块最后亮一下
    last = len(TILING) - 1
    tl.to(f"#{sid}-p{last}", {"borderColor": "rgba(245,165,36,0.9)", "boxShadow": "0 0 48px rgba(245,165,36,0.4)",
                              "scale": 1.05, "duration": 0.5, "ease": "power2.out"}, t + 0.9)
    return "".join(parts)


def scene_question(sc, sid, tl, tlj):
    """面积相同的三个图形（按真实比例），先描边再上色；念到「谁」时冒出大问号。"""
    t0 = sc["start"]
    unit = 200  # 面积 1 = 200×200 像素
    widths = {"tri": SIDE["tri"] * unit, "sqr": SIDE["sqr"] * unit, "hex": 2 * SIDE["hex"] * unit}
    gap = 60
    x = (STAGE_W - sum(widths.values()) - 2 * gap) / 2
    base = 457  # 三个图形底边对齐
    shapes = []
    for i, kind in enumerate(("tri", "sqr", "hex")):
        cx = x + widths[kind] / 2
        side = SIDE[kind] * unit
        if kind == "tri":
            R = side / math.sqrt(3)
            p = regular(cx, base - R / 2, R, 3)
        elif kind == "sqr":
            p = regular(cx, base - side / 2, side / math.sqrt(2), 4, -45)
        else:
            p = regular(cx, base - side * math.sqrt(3) / 2, side, 6, 0)
        da, off = dash(perimeter(p), 6)
        c = COLOR[kind]
        shapes.append(
            f'<polygon class="q-shape" id="{sid}-s{i}" points="{pts(p)}" style="fill:{c}; stroke:{c}" stroke-dasharray="{da}"/>'
            f'<text class="q-label" id="{sid}-t{i}" x="{cx:.1f}" y="{base + 66}">面积 = 1</text>'
        )
        tl.fromto(f"#{sid}-s{i}", {"strokeDashoffset": off}, {"strokeDashoffset": 0, "duration": 0.8, "ease": "power2.inOut"}, t0 + 0.2 + i * 0.2)
        tl.fromto(f"#{sid}-s{i}", {"fillOpacity": 0}, {"fillOpacity": 0.22, "duration": 0.5, "ease": "power1.out"}, t0 + 0.9 + i * 0.2)
        x += widths[kind] + gap
    t_area = when(sc, lambda w: "面积" in w, what="面积")
    for i in range(3):
        tl.fromto(f"#{sid}-t{i}", {"opacity": 0, "y": 16}, {"opacity": 1, "y": 0, "duration": 0.4, "ease": "power2.out"}, t_area + i * 0.12)
    t_who = when(sc, lambda w: "谁" in w, what="谁")
    tl.to(f"#{sid}-g", {"y": 120, "duration": 0.6, "ease": "power3.inOut"}, t_who - 0.15)
    tl.fromto(f"#{sid}-mark", {"opacity": 0, "scale": 0.2, "rotation": -30},
              {"opacity": 1, "scale": 1, "rotation": 0, "duration": 0.7, "ease": "back.out(2.2)"}, t_who)
    return (
        f'<div class="q-mark" id="{sid}-mark">?</div>'
        f'<svg class="stage-svg" width="{STAGE_W}" height="{STAGE_H}" viewBox="0 0 {STAGE_W} {STAGE_H}"><g id="{sid}-g">{"".join(shapes)}</g></svg>'
    )


def scene_outro(sc, sid, tl, tlj):
    """结尾：蜂巢格子从「最少」开始逐个灌满蜂蜜，「最大」时镜头推近，「秘密」时整簇发光。"""
    t0 = sc["start"]
    r = 84
    rc = r * 0.93
    cells = hex_cluster(STAGE_W / 2, STAGE_H / 2, r)
    svg = comb_svg(sid, cells, rc, set(range(len(cells))))
    for i, (x, y) in enumerate(cells):
        o = origin(svgOrigin=f"{x:.1f} {y:.1f}")
        tl.fromto(f"#{sid}-c{i}", {"scale": 0, "opacity": 0, **o},
                  {"scale": 1, "opacity": 1, "duration": 0.4, "ease": "back.out(1.6)", **o}, t0 + 0.05 + i * 0.025)
    t_a = when(sc, lambda w: "最少" in w, what="最少")
    t_b = when(sc, lambda w: "最大" in w, after=t_a, what="最大")
    t_c = when(sc, lambda w: "秘密" in w, after=t_b, what="秘密")
    step = (t_c - t_a - 0.6) / (len(cells) - 1)
    for i in range(len(cells)):
        tl.fromto(f"#{sid}-h{i}", {"y": 2 * rc}, {"y": 0, "duration": 0.7, "ease": "power2.out"}, t_a + i * step)
    tl.fromto(f"#{sid}-stage", {"scale": 1}, {"scale": 1.06, "duration": 2.0, "ease": "power2.inOut"}, t_b)
    tl.fromto(f"#{sid}-glow", {"opacity": 0, "scale": 0.7}, {"opacity": 1, "scale": 1.1, "duration": 1.2, "ease": "power2.out"}, t_c)
    return f'<div class="glow" id="{sid}-glow"></div>{svg}'


def scene_bars(sc, sid, tl, tlj):
    """横向条形图：念到名称时出这一行，念到数字时条长出来（条长与数值成正比，从 0 起）。"""
    data = sc["data"]
    values = [d["value"] for d in data]
    vmax = max(values)
    decimals = max((len(f"{v:g}".split(".")[1]) if "." in f"{v:g}" else 0) for v in values)
    row_h, gap, full = 160, 70, 900
    top = (STAGE_H - len(data) * row_h - (len(data) - 1) * gap) / 2
    rows, cursor, t_val = [], sc["start"], sc["start"]
    for i, d in enumerate(data):
        kind, label = shape_of(d["label"]), d["label"]
        length = d["value"] / vmax * full
        rows.append(
            f'<div class="bar-row" style="top:{top + i * (row_h + gap):.0f}px">'
            f'<div class="bar-head" id="{sid}-h{i}" style="color:{COLOR[kind]}">{icon(kind)}<span>{esc(label)}</span></div>'
            f'<div class="bar-track" id="{sid}-t{i}"></div>'
            f'<div class="bar" id="{sid}-b{i}" style="width:{length:.0f}px; background:{COLOR[kind]}">'
            f'<span class="bar-val" data-layout-allow-overflow>{d["value"]:.{decimals}f}</span></div></div>'  # 条没长出来时被裁掉，属正常
        )
        t_lab = when(sc, lambda w, lab=label: w in lab, after=cursor, default=cursor + 0.5, what=label)
        spoken = f"{d['value']:g}"
        t_val = when(sc, lambda w, v=spoken: w == v, after=t_lab, default=t_lab + 0.8, what=spoken)
        cursor = t_val
        tl.fromto(f"#{sid}-h{i}", {"opacity": 0, "x": -40}, {"opacity": 1, "x": 0, "duration": 0.45, "ease": "power3.out"}, t_lab)
        tl.fromto(f"#{sid}-t{i}", {"opacity": 0}, {"opacity": 1, "duration": 0.4, "ease": "power1.out"}, t_lab)
        tl.fromto(f"#{sid}-b{i}", {"width": 0}, {"width": round(length), "duration": 0.9, "ease": "power3.out"}, t_val)
    # 数值最小的一行（这里是正六边形）最后亮一下
    best = values.index(min(values))
    tl.to(f"#{sid}-b{best}", {"boxShadow": "0 0 44px rgba(245,165,36,0.6)", "duration": 0.5, "ease": "power2.out"}, t_val + 1.0)
    return "".join(rows)


def scene_stats(sc, sid, tl, tlj):
    """大号数据卡：上方描一个蜂蜡格子；念到标签时出卡片，念到数字时数字砸下来。"""
    data = sc["data"]
    n = len(data)
    gap = 36
    card_h = min(240, (STAGE_H - 200 - (n - 1) * gap) / n)
    top = STAGE_H - n * card_h - (n - 1) * gap
    p = regular(STAGE_W / 2, top / 2, 64, 6, 0)
    da, off = dash(perimeter(p), 10)
    parts = [
        f'<svg class="stage-svg" width="{STAGE_W}" height="{top:.0f}" viewBox="0 0 {STAGE_W} {top:.0f}">'
        f'<polygon class="wax" id="{sid}-wax" points="{pts(p)}" stroke-dasharray="{da}"/></svg>'
    ]
    tl.fromto(f"#{sid}-wax", {"strokeDashoffset": off}, {"strokeDashoffset": 0, "duration": 1.2, "ease": "power2.inOut"}, sc["start"] + 0.5)
    tl.fromto(f"#{sid}-wax", {"fillOpacity": 0}, {"fillOpacity": 0.25, "duration": 0.6, "ease": "power1.out"}, sc["start"] + 1.5)
    cursor = sc["start"]
    for i, d in enumerate(data):
        label, value = d["label"], str(d["value"])
        shown = re.sub(r"^-", "−", value)  # 用真正的减号
        parts.append(
            f'<div class="stat-card" id="{sid}-c{i}" style="top:{top + i * (card_h + gap):.0f}px; height:{card_h:.0f}px">'
            f'<div class="stat-label">{icon(shape_of(label), 64)}<span>{esc(label)}</span></div>'
            f'<div class="stat-num" id="{sid}-n{i}">{esc(shown)}</div></div>'
        )
        t_lab = when(sc, lambda w, lab=label: w in lab, after=cursor, default=cursor + 0.5, what=label)
        key = value.lstrip("-+−")
        t_val = when(sc, lambda w, k=key: k in w, after=t_lab, default=t_lab + 1.0, what=key)
        cursor = t_val
        tl.fromto(f"#{sid}-c{i}", {"opacity": 0, "y": 60}, {"opacity": 1, "y": 0, "duration": 0.5, "ease": "power3.out"}, t_lab)
        tl.fromto(f"#{sid}-n{i}", {"opacity": 0, "scale": 2.2}, {"opacity": 1, "scale": 1, "duration": 0.5, "ease": "back.out(1.4)"}, t_val)
        tl.to(f"#{sid}-c{i}", {"borderColor": "rgba(245,165,36,0.75)", "duration": 0.4, "ease": "power1.out"}, t_val)
    return "".join(parts)


def scene_fact(sc, sid, tl, tlj):
    """年份 → 人物 → 结论（按字幕行逐句出现），最后画个勾。"""
    d = sc["data"]
    year, person, claim = str(d.get("year", "")), d.get("person", ""), d.get("claim", "")
    name, _, sub = person.partition("（")
    lines = re.findall(r"[^，,]+[，,]?", claim)
    size = min(58, 680 / max(text_em(s) for s in lines))
    claim_html = "".join(
        f'<div id="{sid}-l{i}" class="{"claim-hl" if i == len(lines) - 1 else ""}">{esc(s)}</div>' for i, s in enumerate(lines)
    )
    ring_da, ring_off = dash(2 * math.pi * 46, 8)
    tick_da, tick_off = dash(math.dist((30, 57), (46, 73)) + math.dist((46, 73), (79, 37)), 8)
    t_year = when(sc, lambda w: year and year in w, what=year)
    t_person = when(sc, lambda w: len(w) >= 2 and w in person, after=t_year, default=t_year + 1.2, what=person)
    later = [c["start"] for c in tlj["cues"] if t_person < c["start"] < sc["end"]]  # 人物之后的字幕行
    times = [later[i] if i < len(later) else t_person + 1.5 * (i + 1) for i in range(len(lines))]
    t_check = sc["words"][-1]["start"]
    tl.fromto(f"#{sid}-year", {"opacity": 0, "scale": 0.4}, {"opacity": 1, "scale": 1, "duration": 0.6, "ease": "back.out(1.8)"}, t_year)
    tl.fromto(f"#{sid}-person", {"opacity": 0, "y": 40}, {"opacity": 1, "y": 0, "duration": 0.5, "ease": "power3.out"}, t_person)
    tl.fromto(f"#{sid}-claim", {"opacity": 0, "y": 50}, {"opacity": 1, "y": 0, "duration": 0.5, "ease": "power3.out"}, times[0])
    for i, t in enumerate(times):
        tl.fromto(f"#{sid}-l{i}", {"opacity": 0, "x": -24}, {"opacity": 1, "x": 0, "duration": 0.45, "ease": "power2.out"}, t)
    tl.fromto(f"#{sid}-ring", {"strokeDashoffset": ring_off}, {"strokeDashoffset": 0, "duration": 0.45, "ease": "power2.inOut"}, t_check)
    tl.fromto(f"#{sid}-tick", {"strokeDashoffset": tick_off}, {"strokeDashoffset": 0, "duration": 0.35, "ease": "power2.out"}, t_check + 0.35)
    return (
        f'<div class="fact-year" id="{sid}-year">{esc(year)}</div>'
        f'<div class="fact-person" id="{sid}-person"><div class="fact-name">{esc(name)}</div>'
        f'<div class="fact-sub">{esc(sub.rstrip("）"))}</div></div>'
        f'<div class="claim" id="{sid}-claim"><div class="claim-text" style="font-size:{size:.0f}px">{claim_html}</div>'
        f'<svg class="check" width="110" height="110" viewBox="0 0 110 110">'
        f'<circle id="{sid}-ring" cx="55" cy="55" r="46" stroke-dasharray="{ring_da}"/>'
        f'<polyline id="{sid}-tick" points="30,57 46,73 79,37" stroke-dasharray="{tick_da}"/></svg></div>'
    )


def scene_generic(sc, sid, tl, tlj):
    """没有专门画面的分镜：在图形区慢慢描出一个六边形。"""
    p = regular(STAGE_W / 2, STAGE_H / 2, 220, 6, 0)
    da, off = dash(perimeter(p), 10)
    tl.fromto(f"#{sid}-hex", {"strokeDashoffset": off}, {"strokeDashoffset": 0, "duration": 1.5, "ease": "power2.inOut"}, sc["start"] + 0.3)
    return (
        f'<svg class="stage-svg" width="{STAGE_W}" height="{STAGE_H}" viewBox="0 0 {STAGE_W} {STAGE_H}">'
        f'<polygon class="wax" id="{sid}-hex" points="{pts(p)}" stroke-dasharray="{da}"/></svg>'
    )


ILLUSTRATIONS = {"hook": scene_hook, "tiling": scene_tiling, "question": scene_question, "outro": scene_outro}


def pick(sc):
    """本题专属插画按分镜 id 选；带数据的分镜按数据形状选；都不是就用通用画面。"""
    if sc["id"] in ILLUSTRATIONS:
        return ILLUSTRATIONS[sc["id"]]
    data = sc.get("data")
    if isinstance(data, list) and data and all(isinstance(d.get("value"), (int, float)) for d in data):
        return scene_bars
    if isinstance(data, list) and data:
        return scene_stats
    if isinstance(data, dict) and "claim" in data:
        return scene_fact
    return scene_generic


def headline(text: str):
    """标题：一行放得下就 80px（或 76px）；放不下就在靠中间的标点后断成两行。"""
    for size in (80, 76):
        if text_em(text) * size <= 900:
            return size, esc(text)
    cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "，、：；？！,:;"]
    if not cuts:
        return 76, esc(text)
    k = min(cuts, key=lambda c: abs(c - len(text) / 2))
    return 76, esc(text[:k]) + "<br>" + esc(text[k:].strip())


def scene(sc, tl, tlj, first: bool, last: bool) -> str:
    sid = f"sc-{sc['id']}"
    t0, t1 = sc["start"], sc["end"]
    tl.note(f"分镜 {sc['id']}：{t0:.2f}s – {t1:.2f}s")
    size, title = headline(sc["headline"])
    if first:  # 第一帧就有标题（抖音默认拿第一帧当封面），只做个回弹
        tl.fromto(f"#{sid}-title", {"scale": 1.1}, {"scale": 1, "duration": 0.8, "ease": "power3.out"}, t0)
    else:
        tl.fromto(f"#{sid}-title", {"opacity": 0, "y": 36}, {"opacity": 1, "y": 0, "duration": 0.55, "ease": "power3.out"}, t0 + 0.05)
    tl.fromto(f"#{sid}-accent", {"scaleX": 0}, {"scaleX": 1, "duration": 0.5, "ease": "power2.out"}, t0 + 0.25)
    stage = pick(sc)(sc, sid, tl, tlj)
    fade = 0.5 if last else 0.25  # 分镜结束前淡出，切到下一个
    tl.to(f"#{sid}-inner", {"opacity": 0, "y": -24, "duration": fade, "ease": "power2.in"}, t1 - fade)
    return f"""
    <section id="{sid}" class="clip scene" data-start="{num(t0)}" data-duration="{num(t1 - t0)}" data-track-index="1">
      <div class="scene-inner" id="{sid}-inner">
        <div class="headline" id="{sid}-title" style="font-size:{size}px"><div>{title}</div><div class="hl-accent" id="{sid}-accent"></div></div>
        <div class="stage" id="{sid}-stage">{stage}</div>
      </div>
    </section>"""


def subtitles(tlj, tl) -> str:
    """字幕：每条一个 clip，弹入；正在念的词变成琥珀色（用 words 的时间点）。"""
    words = [w for sc in tlj["scenes"] for w in sc["words"]]
    tl.note("字幕：逐条弹入，正在念的词高亮")
    out = []
    for i, c in enumerate(tlj["cues"]):
        text, pos, spans, parts = c["text"], 0, [], []
        for w in (w for w in words if c["start"] - 1e-3 <= w["start"] < c["end"] - 1e-3):
            k = text.find(w["text"], pos)
            if k < 0:
                continue
            parts += [esc(text[pos:k]), f'<span id="w{i}-{len(spans)}">{esc(w["text"])}</span>']
            spans.append(w)
            pos = k + len(w["text"])
        parts.append(esc(text[pos:]))
        out.append(
            f'    <div id="cue{i}" class="clip cue" data-start="{num(c["start"])}" data-duration="{num(c["end"] - c["start"])}" '
            f'data-track-index="2" data-track-kind="captions"><div class="cue-line" id="cl{i}">{"".join(parts)}</div></div>'
        )
        tl.fromto(f"#cl{i}", {"opacity": 0, "y": 28, "scale": 0.92},
                  {"opacity": 1, "y": 0, "scale": 1, "duration": 0.22, "ease": "back.out(2)"}, c["start"])
        for j, w in enumerate(spans):
            tl.set(f"#w{i}-{j}", {"color": AMBER}, w["start"])
            if j + 1 < len(spans):
                tl.set(f"#w{i}-{j}", {"color": "#FFFFFF"}, spans[j + 1]["start"])
    return "\n".join(out)


def background(total: float) -> str:
    """背景：暖黑 + 淡淡的琥珀光晕 + 很淡的蜂巢纹理（整片缓慢上移）。"""
    r = 64
    w, h = r * math.sqrt(3), 3 * r
    hexes = "".join(f'<polygon points="{pts(regular(x, y, r, 6))}"/>' for x, y in [(0, 0), (w, 0), (w / 2, 1.5 * r), (0, h), (w, h)])
    return f"""
    <div id="bg" class="clip" data-start="0" data-duration="{num(total)}" data-track-index="0" data-layout-ignore>
      <div class="bg-pattern">
        <svg id="bg-hex" class="bg-hex" width="1080" height="2240" viewBox="0 0 1080 2240">
          <defs><pattern id="hexgrid" width="{w:.2f}" height="{h:.2f}" patternUnits="userSpaceOnUse">{hexes}</pattern></defs>
          <rect width="1080" height="2240" fill="url(#hexgrid)"/>
        </svg>
      </div>
      <div class="bg-glow"></div>
    </div>"""


CSS = """
@font-face { font-family: "Microsoft YaHei"; src: local("Microsoft YaHei"), local("MicrosoftYaHei"); font-weight: 400; }
@font-face { font-family: "Microsoft YaHei"; src: local("Microsoft YaHei Bold"), local("MicrosoftYaHei-Bold"); font-weight: 700; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1080px; height: 1920px; overflow: hidden; background: var(--bg); }
#root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: var(--bg);
  font-family: "Microsoft YaHei", sans-serif; color: var(--cream); }
.defs { position: absolute; width: 0; height: 0; }

/* 背景 */
#bg, .scene, .scene-inner { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }
.bg-pattern { position: absolute; inset: 0; overflow: hidden;
  -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 45%, #000 20%, transparent 100%);
  mask-image: radial-gradient(ellipse 80% 60% at 50% 45%, #000 20%, transparent 100%); }
.bg-hex { position: absolute; left: 0; top: 0; }
.bg-hex polygon { fill: none; stroke: rgba(245, 165, 36, 0.07); stroke-width: 2; }
.bg-glow { position: absolute; inset: 0;
  background: radial-gradient(ellipse 75% 42% at 50% 46%, rgba(245, 165, 36, 0.13), rgba(245, 165, 36, 0) 72%); }

/* 标题区 y 240–440，图形区 y 520–1260 */
.headline { position: absolute; left: 80px; top: 240px; width: 920px; height: 200px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center; font-weight: 700; line-height: 1.22; color: var(--cream); }
.headline > div { flex: none; }  /* 两行标题会超出 200px，不让 flex 把下面的短横压没 */
.hl-accent { width: 72px; height: 8px; margin-top: 20px; border-radius: 4px; background: var(--amber); }
.stage { position: absolute; left: 80px; top: 520px; width: 920px; height: 740px; }
.stage-svg { position: absolute; left: 0; top: 0; overflow: visible; }

/* 蜂巢 */
.cell-bg { fill: #221A12; }
.cell-wall { fill: none; stroke: var(--amber); stroke-width: 6; stroke-linejoin: round; }
.glow { position: absolute; left: 60px; top: -30px; width: 800px; height: 800px; border-radius: 50%;
  background: radial-gradient(circle, rgba(245, 165, 36, 0.38), rgba(245, 165, 36, 0) 68%); }

/* 密铺面板 */
.panel { position: absolute; border-radius: 28px; overflow: hidden; background: rgba(255, 244, 224, 0.035);
  border: 2px solid rgba(255, 244, 224, 0.12); box-shadow: 0 0 0 rgba(245, 165, 36, 0); }
.panel svg { position: absolute; left: -2px; top: -2px; }
.panel polygon { fill: var(--c); fill-opacity: 0.2; stroke: var(--c); stroke-width: 3; stroke-linejoin: round; }
.panel-q { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 130px; font-weight: 700; color: rgba(184, 168, 144, 0.55); }
.panel-label { position: absolute; height: 62px; line-height: 62px; text-align: center; font-size: 46px; font-weight: 700; }

/* 等面积 */
.q-shape { fill-opacity: 0; stroke-width: 6; stroke-linejoin: round; stroke-linecap: round; }
.q-label { font-size: 40px; font-weight: 700; fill: var(--muted); text-anchor: middle; }
.q-mark { position: absolute; left: 0; top: 0; width: 920px; height: 300px; line-height: 300px; text-align: center;
  font-size: 250px; font-weight: 700; color: var(--amber); }

/* 条形图 */
.bar-row { position: absolute; left: 0; width: 920px; height: 160px; }
.bar-head { position: absolute; left: 0; top: 0; height: 60px; display: flex; align-items: center; gap: 16px;
  font-size: 46px; font-weight: 700; }
.bar-track { position: absolute; left: 0; top: 72px; width: 900px; height: 88px; border-radius: 44px;
  background: rgba(255, 244, 224, 0.06); }
.bar { position: absolute; left: 0; top: 72px; height: 88px; border-radius: 44px; overflow: hidden;
  box-shadow: 0 0 0 rgba(245, 165, 36, 0); }
.bar-val { position: absolute; right: 30px; top: 0; line-height: 88px; font-size: 54px; font-weight: 700; color: #15110E; }

/* 数据卡 */
.wax { fill: var(--amber); fill-opacity: 0; stroke: var(--amber); stroke-width: 10; stroke-linejoin: round; stroke-linecap: round; }
.stat-card { position: absolute; left: 0; width: 920px; padding: 0 56px; display: flex; align-items: center;
  justify-content: space-between; border-radius: 32px; background: rgba(255, 244, 224, 0.045);
  border: 2px solid rgba(255, 244, 224, 0.1); }
.stat-label { display: flex; align-items: center; gap: 18px; font-size: 52px; font-weight: 700; color: var(--cream); }
.stat-num { font-size: 168px; line-height: 1; font-weight: 700; color: var(--amber); }

/* 年份 / 人物 / 结论 */
.fact-year { position: absolute; left: 0; top: 0; width: 920px; height: 230px; line-height: 230px; text-align: center;
  font-size: 210px; font-weight: 700; color: var(--amber); letter-spacing: 6px; }
.fact-person { position: absolute; left: 0; top: 250px; width: 920px; text-align: center; }
.fact-name { font-size: 66px; font-weight: 700; color: var(--cream); line-height: 1.3; }
.fact-sub { font-size: 38px; color: var(--muted); letter-spacing: 2px; line-height: 1.4; }
.claim { position: absolute; left: 0; top: 460px; width: 920px; height: 260px; padding: 0 40px 0 56px; display: flex;
  align-items: center; justify-content: space-between; border-radius: 32px; background: rgba(245, 165, 36, 0.08);
  border: 2px solid rgba(245, 165, 36, 0.35); }
.claim-text { font-weight: 700; line-height: 1.45; color: var(--cream); }
.claim-hl { color: var(--amber); }
.check { flex: none; }
.check circle, .check polyline { fill: none; stroke: var(--amber); stroke-width: 8; stroke-linecap: round; stroke-linejoin: round; }

/* 字幕区 y ≈ 1300–1480 */
.cue { position: absolute; left: 0; top: 1290px; width: 1080px; height: 200px; display: flex; align-items: center;
  justify-content: center; }
.cue-line { font-size: 64px; font-weight: 700; color: #FFFFFF; white-space: nowrap; max-width: 980px; letter-spacing: 1px;
  text-shadow: 3px 0 0 #0D0A08, -3px 0 0 #0D0A08, 0 3px 0 #0D0A08, 0 -3px 0 #0D0A08, 2px 2px 0 #0D0A08,
    -2px 2px 0 #0D0A08, 2px -2px 0 #0D0A08, -2px -2px 0 #0D0A08, 0 6px 16px rgba(0, 0, 0, 0.7); }
"""

PAGE = """<!doctype html>
<html lang="zh-CN" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>__TITLE__</title>
    <!-- 由 build.py 根据 timeline.json 生成，不要手改 -->
    <script src="assets/gsap.min.js"></script>
    <style>
:root { __VARS__ }
__CSS__
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-fps="__FPS__" data-width="1080" data-height="1920">
    <svg class="defs" width="0" height="0" aria-hidden="true"><defs>
      <linearGradient id="honey" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFC94A"/><stop offset="1" stop-color="#E5890A"/></linearGradient>
    </defs></svg>
__BG__
__SCENES__
__SUBS__
    <audio id="narration" src="assets/narration.wav" data-start="0" data-duration="__DUR__" data-track-index="3"></audio>
    </div>
    <script>
const tl = gsap.timeline({ paused: true });
__TWEENS__

window.__timelines = window.__timelines || {};
window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def build(tid: str) -> Path:
    tlj = json.loads((ROOT / "build" / tid / "timeline.json").read_text(encoding="utf-8"))
    total = tlj["duration"]

    assets = HERE / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "build" / tid / "narration.wav", assets / "narration.wav")
    shutil.copy2(HERE / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")

    tl = Timeline()
    tl.note("背景：蜂巢纹理整片缓慢上移")
    tl.fromto("#bg-hex", {"y": 0}, {"y": -240, "duration": total, "ease": "none"}, 0)
    n = len(tlj["scenes"])
    scenes = [scene(sc, tl, tlj, i == 0, i == n - 1) for i, sc in enumerate(tlj["scenes"])]
    subs = subtitles(tlj, tl)

    colors = {"bg": BG, "amber": AMBER, "cream": CREAM, "muted": MUTED}
    page = (
        PAGE.replace("__TITLE__", esc(tlj["title"]))
        .replace("__VARS__", " ".join(f"--{k}: {v};" for k, v in colors.items()))
        .replace("__CSS__", CSS.strip())
        .replace("__DUR__", num(total))
        .replace("__FPS__", str(tlj["fps"]))
        .replace("__BG__", background(total))
        .replace("__SCENES__", "".join(scenes))
        .replace("__SUBS__", subs)
        .replace("__TWEENS__", "\n".join(tl.lines).strip())
    )
    out = HERE / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"{tlj['title']}：{len(tlj['scenes'])} 个分镜、{len(tlj['cues'])} 条字幕、{len(tl.lines)} 行动画，"
          f"总时长 {total:.2f}s → {out.name}")
    return out


def render(tid: str) -> None:
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    subprocess.run([npx, "hyperframes", "lint"], cwd=HERE, check=True)
    subprocess.run([npx, "hyperframes", "render", "-o", f"../out/{tid}_2_hyperframes.mp4", "--workers", "3"], cwd=HERE, check=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    topic = args[0] if args else "hexagon"
    build(topic)
    if "--render" in sys.argv:
        render(topic)
