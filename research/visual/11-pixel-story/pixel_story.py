"""像素风人物小故事《掉落的星星》（纯代码，不用任何 AI 图像模型）

剧情（跟着配音的词级时间轴走，见 content/story.json）：
    walk  傍晚，小柚带着猫咪阿团走在回家路上（镜头跟随横移）
    fall  天色转暗、窗户亮灯；流星划过夜空，落到山坡后面
    find  山坡上，一颗迷路的小星星在哭
    lift  小柚把它举过头顶，阿团跳起来，小星星发光升起
    end   小星星回到夜空眨眨眼，满天星星，"晚安"

像素风的做法：
    底稿 108×192，整数倍放大 10 倍到 1080×1920（最近邻，像素方正锐利）
    角色是字符网格手绘的精灵图（一个字符 = 色板里一种颜色），走路、抬头、举起、挥手是不同的帧
    限定色板（Endesga 32），渐变和光晕用 4×4 有序抖动，黄昏→夜晚用抖动溶解过渡
    对白是 RPG 式像素对话框（宋体 12px 点阵字），按配音的词级时间点逐字打出
    8-bit 芯片音乐和音效也是代码合成的

用法（任意目录）:
    uv run vlab-tts research/visual/11-pixel-story/content/story.json      # 配音（已生成，改了稿子才重跑）
    uv run python research/visual/11-pixel-story/pixel_story.py            # → renders/pixel-story.mp4
    uv run python research/visual/11-pixel-story/pixel_story.py --still 18.5   # 只出一帧 PNG
    uv run python research/visual/11-pixel-story/pixel_story.py --sheet        # 角色设定图 renders/sprites.png
"""

import argparse
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TL = json.loads((HERE / "build" / "pixel-story" / "timeline.json").read_text(encoding="utf-8"))
SC = {s["id"]: s for s in TL["scenes"]}
DUR = TL["duration"]
BW, BH, SCALE = 108, 192, 10          # 底稿尺寸和放大倍数（1080×1920）
UW, UH, USCALE = 216, 384, 5          # 界面层（对话框、标题）尺寸和放大倍数
FPS = 30
FONT = "C:/Windows/Fonts/simsun.ttc"  # 宋体：12/16px 有内置点阵，像素风中文


def word_t(sid, text, nth=1):
    hits = [w for w in SC[sid]["words"] if w["text"].strip() == text] or [w for w in SC[sid]["words"] if text in w["text"]]
    return hits[nth - 1]["start"]


# ---------- 色板（Endesga 32） ----------
def hx(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)


P = {k: hx(v) for k, v in dict(
    ink="#181425", navy="#262b44", slate="#3a4466", steel="#5a6988", mist="#8b9bb4", pale="#c0cbdc", white="#ffffff",
    plum="#68386c", rose="#b55088", salmon="#f6757a", peach="#e8b796", tan="#c28569", sand="#e4a672",
    rust="#be4a2f", orange="#f77622", gold="#feae34", yellow="#fee761", cream="#ead4aa",
    brown="#b86f50", dbrown="#733e39", wine="#3e2731", red="#e43b44", dred="#a22633",
    green="#63c74d", fgreen="#3e8948", pine="#265c42", deep="#193c3e", blue="#124e89", sky="#0099db", cyan="#2ce8f5",
).items()}

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16


def bayer(h, w):
    return np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]


# ---------- 精灵图：字符网格 ----------
KID = [
    "....kkkk....",
    "..kkhhhhkk..",
    ".khhhHHhhhk.",
    ".khhhhhhhhhk",
    ".khhhhssssk.",
    ".khhhssssek.",
    ".khhhsssssk.",
    "..khhsSssk..",
    "...krrrrrk..",
    "..krrRRrrrk.",
    ".kRrkcccccck",
    ".kRkcccccCsk",
    "..kcccccccCk",
    "..kCcccccCCk",
    "...kCCCCCCk.",
    "...kpppppk..",
    "...kpk.kpk..",
    "...kpk.kpk..",
    "..kbbk.kbbk.",
    "............",
]
LEGS = {   # 第 16–18 行换成不同的腿
    "stand": ["...kpk.kpk..", "...kpk.kpk..", "..kbbk.kbbk."],
    "strideA": ["..kpk..kpk..", ".kpk....kpk.", ".kbbk...kbbk"],
    "pass": ["....kppk....", "....kppk....", "....kbbbk..."],
}
LOOKUP = {4: ".khhhhsssek.", 5: ".khhhsssssk."}      # 抬头：眼睛上移一格
KID_COL = dict(k="ink", h="dbrown", H="brown", s="peach", S="salmon", e="ink", r="red", R="dred",
               c="gold", C="orange", p="navy", b="wine")

CAT = [
    "..........k.k.",
    "k........kokok",
    "ok......kooook",
    ".ok.....koeoek",
    "..okkkkkkoooPk",
    "..kooooooooook",
    "..kOooooooOok.",
    "..kOk.kOk.kOk.",
]
CAT_LEGS = {"A": "..kOk.kOk.kOk.", "B": "...kOk..kOkOk.", "tuck": ".............."}
CAT_COL = dict(k="ink", o="orange", O="rust", e="ink", P="salmon")

BUBBLE_EX = [".kkkkk.", "kwwrwwk", "kwwrwwk", "kwwrwwk", "kwwwwwk", "kwwrwwk", ".kkkkk.", "...k..."]
BUBBLE_Q = [".kkkkk.", "kwqqqwk", "kwwwqwk", "kwwqqwk", "kwwwwwk", "kwwqwwk", ".kkkkk.", "...k..."]
BUB_COL = dict(k="ink", w="white", r="red", q="blue")


def grid(rows, colmap):
    w = len(rows[0])
    assert all(len(r) == w for r in rows), [len(r) for r in rows]
    idx = np.zeros((len(rows), w), np.int16) - 1
    cols = []
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                name = colmap[ch]
                if name not in cols:
                    cols.append(name)
                idx[y, x] = cols.index(name)
    return idx, [P[c] for c in cols]


def kid_sprite(legs="stand", look_up=False):
    rows = list(KID)
    rows[16:19] = LEGS[legs]
    if look_up:
        for k, v in LOOKUP.items():
            rows[k] = v
    return grid(rows, KID_COL)


def cat_sprite(legs="A", tail_up=False):
    rows = list(CAT)
    rows[7] = CAT_LEGS[legs]
    if tail_up:                     # 尾巴翘起来
        rows[0] = "k.........k.k."
        rows[1] = "ok.......kokok"
        rows[2] = ".ok.....kooook"
        rows[3] = "..o.....koeoek"
    return grid(rows, CAT_COL)


def blit(cv, spr, x, y, flip=False, dark=0.0):
    idx, cols = spr
    if flip:
        idx = idx[:, ::-1]
    h, w = idx.shape
    x, y = int(round(x)), int(round(y))
    for i, c in enumerate(cols):
        c = c if dark <= 0 else (c * (1 - dark) + P["navy"] * dark).astype(np.uint8)   # 夜里角色偏暗偏蓝
        ys, xs = np.nonzero(idx == i)
        ys, xs = ys + y, xs + x
        ok = (ys >= 0) & (ys < cv.shape[0]) & (xs >= 0) & (xs < cv.shape[1])
        cv[ys[ok], xs[ok]] = c


def px(cv, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < cv.shape[1] and 0 <= y < cv.shape[0]:
        cv[y, x] = c


def star_sprite(r=6, crying=False, wink=False, glow_eyes=False):
    """在低分辨率下光栅化五角星（不抗锯齿），再自动描边——像素画里常用的做法"""
    n = 2 * r + 3
    m = Image.new("L", (n, n), 0)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.48
        pts.append((n / 2 - 0.5 + rr * math.cos(a), n / 2 - 0.2 + rr * math.sin(a)))
    ImageDraw.Draw(m).polygon(pts, fill=1)
    fill = np.asarray(m).astype(bool)
    pad = np.pad(fill, 1)
    outline = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & ~fill
    idx = np.full((n, n), -1, np.int16)
    idx[outline] = 0
    idx[fill] = 1
    yy, xx = np.mgrid[0:n, 0:n]
    idx[fill & (xx + yy > n + 1)] = 2                         # 右下半边暗一点
    c = n // 2
    idx[c - 1, c - 2] = idx[c - 1, c + 1] = 3                 # 眼睛
    if wink:                                                  # 眨眼：右眼闭上（往下挪一格，像一条弯线）
        idx[c - 1, c + 1] = 1
        idx[c, c + 1] = 3
    idx[c - 3, c - 1] = 4                                     # 高光
    if crying:
        idx[c, c - 2] = 5
    return idx, [P["dbrown"], P["yellow"], P["gold"], P["ink"], P["white"], P["sky"]]


# ---------- 背景元素 ----------
def gradient(h, w, stops, t_shift=0.0):
    """竖直渐变 + 有序抖动：每一行只用相邻两个色板颜色，按抖动阈值混合"""
    out = np.zeros((h, w, 3), np.uint8)
    B = bayer(h, w)
    ys = np.arange(h) / (h - 1)
    for y in range(h):
        v = min(max(ys[y] + t_shift, 0), 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= v <= p1:
                f = (v - p0) / (p1 - p0)
                out[y] = np.where((B[y] < f)[:, None], P[c1], P[c0])
                break
    return out


def dither_glow(cv, cx, cy, radius, color, strength=1.0):
    h, w = cv.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - cx, (yy - cy) * 1.1) / max(radius, 1e-3)
    m = np.clip(1 - d, 0, 1) ** 1.6 * strength > bayer(h, w)
    cv[m] = P[color]


def ridge(w, base, amp, seed, rough=0.5, period=40):
    rng = np.random.default_rng(seed)
    x = np.arange(w)
    y = np.zeros(w)
    a, per = amp, period
    for _ in range(4):
        ph = rng.uniform(0, 2 * np.pi)
        y += a * np.sin(2 * np.pi * x / per + ph)
        a *= rough
        per /= 2.1
    return np.round(base + y).astype(int)


def fill_below(cv, tops, color, rim=None):
    h = cv.shape[0]
    for x, t in enumerate(tops):
        if 0 <= x < cv.shape[1]:
            cv[max(t, 0):h, x] = P[color]
            if rim is not None and 0 <= t < h:
                cv[t, x] = P[rim]


def pine(cv, x, base, height, color, rim=None):
    for i in range(height):
        y = base - i
        half = int((height - i) * 0.32 + (1 if (i % 4) < 2 else 0))   # 锯齿边
        for dx in range(-half, half + 1):
            px(cv, x + dx, y, P[color])
        if rim is not None:
            px(cv, x - half, y, P[rim])


STARS = np.random.default_rng(11).integers([0, 0], [BW, 110], (70, 2))
STARS_EXTRA = np.random.default_rng(12).integers([0, 0], [BW, 100], (40, 2))


def sky_stars(cv, t, density=1.0, extra=0.0):
    rng = np.random.default_rng(int(t * 6))
    for i, (x, y) in enumerate(STARS):
        if i / len(STARS) > density:
            break
        tw = 0.5 + 0.5 * math.sin(t * 3 + i * 1.7)
        px(cv, x, y, P["pale"] if tw > 0.35 else P["steel"])
        if i % 13 == 0 and tw > 0.8:                 # 少数大星星闪成十字
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px(cv, x + dx, y + dy, P["steel"])
    for i, (x, y) in enumerate(STARS_EXTRA):
        if i / len(STARS_EXTRA) < extra:
            px(cv, x, y, P["yellow"] if (i + int(t * 4)) % 5 else P["white"])


# ---------- 场景一：小镇街道（黄昏 → 夜晚） ----------
WORLD_W = 220
HILL_FAR = ridge(WORLD_W, 104, 7, 3, period=70)
HILL_NEAR = ridge(WORLD_W, 118, 4, 5, period=45)
HOUSES = [(14, 22, 16, "dred"), (40, 18, 20, "rust"), (66, 26, 14, "wine"), (98, 20, 18, "dred"),
          (126, 24, 22, "rust"), (160, 18, 16, "wine"), (186, 22, 20, "dred")]   # (x, 宽, 高, 屋顶色)
GROUND_Y = 142
FEET_Y = 158
WINDOW_T = {}


def town_layer(t, night, cam):
    sky = gradient(120, BW, [(0, "navy"), (0.35, "plum"), (0.65, "rose"), (0.85, "salmon"), (1, "sand")]) if not night else \
        gradient(120, BW, [(0, "ink"), (0.5, "navy"), (0.85, "slate"), (1, "plum")])
    cv = np.zeros((BH, BW, 3), np.uint8)
    cv[:120] = sky
    cv[120:] = P["ink"]
    if night:
        sky_stars(cv, t, density=min(1.0, max(0.0, (t - 4.5) / 2.0)))
        # 月亮
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                if dx * dx + dy * dy <= 25 and (dx - 2) ** 2 + (dy + 1) ** 2 > 16:
                    px(cv, 18 + dx, 24 + dy, P["cream"])
    else:
        dither_glow(cv, 80, 112, 30, "gold", 0.9)                 # 落日余晖
        for dx in range(-4, 5):
            for dy in range(-4, 1):
                if dx * dx + dy * dy <= 16:
                    px(cv, 80 + dx, 116 + dy, P["yellow"])
    o1 = int(cam * 0.25)
    fill_below(cv, [HILL_FAR[(x + o1) % WORLD_W] for x in range(BW)], "plum" if not night else "navy",
               rim="rose" if not night else "slate")
    o2 = int(cam * 0.5)
    fill_below(cv, [HILL_NEAR[(x + o2) % WORLD_W] for x in range(BW)], "wine" if not night else "ink")
    # 房子（视差 0.8）
    o3 = int(cam * 0.8)
    for i, (hxp, w, h, roof) in enumerate(HOUSES):
        x0 = hxp - o3
        if x0 > BW or x0 + w < 0:
            continue
        wall = ("brown", "dbrown") if not night else ("dbrown", "wine")
        cv[GROUND_Y - h:GROUND_Y, max(x0, 0):max(min(x0 + w, BW), 0)] = P[wall[0]]
        cv[GROUND_Y - h:GROUND_Y, max(x0 + w - 3, 0):max(min(x0 + w, BW), 0)] = P[wall[1]]
        for k in range(w // 2 + 2):                         # 三角屋顶
            y = GROUND_Y - h - k
            xa, xb = x0 - 1 + k, x0 + w + 1 - k
            if xb <= xa:
                break
            cv[y, max(xa, 0):max(min(xb, BW), 0)] = P[roof if not night else "ink"]
        cv[GROUND_Y - h - 6:GROUND_Y - h + 2, max(x0 + 3, 0):max(min(x0 + 5, BW), 0)] = P["wine"]   # 烟囱
        for wx in range(x0 + 3, x0 + w - 4, 6):            # 窗户：夜里依次亮灯
            for wy in (GROUND_Y - h + 4, GROUND_Y - h + 11):
                if wy + 3 > GROUND_Y - 2:
                    continue
                key = (i, wx - x0, wy)
                WINDOW_T.setdefault(key, 5.0 + np.random.default_rng(hash(key) % 1000).uniform(0, 1.8))
                lit = night and t >= WINDOW_T[key]
                cv[wy:wy + 3, max(wx, 0):max(min(wx + 3, BW), 0)] = P["yellow" if lit else ("navy" if night else "wine")]
        # 烟
        for s in range(5):
            sy = GROUND_Y - h - 8 - s * 3 - int((t * 4) % 3)
            px(cv, x0 + 4 + int(math.sin(t * 2 + s + i) * 1.5), sy, P["mist" if not night else "steel"])
    # 地面和小路
    cv[GROUND_Y:GROUND_Y + 8] = P["fgreen" if not night else "deep"]
    cv[GROUND_Y + 8:FEET_Y + 2] = P["sand" if not night else "steel"]
    cv[FEET_Y + 2:] = P["pine" if not night else "ink"]
    rng = np.random.default_rng(7)
    for gx in rng.integers(0, WORLD_W, 40):              # 草丛
        px(cv, gx - int(cam), GROUND_Y - 1, P["green" if not night else "pine"])
    return cv


# ---------- 场景二：山坡（夜） ----------
HILLTOP = ridge(BW, 150, 2, 9, period=60)
TOWN_LIGHTS = np.random.default_rng(21).integers([0, 124], [BW, 128], (14, 2))


def hill_layer(t):
    cv = np.zeros((BH, BW, 3), np.uint8)
    cv[:] = gradient(BH, BW, [(0, "ink"), (0.45, "navy"), (0.7, "slate"), (0.8, "plum"), (1, "plum")])
    extra = min(1.0, max(0.0, (t - word_t("end", "夜空")) / 2.5))
    sky_stars(cv, t, density=1.0, extra=extra)
    # 大月亮
    for dy in range(-9, 10):
        for dx in range(-9, 10):
            d2 = dx * dx + dy * dy
            if d2 <= 81:
                c = "cream" if d2 < 64 else "peach"
                if (dx - 3) ** 2 + (dy + 2) ** 2 < 5 or (dx + 4) ** 2 + (dy - 3) ** 2 < 3:
                    c = "sand"                               # 环形山
                px(cv, 22 + dx, 30 + dy, P[c])
    fill_below(cv, ridge(BW, 128, 3, 4, period=50), "navy", rim="slate")      # 远山
    for x, y in TOWN_LIGHTS:                                                  # 远处小镇的灯
        px(cv, x, y + 2, P["yellow"] if (x + int(t * 3)) % 4 else P["gold"])
    fill_below(cv, HILLTOP, "deep", rim="pine")
    pine(cv, 10, 151, 46, "ink", rim="navy")                                   # 山坡上的树
    pine(cv, 22, 152, 30, "ink", rim="navy")
    rng = np.random.default_rng(5)
    for gx in rng.integers(0, BW, 26):
        px(cv, gx, HILLTOP[gx] - 1, P["pine"])
    for i in range(7):                                                        # 萤火虫
        fx = 50 + 40 * math.sin(t * 0.4 + i * 2.1) + i * 3
        fy = 120 + 14 * math.sin(t * 0.7 + i * 1.3)
        if math.sin(t * 2.5 + i * 3) > -0.2:
            px(cv, fx % BW, fy, P["yellow"])
    return cv


# ---------- 界面层：标题、对话框（216×384 点阵） ----------
FONT12 = ImageFont.truetype(FONT, 12)
FONT16 = ImageFont.truetype(FONT, 16)


def char_times(sid):
    """把旁白的每个字对到配音的词上：词内的字按时间均匀分布，标点跟着前一个字"""
    s = SC[sid]
    text = next(x for x in json.loads((HERE / "content" / "story.json").read_text(encoding="utf-8"))["scenes"]
                if x["id"] == sid)["narration"]
    times, wi, ci = [], 0, 0
    words = s["words"]
    last = s["voice_start"]
    for ch in text:
        if wi < len(words) and ch in words[wi]["text"]:
            w = words[wi]
            n = len(w["text"].strip())
            last = w["start"] + (w["end"] - w["start"]) * ci / max(n, 1)
            ci += 1
            if ci >= n:
                wi, ci = wi + 1, 0
        times.append((ch, last))
    return times


CHAR_TIMES = {sid: char_times(sid) for sid in SC}


def ui_layer(t):
    img = Image.new("RGBA", (UW, UH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    sid = next(s["id"] for s in TL["scenes"] if s["start"] <= t < s["end"] + 1e-6) if t < DUR else TL["scenes"][-1]["id"]
    # 对话框
    x0, y0, x1, y1 = 8, UH - 54, UW - 8, UH - 10
    ink, slate, cream = tuple(P["ink"]), tuple(P["slate"]), tuple(P["cream"])
    d.rectangle([x0 + 1, y0, x1 - 1, y1], fill=ink + (235,))
    d.rectangle([x0, y0 + 1, x1, y1 - 1], fill=ink + (235,))
    d.line([(x0 + 2, y0), (x1 - 2, y0)], fill=cream)
    d.line([(x0 + 2, y1), (x1 - 2, y1)], fill=cream)
    d.line([(x0, y0 + 2), (x0, y1 - 2)], fill=cream)
    d.line([(x1, y0 + 2), (x1, y1 - 2)], fill=cream)
    d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], outline=slate)
    shown = "".join(ch for ch, ct in CHAR_TIMES[sid] if ct <= t)
    lines, cur = [], ""
    for ch in shown:
        if d.textlength(cur + ch, font=FONT12) > (x1 - x0 - 16):
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    lines.append(cur)
    for i, ln in enumerate(lines[:2]):
        d.text((x0 + 8, y0 + 7 + i * 16), ln, font=FONT12, fill=cream)
    if len(shown) == len(CHAR_TIMES[sid]) and int(t * 3) % 2 == 0:     # 打完了：右下角闪烁小三角
        d.polygon([(x1 - 12, y1 - 9), (x1 - 6, y1 - 9), (x1 - 9, y1 - 6)], fill=tuple(P["gold"]))
    # 片头标题
    if t < 3.2:
        title_box(img, "掉落的星星", 46, t, 0.2, 2.6, scale=2)
        title_box(img, "一个像素小故事", 84, t, 0.6, 2.6, scale=1, color="pale")
    wan = word_t("end", "晚安")
    if t >= wan:
        title_box(img, "晚安", 150, t, wan, 99, scale=3, color="yellow")
    return img


def title_box(img, text, cy, t, t_in, t_out, scale=1, color="cream"):
    a = min(1.0, (t - t_in) / 0.5) if t < t_out else max(0.0, 1 - (t - t_out) / 0.5)
    if a <= 0:
        return
    font = FONT16 if scale > 1 else FONT12
    tw = int(ImageDraw.Draw(img).textlength(text, font=font))
    layer = Image.new("RGBA", (tw + 4, font.size + 4), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.fontmode = "1"
    ld.text((2, 3), text, font=font, fill=tuple(P["ink"]))                # 投影
    ld.text((1, 1), text, font=font, fill=tuple(P[color]))
    layer = layer.resize((layer.width * scale, layer.height * scale), Image.NEAREST)
    arr = np.asarray(layer).copy()
    keep = (bayer(arr.shape[0], arr.shape[1]) < a) & (arr[..., 3] > 0)  # 抖动淡入淡出
    arr[..., 3] = np.where(keep, 255, 0)
    img.alpha_composite(Image.fromarray(arr), ((UW - arr.shape[1]) // 2, cy - arr.shape[0] // 2))


# ---------- 每一帧 ----------
def lerp(a, b, f):
    return a + (b - a) * min(max(f, 0.0), 1.0)


def ease(f):
    f = min(max(f, 0.0), 1.0)
    return f * f * (3 - 2 * f)


def walk_cycle(t, speed=8):
    return ["strideA", "pass", "strideA", "pass"][int(t * speed) % 4]


def town_frame(t):
    stop = word_t("fall", "忽然") - 0.1
    kx = lerp(12, 82, (t - 0.3) / (stop - 0.3))
    walking = 0.3 <= t < stop
    cam = min(max(kx - 40, 0), WORLD_W - BW)
    n_mix = ease((t - 4.2) / 1.4)                                       # 黄昏 → 夜晚（抖动溶解）
    day, night = town_layer(t, False, cam), town_layer(t, True, cam)
    cv = np.where((bayer(BH, BW) < n_mix)[..., None], night, day)
    # 流星
    t0, t1 = word_t("fall", "划过"), word_t("fall", "掉到")
    if t0 <= t <= t1 + 0.1:
        f = (t - t0) / (t1 - t0)
        sx, sy = lerp(4, 92, f), lerp(14, 104, f ** 1.3)
        for k in range(40):                                             # 拖尾：连续、由白到橙
            g = f - k * 0.006
            if g < 0:
                break
            c = ["white", "yellow", "gold", "orange", "rust"][min(k // 8, 4)]
            px(cv, lerp(4, 92, g), lerp(14, 104, g ** 1.3), P[c])
        px(cv, sx + 1, sy, P["white"])
    if t > t1:                                                          # 落地的光
        a = max(0.0, 1 - (t - t1) / 2.4)
        dither_glow(cv, 92, 106, 16 * (0.6 + 0.4 * a), "gold", a)
        dither_glow(cv, 92, 106, 7, "yellow", a)
    dark = 0.35 * n_mix
    look = t >= word_t("fall", "忽然") + 0.2
    legs = walk_cycle(t) if walking else "stand"
    bob = -1 if walking and legs == "pass" else 0
    blit(cv, kid_sprite(legs, look_up=look), kx - cam, FEET_Y - 19 + bob, dark=dark)
    cx = kx - 18 if t < stop + 0.3 else kx - 18
    clegs = ["A", "B"][int(t * 6) % 2] if t < stop + 0.3 else "A"
    blit(cv, cat_sprite(clegs, tail_up=look), cx - cam, FEET_Y - 7, dark=dark)
    if word_t("fall", "忽然") <= t < word_t("fall", "星星"):
        blit(cv, grid(BUBBLE_EX, BUB_COL), kx - cam + 3, FEET_Y - 31)
    if word_t("fall", "山坡") <= t < SC["fall"]["end"]:
        blit(cv, grid(BUBBLE_Q, BUB_COL), cx - cam + 8, FEET_Y - 18)
    return cv


def hill_frame(t):
    cv = hill_layer(t)
    s_find = SC["find"]["start"]
    ground = lambda x: HILLTOP[int(min(max(x, 0), BW - 1))]            # noqa: E731
    run0, run1 = word_t("find", "跑"), word_t("find", "看")
    kx = lerp(-14, 36, (t - run0) / (run1 - run0))
    ckx = lerp(-30, 20, (t - run0 - 0.15) / (run1 - run0))
    running = run0 <= t < run1
    lift_t, jump_t = word_t("lift", "举起"), word_t("lift", "跳")
    up_t, sky_t = word_t("lift", "天上"), word_t("end", "夜空")
    # 小星星的位置：地上 → 举过头顶 → 升上夜空
    sx0, sy0 = 62, ground(69) - 13                                   # 坐在草地上
    hold = (kx - 1, ground(kx + 6) - 38)                               # 举过头顶
    if t < lift_t - 0.2:
        sx, sy = sx0, sy0 + (1 if int(t * 2) % 2 else 0)
    elif t < up_t:
        f = ease((t - (lift_t - 0.2)) / 0.5)
        sx, sy = lerp(sx0, hold[0], f), lerp(sy0, hold[1], f)
    else:
        f = ease((t - up_t) / (sky_t - up_t + 0.4))
        sx = lerp(hold[0], 72, f) + 4 * math.sin((t - up_t) * 2.2) * (1 - f)
        sy = lerp(hold[1], 20, f)
    glow = 0.55 + 0.15 * math.sin(t * 4)
    if t >= word_t("lift", "找回"):
        glow = min(1.3, glow + (t - word_t("lift", "找回")) * 0.6)
    dither_glow(cv, sx + 7, sy + 7, 13 * glow, "slate", 0.9)
    dither_glow(cv, sx + 7, sy + 7, 8 * glow, "gold", 0.7)
    # 小星星
    crying = s_find <= t < lift_t
    wink = any(word_t("end", "眨", k) <= t < word_t("end", "眨", k) + 0.22 for k in (1, 2))
    blit(cv, star_sprite(6, crying=crying and int(t * 3) % 2 == 0, wink=wink), sx, sy)
    if crying:                                                          # 眼泪一滴滴落下
        for k in range(3):
            ph = (t * 1.6 + k / 3) % 1
            px(cv, sx + 5 - (k % 2) * 4 + 1, sy + 7 + ph * 6, P["sky"])
    if t >= word_t("lift", "找回"):                                     # 闪光粒子
        rng = np.random.default_rng(3)
        for k in range(16):
            ang, spd = rng.uniform(0, 2 * np.pi), rng.uniform(8, 20)
            age = (t - word_t("lift", "找回") + k * 0.07) % 1.0
            px(cv, sx + 7 + math.cos(ang) * spd * age, sy + 7 + math.sin(ang) * spd * age,
               P["yellow" if age < 0.6 else "gold"])
    # 小柚
    kfeet = ground(kx + 6)                                              # 脚踩在山坡表面
    if running:
        spr = kid_sprite(walk_cycle(t, 12))
        blit(cv, spr, kx, kfeet - 19 + (-1 if walk_cycle(t, 12) == "pass" else 0), dark=0.3)
    else:
        blit(cv, kid_sprite("stand", look_up=t >= lift_t - 0.2), kx, kfeet - 19, dark=0.3)
        if lift_t - 0.2 <= t < up_t + 0.6:                               # 双手举高
            arm(cv, kx + 2, kfeet - 9, kx + 3, kfeet - 24)
            arm(cv, kx + 9, kfeet - 9, kx + 8, kfeet - 24)
        if t >= sky_t:                                                   # 挥手
            a = 1 if int(t * 4) % 2 else -1
            arm(cv, kx + 9, kfeet - 9, kx + 10 + a, kfeet - 22)
    # 阿团
    cfeet = ground(ckx + 7)
    cy = cfeet - 8
    tail_up = t >= word_t("find", "原来")
    if jump_t <= t < jump_t + 1.0:                                       # 跳两下
        ph = ((t - jump_t) / 0.5) % 1
        cy -= 7 * 4 * ph * (1 - ph)
        blit(cv, cat_sprite("tuck", tail_up=True), ckx, cy, dark=0.3)
    else:
        blit(cv, cat_sprite(["A", "B"][int(t * 8) % 2] if running else "A", tail_up=tail_up), ckx, cy, dark=0.3)
    if word_t("find", "原来") <= t < word_t("find", "迷路"):
        blit(cv, grid(BUBBLE_EX, BUB_COL), kx + 3, kfeet - 31)
    return cv


def arm(cv, x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n):
        f = i / max(n - 1, 1)
        x, y = lerp(x0, x1, f), lerp(y0, y1, f)
        px(cv, x - 1, y, P["ink"])
        px(cv, x, y, P["gold"])
        px(cv, x + 1, y, P["ink"])
    px(cv, x1, y1 - 1, P["peach"])
    px(cv, x1, y1, P["peach"])


CLOSE = (22, 81)                 # 特写镜头的左上角（裁 54×96，放大 2 倍）


def hill_view(t):
    """发现、举起小星星时用 2 倍特写；小星星开始升空时切回全景。裁剪后整数倍放大，像素仍然方正。"""
    cv = hill_frame(t)
    if t < word_t("lift", "天上"):
        x0, y0 = CLOSE
        cv = cv[y0:y0 + BH // 2, x0:x0 + BW // 2].repeat(2, 0).repeat(2, 1)
    return cv


def frame(t):
    s_find = SC["find"]["start"]
    if t < s_find - 0.25:
        cv = town_frame(t)
    elif t < s_find + 0.25:                                              # 抖动溶解转场
        f = (t - (s_find - 0.25)) / 0.5
        cv = np.where((bayer(BH, BW) < f)[..., None], hill_view(t), town_frame(t))
    else:
        cv = hill_view(t)
    if t > DUR - 1.0:                                                    # 片尾抖动淡出到黑
        f = (t - (DUR - 1.0)) / 0.9
        cv = np.where((bayer(BH, BW) < f)[..., None], P["ink"], cv)
    big = cv.repeat(SCALE, 0).repeat(SCALE, 1)
    ui = np.asarray(ui_layer(t)).repeat(USCALE, 0).repeat(USCALE, 1)
    a = ui[..., 3:4].astype(np.float32) / 255
    return (big * (1 - a) + ui[..., :3] * a).astype(np.uint8)


# ---------- 8-bit 声音 ----------
SR = 24000


def tone(freq, dur, kind="square", vol=0.2, duty=0.25):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    ph = (tt * freq) % 1
    w = np.where(ph < duty, 1.0, -1.0) if kind == "square" else (4 * np.abs(ph - 0.5) - 1)
    env = np.minimum(1, tt / 0.01) * np.exp(-tt * 2.2)
    return w * env * vol


def note_hz(n):
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    return 440 * 2 ** ((names[n[0]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def music():
    beat = 60 / 84
    out = np.zeros(int((DUR + 1) * SR))
    melody = ("E5 G5 A5 G5 E5 D5 C5 D5 E5 G5 A5 C6 A5 G5 E5 -  "
              "D5 E5 G5 E5 D5 C5 A4 C5 D5 E5 D5 C5 A4 G4 C5 -").split()
    bass = ["C3", "A2", "F2", "G2"]
    t = 0.6
    i = 0
    while t < DUR - 1.5:
        n = melody[i % len(melody)]
        if n != "-":
            s = tone(note_hz(n), beat * 0.95, "square", 0.10, 0.25)
            k = int(t * SR)
            out[k:k + len(s)] += s[:len(out) - k]
        if i % 4 == 0:
            b = tone(note_hz(bass[(i // 4) % 4]), beat * 3.8, "tri", 0.16)
            k = int(t * SR)
            out[k:k + len(b)] += b[:len(out) - k]
        t += beat / 2
        i += 1
    # 结尾的和弦
    for nn in ("C4", "E4", "G4", "C5"):
        s = tone(note_hz(nn), 2.2, "tri", 0.09)
        k = int((DUR - 2.3) * SR)
        out[k:k + len(s)] += s[:len(out) - k]
    # 音效：流星呼啸、落地、闪光
    t0, t1 = word_t("fall", "划过"), word_t("fall", "掉到")
    n = int((t1 - t0) * SR)
    tt = np.arange(n) / SR
    f = np.linspace(1800, 300, n)
    sweep = np.where((np.cumsum(f) / SR) % 1 < 0.5, 1.0, -1.0) * np.exp(-tt * 1.5) * 0.08
    out[int(t0 * SR):int(t0 * SR) + n] += sweep
    noise = np.random.default_rng(0).uniform(-1, 1, int(0.4 * SR))
    noise = np.convolve(noise, np.ones(12) / 12, "same") * np.exp(-np.arange(len(noise)) / SR * 9) * 0.35
    out[int(t1 * SR):int(t1 * SR) + len(noise)] += noise
    for ts in (word_t("lift", "找回"), word_t("end", "眨"), word_t("end", "眨", 2)):
        for k, nn in enumerate(("C6", "E6", "G6", "C7")):
            s = tone(note_hz(nn), 0.18, "tri", 0.12)
            st = int((ts + k * 0.05) * SR)
            out[st:st + len(s)] += s[:len(out) - st]
    fade = np.ones(len(out))
    fade[:int(0.8 * SR)] = np.linspace(0, 1, int(0.8 * SR))
    end = int((DUR - 0.2) * SR)
    fade[end - int(1.5 * SR):end] = np.linspace(1, 0, int(1.5 * SR))
    fade[end:] = 0
    return np.clip(out * fade, -1, 1)


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


# ---------- 输出 ----------
def sprite_sheet(path):
    cv = np.zeros((48, 108, 3), np.uint8)
    cv[:] = P["slate"]
    items = [(kid_sprite("stand"), 4), (kid_sprite("strideA"), 20), (kid_sprite("pass"), 36),
             (kid_sprite("stand", True), 52), (cat_sprite("A"), 68), (cat_sprite("tuck", True), 86)]
    for spr, x in items:
        blit(cv, spr, x, 24 - spr[0].shape[0])
    for k, spr in enumerate((star_sprite(6), star_sprite(6, crying=True), star_sprite(6, wink=True))):
        blit(cv, spr, 6 + k * 20, 29)
    Image.fromarray(cv.repeat(10, 0).repeat(10, 1)).save(path)
    print("角色设定图 →", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=float)
    ap.add_argument("--sheet", action="store_true")
    args = ap.parse_args()
    out_dir = HERE / "renders"
    out_dir.mkdir(exist_ok=True)
    if args.sheet:
        sprite_sheet(out_dir / "sprites.png")
        return
    if args.still is not None:
        p = out_dir / f"still_{args.still:.1f}s.png"
        Image.fromarray(frame(args.still)).save(p)
        print("静帧 →", p)
        return
    media = HERE / "media"
    media.mkdir(exist_ok=True)
    silent, audio = media / "silent.mp4", media / "music.wav"
    ff = shutil.which("ffmpeg") or "ffmpeg"
    n = round(DUR * FPS)
    enc = subprocess.Popen([ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{BW * SCALE}x{BH * SCALE}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                            "-tune", "animation", "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for i in range(n):
        enc.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"  帧 {i}/{n}")
    enc.stdin.close()
    enc.wait()
    write_wav(audio, music())
    final = out_dir / "pixel-story.mp4"
    narration = HERE / "build" / "pixel-story" / "narration.wav"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(silent), "-i", str(narration), "-i", str(audio),
                    "-filter_complex", "[1:a]aresample=48000[n];[2:a]aresample=48000,volume=0.55[m];"
                    "[n][m]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,pan=stereo|c0=c0|c1=c0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{DUR:.3f}",
                    "-movflags", "+faststart", str(final)], check=True)
    silent.unlink()
    print("成片 →", final)


if __name__ == "__main__":
    main()
