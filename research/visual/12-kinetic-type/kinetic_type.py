"""文字动效测试《光有多快》：文字本身就是画面（纯代码，Pillow + numpy）

五句话，每句展示一类常用的文字动效，全部按配音的词级时间点出场：
    q      你知道光有多快吗？              逐字弹出（回弹缓动）、"光"闪光、问号摇摆
    speed  每秒三十万公里。                数字滚动（每一位像里程表一样滚）、速度线、落定时冲击
    orbit  一秒钟，能绕地球七圈半。        打字机、环形文字绕圈旋转、光点绕环
    sun    从太阳到地球，光也要走八分多钟。光脉冲沿路径传播、遮罩揭示
    past   所以你看到的太阳，是八分多钟前的太阳。故障风（RGB 错位 + 切片抖动）、逐字波浪
镜头之间的转场：推进穿越、甩镜、旋涡收缩、淡出。

渲染时同时生成"音效事件"（每个字弹出、每次转场、数字每跳一档……），
交给 vlab.audio 自动配音效，再和配音、配乐按自动避让规则混音。

用法（任意目录）:
    uv run vlab-tts research/visual/12-kinetic-type/content/light.json   # 配音（已生成）
    uv run python research/visual/12-kinetic-type/kinetic_type.py        # → renders/light-speed.mp4
    uv run python research/visual/12-kinetic-type/kinetic_type.py --still 4.2
"""

import argparse
import json
import math
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "build" / "light-speed" / "timeline.json").read_text(encoding="utf-8"))
SC = {s["id"]: s for s in TL["scenes"]}
DUR = TL["duration"]
W, H, FPS = 1080, 1920, 30
F_ZH = "C:/Windows/Fonts/msyhbd.ttc"       # 微软雅黑粗体
F_NUM = "C:/Windows/Fonts/ariblk.ttf"      # Arial Black：数字
INK, GOLD, CYAN, PINK, DIM = (245, 243, 255), (255, 209, 102), (76, 201, 240), (255, 107, 154), (150, 160, 195)


def ws(sid, text, nth=1):
    hits = [w for w in SC[sid]["words"] if w["text"].strip() == text]
    return hits[nth - 1]["start"]


def we(sid, text, nth=1):
    hits = [w for w in SC[sid]["words"] if w["text"].strip() == text]
    return hits[nth - 1]["end"]


# ---------- 缓动 ----------
def c01(x):
    return max(0.0, min(1.0, x))


def out_back(x, s=1.9):
    x = c01(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def out_cubic(x):
    return 1 - (1 - c01(x)) ** 3


def in_cubic(x):
    return c01(x) ** 3


def in_out(x):
    x = c01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


# ---------- 文字图层（带缓存） ----------
@lru_cache(maxsize=1024)
def text_img(text, font, size, color, pad=0):
    f = ImageFont.truetype(font, size)
    l, t, r, b = f.getbbox(text)
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=f, fill=color + (255,))
    return img


@lru_cache(maxsize=256)
def glow_img(text, font, size, color, radius):
    return text_img(text, font, size, color, radius * 3).filter(ImageFilter.GaussianBlur(radius))


def fade(layer, alpha):
    if alpha >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    return out


def place(canvas, layer, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    """把图层以 (cx, cy) 为中心贴到画布上，支持缩放、旋转、透明度，超出画布的部分自动裁掉"""
    if alpha <= 0.004 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    layer = fade(layer, alpha)
    x0, y0 = int(round(cx - layer.width / 2)), int(round(cy - layer.height / 2))
    sx, sy = max(0, -x0), max(0, -y0)
    dx, dy = max(0, x0), max(0, y0)
    w, h = min(layer.width - sx, canvas.width - dx), min(layer.height - sy, canvas.height - dy)
    if w > 0 and h > 0:
        canvas.alpha_composite(layer, dest=(dx, dy), source=(sx, sy, sx + w, sy + h))


def word(canvas, text, cx, cy, size, color, t, t0, font=F_ZH, glow=0, rot=0.0, dur=0.32, alpha=1.0):
    """一个词：t0 时回弹弹出"""
    p = (t - t0) / dur
    if p < 0:
        return
    s = out_back(p)
    a = c01(p * 3) * alpha
    if glow:
        place(canvas, glow_img(text, font, size, color, glow), cx, cy, s, rot, a * 0.9)
    place(canvas, text_img(text, font, size, color), cx, cy, s, rot, a)


def row_layout(items, cx, gap):
    """一行几个词，整体居中，返回每个词的中心 x"""
    widths = [text_img(t, f, s, c).width for t, f, s, c in items]
    total = sum(widths) + gap * (len(items) - 1)
    x, out = cx - total / 2, []
    for w in widths:
        out.append(x + w / 2)
        x += w + gap
    return out


# ---------- 背景 ----------
_yy = np.linspace(0, 1, H)[:, None]
_xx = np.linspace(-1, 1, W)[None, :]
BG = np.zeros((H, W, 4), np.uint8)
_grad = (np.array([10, 12, 28]) * (1 - _yy[..., None]) + np.array([30, 18, 62]) * _yy[..., None])
_vig = (1 - 0.45 * (_xx ** 2 + ((_yy - 0.5) * 2) ** 2) / 2)[..., None]
BG[..., :3] = np.clip(_grad * _vig, 0, 255).astype(np.uint8)
BG[..., 3] = 255
_rng = np.random.default_rng(7)
STARS = np.column_stack([_rng.uniform(0, W, 160), _rng.uniform(0, H, 160), _rng.uniform(4, 18, 160), _rng.uniform(0, 6.28, 160)])


def background(t):
    a = BG.copy()
    for x, y, v, ph in STARS:
        yy = int((y + v * t) % H)
        xx = int(x)
        b = int(90 + 80 * math.sin(t * 2 + ph))
        a[yy:yy + 2, xx:xx + 2, :3] = b
    return Image.fromarray(a, "RGBA")


def speed_lines(canvas, t, t0, t1, density=1.0):
    if not (t0 <= t <= t1):
        return
    d = ImageDraw.Draw(canvas)
    rng = np.random.default_rng(3)
    for i in range(int(40 * density)):
        y = rng.uniform(250, 1700)
        length = rng.uniform(180, 620)
        speed = rng.uniform(1800, 3400)
        x = W + 300 - ((t - t0) * speed + rng.uniform(0, 2400)) % (W + 1200)
        c = CYAN if i % 3 else INK
        d.line([(x, y), (x + length, y)], fill=c + (int(rng.uniform(40, 130)),), width=int(rng.uniform(2, 5)))


def affine(layer, scale=1.0, rot_deg=0.0, tx=0.0, ty=0.0, cx=W / 2, cy=H / 2):
    """整个镜头的变换（转场用）：绕 (cx, cy) 缩放、旋转，再平移"""
    th = math.radians(rot_deg)
    a, b = math.cos(th) / scale, math.sin(th) / scale
    d, e = -math.sin(th) / scale, math.cos(th) / scale
    ox, oy = cx + tx, cy + ty
    c = cx - a * ox - b * oy
    f = cy - d * ox - e * oy
    return layer.transform(layer.size, Image.AFFINE, (a, b, c, d, e, f), resample=Image.BICUBIC)


# ---------- 五个镜头 ----------
def scene_q(cv, t):
    row1 = [("你", F_ZH, 120, INK), ("知道", F_ZH, 120, INK)]
    for (txt, f, s, c), x, t0 in zip(row1, row_layout(row1, 540, 14), (ws("q", "你"), ws("q", "知道"))):
        word(cv, txt, x, 690, s, c, t, t0)
    t_light = ws("q", "光")
    if t >= t_light:                                                        # "光"：闪光 + 呼吸光晕
        pulse = 0.75 + 0.25 * math.sin((t - t_light) * 6)
        place(cv, glow_img("光", F_ZH, 440, GOLD, 40), 540, 1010, out_back((t - t_light) / 0.4), 0, pulse)
    word(cv, "光", 540, 1010, 440, GOLD, t, t_light, dur=0.4)
    row3 = [("有", F_ZH, 150, INK), ("多", F_ZH, 150, INK), ("快", F_ZH, 150, CYAN), ("吗？", F_ZH, 150, PINK)]
    times = (ws("q", "有"), ws("q", "多"), ws("q", "快"), ws("q", "吗"))
    for (txt, f, s, c), x, t0 in zip(row3, row_layout(row3, 540, 10), times):
        rot = 0.0
        if txt == "吗？" and t >= t0:                                        # 问号摇摆
            rot = 14 * math.sin((t - t0) * 14) * math.exp(-(t - t0) * 3)
        word(cv, txt, x, 1340, s, c, t, t0, rot=rot)


ODO_DIGITS = 6


def paste_clip(dst, src, x, y):
    """贴图，超出边界（包括负坐标）的部分裁掉"""
    sx, sy = max(0, -x), max(0, -y)
    dx, dy = max(0, x), max(0, y)
    w, h = min(src.width - sx, dst.width - dx), min(src.height - sy, dst.height - dy)
    if w > 0 and h > 0:
        dst.alpha_composite(src, dest=(dx, dy), source=(sx, sy, sx + w, sy + h))


def odometer(v, color_on, color_off):
    """里程表式数字：每一位按 (v / 10^k) 的小数部分上下滚动"""
    cell = text_img("0", F_NUM, 210, color_on)
    cw, ch = cell.width + 6, cell.height + 10
    comma = text_img(",", F_NUM, 210, color_on)
    total_w = cw * ODO_DIGITS + comma.width + 6
    out = Image.new("RGBA", (total_w, ch), (0, 0, 0, 0))
    x = 0
    for i in range(ODO_DIGITS):
        k = ODO_DIGITS - 1 - i
        cont = (v / 10 ** k) % 10
        dgt, frac = int(cont), cont - int(cont)
        if k > 0 and v < 10 ** k - 0.5:
            col = color_off
        else:
            col = color_on
        cell_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        g0 = text_img(str(dgt), F_NUM, 210, col)
        g1 = text_img(str((dgt + 1) % 10), F_NUM, 210, col)
        paste_clip(cell_img, g0, (cw - g0.width) // 2, int(5 - frac * ch))           # 当前数字往上滚出去
        if frac > 0.001:
            paste_clip(cell_img, g1, (cw - g1.width) // 2, int(5 + (1 - frac) * ch))  # 下一个数字从下面滚进来
        out.alpha_composite(cell_img, (x, 0))
        x += cw
        if i == 0 + 2:                                                       # 千分位逗号（300,000）
            out.alpha_composite(comma, (x + 3, ch - comma.height - 12))
            x += comma.width + 6
    return out


def counter_value(t):
    t0 = ws("speed", "三十万公里")
    t1 = we("speed", "三十万公里") + 0.15
    return 300000 * out_cubic((t - t0) / (t1 - t0)), t0, t1


def scene_speed(cv, t):
    speed_lines(cv, t, ws("speed", "每") + 0.3, SC["speed"]["end"], 1.0)
    row = [("每", F_ZH, 110, INK), ("秒", F_ZH, 110, INK)]
    for (txt, f, s, c), x, t0 in zip(row, row_layout(row, 540, 10), (ws("speed", "每"), ws("speed", "秒"))):
        p = out_cubic((t - t0) / 0.3)
        if t >= t0:
            place(cv, text_img(txt, f, s, c), x - 90 * (1 - p), 660, 1, 0, p)
    v, t0, t1 = counter_value(t)
    if t >= t0:
        num = odometer(v, GOLD, (90, 80, 70))
        punch = 1 + 0.12 * math.exp(-(t - t1) * 10) if t >= t1 else 1.0
        s = out_back((t - t0) / 0.3) * punch
        place(cv, num.filter(ImageFilter.GaussianBlur(18)), 540, 960, s, 0, 0.8)
        place(cv, num, 540, 960, s)
    tu = we("speed", "三十万公里") - 0.25
    if t >= tu:
        p = out_cubic((t - tu) / 0.35)
        place(cv, text_img("公里", F_ZH, 130, CYAN), 540, 1230 + 60 * (1 - p), 1, 0, p)


ORBIT_TEXT = "绕地球七圈半 · 绕地球七圈半 · "


def scene_orbit(cv, t):
    # 打字机："一秒钟"
    t0, t1 = ws("orbit", "一秒钟"), we("orbit", "一秒钟")
    chars = "一秒钟"
    xs = row_layout([(c, F_ZH, 130, INK) for c in chars], 540, 8)
    n = 0 if t < t0 else min(3, 1 + int((t - t0) / ((t1 - t0) / 3)))
    for i in range(n):
        place(cv, text_img(chars[i], F_ZH, 130, INK), xs[i], 520)
    if t >= t0 and (int(t * 3) % 2 == 0 or t < t1):                         # 光标
        cx = xs[n - 1] + 75 if n else xs[0] - 65
        ImageDraw.Draw(cv).rectangle([cx, 455, cx + 10, 585], fill=GOLD + (255,))
    cx, cy, R = 540, 1000, 210
    t_ring = ws("orbit", "能")
    if t >= t_ring:                                                          # 地球：一个发光的圆环
        s = out_back((t - t_ring) / 0.4)
        ring = ring_img(R, CYAN)
        place(cv, ring[1], cx, cy, s, 0, 0.9)
        place(cv, ring[0], cx, cy, s)
        # 光点绕环飞，带尾巴
        d = ImageDraw.Draw(cv)
        for k in range(18):
            ang = (t - t_ring) * 2 * math.pi * 1.6 - k * 0.07
            px, py = cx + R * s * math.cos(ang), cy + R * s * math.sin(ang)
            r = 12 - k * 0.55
            d.ellipse([px - r, py - r, px + r, py + r], fill=GOLD + (int(255 * (1 - k / 18)),))
    word(cv, "地球", cx, cy, 110, INK, t, ws("orbit", "地球"))
    t_txt = ws("orbit", "绕")
    if t >= t_txt:                                                           # 环形文字：每个字按切线方向旋转
        a = c01((t - t_txt) / 0.4)
        n = len(ORBIT_TEXT)
        spin = (t - t_txt) * 0.9
        for i, ch in enumerate(ORBIT_TEXT):
            ang = 2 * math.pi * i / n + spin
            px, py = cx + 320 * math.cos(ang), cy + 320 * math.sin(ang)
            col = GOLD if ch in "七圈半" else INK
            place(cv, text_img(ch, F_ZH, 64, col), px, py, 1, -math.degrees(ang) - 90, a)
    t_big = ws("orbit", "七圈半")
    shake = 6 * math.exp(-(t - t_big) * 8) * math.sin((t - t_big) * 60) if t >= t_big else 0
    word(cv, "七圈半", 540 + shake, 1480, 210, GOLD, t, t_big, glow=24)


@lru_cache(maxsize=4)
def ring_img(R, color):
    img = Image.new("RGBA", (2 * R + 80, 2 * R + 80), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([40, 40, 40 + 2 * R, 40 + 2 * R], outline=color + (255,), width=10)
    return img, img.filter(ImageFilter.GaussianBlur(16))


@lru_cache(maxsize=4)
def sun_img(r):
    n = 4 * r
    yy, xx = np.mgrid[0:n, 0:n] - n / 2
    d = np.hypot(xx, yy) / r
    core = np.clip((1.05 - d) * 8, 0, 1)
    halo = np.clip(1 - (d - 1) / 1.0, 0, 1) ** 2 * 0.55
    a = np.clip(core + halo * (d >= 1), 0, 1)
    rgb = np.zeros((n, n, 4), np.uint8)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = 255, (209 + 30 * core).clip(0, 255), (102 + 120 * core).clip(0, 255)
    rgb[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgb, "RGBA")


def scene_sun(cv, t):
    sx, ex, y = 230, 850, 960
    word(cv, "从", sx, 760, 80, DIM, t, ws("sun", "从"))
    word(cv, "到", 540, 760, 80, DIM, t, ws("sun", "到"))
    t_sun = ws("sun", "太阳")
    if t >= t_sun:
        place(cv, sun_img(100), sx, y, out_back((t - t_sun) / 0.4), 0, 1)
        p = out_cubic((t - t_sun) / 0.35)
        place(cv, text_img("太阳", F_ZH, 110, GOLD), sx - 120 * (1 - p), 1160, 1, 0, p)
    t_earth = ws("sun", "地球")
    if t >= t_earth:
        p = out_cubic((t - t_earth) / 0.35)
        ring = ring_img(70, CYAN)
        hit = math.exp(-(t - we("sun", "八分多钟")) * 4) if t >= we("sun", "八分多钟") else 0
        place(cv, ring[1], ex + 120 * (1 - p), y, 1 + 0.25 * hit, 0, p)
        place(cv, ring[0], ex + 120 * (1 - p), y, 1 + 0.25 * hit, 0, p)
        place(cv, text_img("地球", F_ZH, 110, CYAN), ex + 120 * (1 - p), 1160, 1, 0, p)
    t_line = ws("sun", "到")
    if t >= t_line:                                                          # 虚线路径慢慢画出来
        d = ImageDraw.Draw(cv)
        x_end = 350 + (770 - 350) * out_cubic((t - t_line) / 0.5)
        x = 350
        while x < x_end:
            d.line([(x, y), (min(x + 22, x_end), y)], fill=DIM + (200,), width=5)
            x += 38
    t_go, t_arrive = ws("sun", "光"), we("sun", "八分多钟")
    if t_go <= t <= t_arrive + 0.3:                                          # 光脉冲沿路径传播
        f = c01((t - t_go) / (t_arrive - t_go))
        hx = 350 + 420 * f
        d = ImageDraw.Draw(cv)
        for k in range(30):
            xx = hx - k * 7
            if xx < 350:
                break
            r = 13 - k * 0.38
            d.ellipse([xx - r, y - r, xx + r, y + r], fill=GOLD + (int(255 * (1 - k / 30)),))
    t_rev = ws("sun", "八分多钟")
    if t >= t_rev:                                                           # 遮罩揭示：色块扫过，扫过的地方文字出现
        txt = text_img("八分多钟", F_ZH, 190, INK)
        p = in_out((t - t_rev) / 0.55)
        vis = int(txt.width * p)
        if vis > 0:
            place(cv, txt.crop((0, 0, vis, txt.height)), 540 - txt.width / 2 + vis / 2, 1400)
        bar_w = 40 if p < 1 else max(0, 40 * (1 - (t - t_rev - 0.55) / 0.25))
        if bar_w > 0:
            bx = 540 - txt.width / 2 + vis
            ImageDraw.Draw(cv).rectangle([bx - bar_w / 2, 1400 - txt.height / 2 - 14, bx + bar_w / 2, 1400 + txt.height / 2 + 14],
                                         fill=GOLD + (255,))
    t_note = t_arrive + 0.05
    if t >= t_note:
        p = out_cubic((t - t_note) / 0.4)
        place(cv, text_img("≈ 499 秒", F_ZH, 80, DIM), 540, 1560 + 40 * (1 - p), 1, 0, p)


def glitch(layer, t, strength):
    """故障风：RGB 通道错位 + 横向切片抖动"""
    if strength <= 0.01:
        return layer
    a = np.asarray(layer).copy()
    rng = np.random.default_rng(int(t * 60))
    off = int(14 * strength)
    out = np.zeros_like(a)
    out[..., 3] = a[..., 3]
    out[:, :, 0] = np.roll(a[:, :, 0], -off, axis=1)
    out[:, :, 1] = a[:, :, 1]
    out[:, :, 2] = np.roll(a[:, :, 2], off, axis=1)
    out[..., 3] = np.maximum.reduce([a[..., 3], np.roll(a[..., 3], -off, 1), np.roll(a[..., 3], off, 1)])
    h = a.shape[0]
    for _ in range(int(6 * strength)):
        y0 = int(rng.uniform(0, h - 8))
        hh = int(rng.uniform(4, h / 5))
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(rng.uniform(-40, 40) * strength), axis=1)
    return Image.fromarray(out, "RGBA")


def glitch_strength(t):
    t0 = ws("past", "八分多钟")
    s = math.exp(-(t - t0) * 6) if t >= t0 else 0
    for tb in (18.4, 19.25):
        if tb <= t < tb + 0.14:
            s = max(s, 0.8)
    return s


def scene_past(cv, t):
    row1 = [("所以", F_ZH, 110, INK), ("你", F_ZH, 110, INK), ("看到", F_ZH, 110, INK), ("的", F_ZH, 110, INK)]
    times = (ws("past", "所以"), ws("past", "你"), ws("past", "看到"), ws("past", "的"))
    for (txt, f, s, c), x, t0 in zip(row1, row_layout(row1, 540, 12), times):
        word(cv, txt, x, 600, s, c, t, t0)
    t_sun = ws("past", "太阳")
    if t >= t_sun:
        pulse = 0.7 + 0.3 * math.sin((t - t_sun) * 4)
        place(cv, glow_img("太阳", F_ZH, 330, GOLD, 40), 540, 880, out_back((t - t_sun) / 0.4), 0, pulse)
    word(cv, "太阳", 540, 880, 330, GOLD, t, t_sun, dur=0.4)
    word(cv, "是", 540, 1150, 110, INK, t, ws("past", "是"))
    row4 = [("八分多钟", F_ZH, 140, PINK), ("前的", F_ZH, 140, PINK)]
    times4 = (ws("past", "八分多钟"), ws("past", "前"))
    g = glitch_strength(t)
    for (txt, f, s, c), x, t0 in zip(row4, row_layout(row4, 540, 6), times4):
        if t >= t0:
            p = out_cubic((t - t0) / 0.2)
            place(cv, glitch(text_img(txt, f, s, c), t, g), x, 1330, 1, 0, p)
    t_last = ws("past", "太阳", 2)
    if t >= t_last:                                                          # 最后的"太阳"：逐字波浪
        a = out_cubic((t - t_last) / 0.5) * 0.75
        xs = row_layout([("太", F_ZH, 200, GOLD), ("阳", F_ZH, 200, GOLD)], 540, 10)
        for i, (ch, x) in enumerate(zip("太阳", xs)):
            place(cv, text_img(ch, F_ZH, 200, (230, 190, 110)), x, 1560 + 16 * math.sin((t - t_last) * 4 + i * 1.3), 1, 0, a)
    t_note = 18.3
    if t >= t_note:
        p = out_cubic((t - t_note) / 0.5)
        place(cv, text_img("光速 ≈ 299,792 公里/秒", F_ZH, 56, DIM), 540, 1760, 1, 0, p * 0.9)


SCENES = [("q", scene_q, "zoom"), ("speed", scene_speed, "whip"), ("orbit", scene_orbit, "swirl"),
          ("sun", scene_sun, "fade"), ("past", scene_past, "end")]
EXIT = 0.28


def frame(t):
    cv = background(t)
    for sid, fn, kind in SCENES:
        s0, s1 = SC[sid]["start"], SC[sid]["end"]
        if not (s0 <= t < s1 or (sid == "past" and t >= s0)):
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fn(layer, t)
        p = c01((t - (s1 - EXIT)) / EXIT)
        if kind == "zoom" and p > 0:                                         # 推进穿越：朝"光"冲过去
            layer = fade(affine(layer, 1 + 2.2 * in_cubic(p), 0, 0, 0, 540, 1010), 1 - p)
        elif kind == "whip" and p > 0:                                       # 甩镜：整体快速甩出左边
            layer = affine(layer, 1, 0, -1200 * in_cubic(p), 0)
        elif kind == "swirl" and p > 0:                                      # 旋涡：边转边缩小
            layer = fade(affine(layer, 1 - 0.85 * in_cubic(p), 120 * in_cubic(p), 0, 0, 540, 1000), 1 - p)
        elif kind == "fade" and p > 0:
            layer = fade(layer, 1 - p)
        elif kind == "end":
            q = c01((t - (DUR - 0.9)) / 0.8)
            if q > 0:
                layer = fade(layer, 1 - q)
        cv.alpha_composite(layer)
        if sid == "q":                                                       # "光"出现时整屏一闪
            tl = ws("q", "光")
            if tl <= t < tl + 0.35:
                cv.alpha_composite(Image.new("RGBA", (W, H), (255, 240, 200, int(90 * (1 - (t - tl) / 0.35)))))
    return np.asarray(cv.convert("RGB"))


# ---------- 音效事件：画面里每个"动作"都对应一个声音 ----------
def sfx_events():
    ev = []
    add = lambda t, kind, g=1.0: ev.append({"t": round(t, 3), "kind": kind, "gain": g})   # noqa: E731
    for w_, k, g in (("你", "pop", 0.5), ("知道", "pop", 0.5), ("有", "pop", 0.4), ("多", "pop", 0.4), ("快", "pop", 0.5)):
        add(ws("q", w_), k, g)
    add(ws("q", "光"), "chime", 0.8)
    add(ws("q", "光"), "pop", 0.6)
    add(ws("q", "吗"), "boing", 0.6)
    add(SC["q"]["end"] - EXIT, "whoosh", 0.7)
    add(ws("speed", "每"), "whoosh", 0.35)
    v_prev, t = 0, ws("speed", "三十万公里")
    _, t0, t1 = counter_value(t)
    while t <= t1:                                                           # 数字每跳过一个万位就"咔"一声，越来越慢
        v, _, _ = counter_value(t)
        if int(v // 10000) != int(v_prev // 10000):
            add(t, "tick", 0.45)
        v_prev = v
        t += 1 / 120
    add(t1, "impact", 0.9)
    add(we("speed", "三十万公里") - 0.25, "pop", 0.4)
    add(SC["speed"]["end"] - EXIT, "whip", 0.8)
    a, b = ws("orbit", "一秒钟"), we("orbit", "一秒钟")
    for i in range(3):
        add(a + i * (b - a) / 3, "key", 0.6)
    add(ws("orbit", "能"), "shimmer", 0.5)
    add(ws("orbit", "绕"), "whoosh", 0.35)
    add(ws("orbit", "地球"), "pop", 0.45)
    add(ws("orbit", "七圈半"), "impact", 0.7)
    add(SC["orbit"]["end"] - EXIT, "whoosh", 0.6)
    add(ws("sun", "从"), "pop", 0.3)
    add(ws("sun", "太阳"), "whoosh", 0.45)
    add(ws("sun", "到"), "pop", 0.3)
    add(ws("sun", "地球"), "whoosh", 0.45)
    add(ws("sun", "光"), "laser", 0.45)
    add(ws("sun", "八分多钟"), "whip", 0.45)
    add(we("sun", "八分多钟"), "chime", 0.6)
    add(we("sun", "八分多钟") + 0.05, "tick", 0.4)
    add(SC["sun"]["end"] - EXIT, "whoosh", 0.35)
    for w_ in ("所以", "你", "看到"):
        add(ws("past", w_), "pop", 0.4)
    add(ws("past", "太阳"), "impact", 0.8)
    add(ws("past", "太阳"), "chime", 0.5)
    add(ws("past", "是"), "pop", 0.4)
    add(ws("past", "八分多钟"), "glitch", 0.6)
    add(ws("past", "前"), "glitch", 0.35)
    add(ws("past", "太阳", 2), "chime", 0.45)
    add(18.3, "tick", 0.3)
    for tb in (18.4, 19.25):
        add(tb, "glitch", 0.3)
    return sorted(ev, key=lambda e: e["t"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=float)
    args = ap.parse_args()
    out_dir = HERE / "renders"
    out_dir.mkdir(exist_ok=True)
    if args.still is not None:
        p = out_dir / f"still_{args.still:.1f}s.png"
        Image.fromarray(frame(args.still)).save(p)
        print("静帧 →", p)
        return
    events = sfx_events()
    (HERE / "build" / "light-speed" / "sfx_events.json").write_text(json.dumps(events, ensure_ascii=False, indent=1), encoding="utf-8")
    media = HERE / "media"
    media.mkdir(exist_ok=True)
    silent = media / "silent.mp4"
    n = round(DUR * FPS)
    enc = subprocess.Popen([shutil.which("ffmpeg") or "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for i in range(n):
        enc.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"  帧 {i}/{n}")
    enc.stdin.close()
    enc.wait()
    # 声音：配音 + 事件驱动音效 + 配乐（说话时自动压低）
    from vlab.audio import mix, music, sfx
    sfx_wav, music_wav = media / "sfx.wav", media / "music.wav"
    sfx.write_wav(sfx_wav, sfx.render(events, DUR))
    music.write_wav(music_wav, music.ambient_pulse(DUR, bpm=100, seed=3))
    mix.mux(silent, HERE / "build" / "light-speed" / "narration.wav", HERE / "renders" / "light-speed.mp4",
            music=music_wav, sfx=sfx_wav, duration=DUR)
    silent.unlink()
    print("成片 →", HERE / "renders" / "light-speed.mp4", f"（{len(events)} 个音效事件）")


if __name__ == "__main__":
    main()
