"""程序化风景：日落湖景，有山、有水、有动物（纯代码，不用任何 AI 模型）

画面（竖屏 1080×1920，12 秒）：
    天空   渐变 + 太阳光晕 + 横向拉长的晚霞云（2D 噪声）
    山     四层分形山脊，越远越朦胧（大气透视），最远一层带雪顶，逆光描边
    岸     松树剪影，镜头缓慢横移，各层视差不同
    水     逐像素算倒影：按透视把噪声铺到水面上，扰动采样坐标，近处波大、远处波细；
           加波峰高光和太阳碎金光带
    动物   鹿在岸边喝水（喝水→抬头警觉→再低头），嘴碰水处起涟漪；
           雁群人字形飞过太阳，另一小群反向飞；鱼跃出水面，带水花和涟漪
    前景   芦苇随风摆
动物和鸟画在"水面以上"的图层里，所以倒影里也有它们。

用法：
    在代码里复用（003 的结尾就是这样）：
        from vlab.scenes import landscape
        scene = landscape.build_scene(); img = landscape.render_frame(scene, t)   # img 是 0..1 的浮点数组
    直接出片（lab/06 的脚本调用的就是 main）：
        uv run python lab/06-landscape/render_landscape.py            # 成片 lab/06-landscape/renders/landscape.mp4
        uv run python lab/06-landscape/render_landscape.py --still 4.8   # 只出一帧 PNG，调画面用
        uv run python lab/06-landscape/render_landscape.py --fps 15      # 快速预览

依赖：numpy、Pillow（根目录 .venv 已有），ffmpeg 在 PATH 上。
"""

import argparse
import math
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

W, H = 1080, 1920
HZ = 1150            # 水岸线（地平线）
DUR = 12.0
PAN = 120.0          # 整段镜头横移量（最近一层山的像素数）
rng = np.random.default_rng(20261020)


# ---------- 小工具 ----------
def C(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


def fbm1d(n, octaves, length, rough=0.5):
    """一维分形值噪声，返回 [-1, 1]"""
    out, amp, tot, L = np.zeros(n, np.float32), 1.0, 0.0, float(length)
    x = np.arange(n, dtype=np.float32)
    for _ in range(octaves):
        pts = rng.uniform(-1, 1, int(n / L) + 3).astype(np.float32)
        xi = x / L
        i = np.floor(xi).astype(int)
        f = xi - i
        f = f * f * (3 - 2 * f)
        out += amp * (pts[i] * (1 - f) + pts[i + 1] * f)
        tot += amp
        amp *= rough
        L /= 2
    return out / tot


def fbm2d(h, w, octaves, cell, rough=0.55):
    """二维分形值噪声（不平铺），返回约 [0, 1]"""
    out, amp, tot = np.zeros((h, w), np.float32), 1.0, 0.0
    for _ in range(octaves):
        gh, gw = int(h / cell) + 3, int(w / cell) + 3
        g = rng.random((gh, gw)).astype(np.float32)
        img = Image.fromarray(g, "F").resize((int(gw * cell), int(gh * cell)), Image.BICUBIC)
        out += amp * np.asarray(img)[:h, :w]
        tot += amp
        amp *= rough
        cell = max(1.0, cell / 2)
    return out / tot


def tile_noise(n, octaves, cell, rough=0.5):
    """可平铺的二维噪声（水面用，采样时取模不会出接缝）"""
    out, amp, tot = np.zeros((n, n), np.float32), 1.0, 0.0
    for _ in range(octaves):
        c = n // cell
        g = np.pad(rng.random((c, c)).astype(np.float32), 2, mode="wrap")
        size = (c + 4) * cell
        img = np.asarray(Image.fromarray(g, "F").resize((size, size), Image.BICUBIC))
        out += amp * img[2 * cell:2 * cell + n, 2 * cell:2 * cell + n]
        tot += amp
        amp *= rough
        cell //= 2
        if cell < 2:
            break
    return out / tot


def sample(N, u, v):
    """在平铺噪声上双线性采样"""
    n = N.shape[0]
    u0, v0 = np.floor(u), np.floor(v)
    fu, fv = (u - u0).astype(np.float32), (v - v0).astype(np.float32)
    u0, v0 = u0.astype(np.int64) % n, v0.astype(np.int64) % n
    u1, v1 = (u0 + 1) % n, (v0 + 1) % n
    return (N[v0, u0] * (1 - fu) + N[v0, u1] * fu) * (1 - fv) + (N[v1, u0] * (1 - fu) + N[v1, u1] * fu) * fv


def shift_crop(layer, off):
    """按亚像素偏移截出 W 宽（线性插值，慢速横移不抖）"""
    i = int(math.floor(off))
    f = off - i
    return layer[:, i:i + W] * (1 - f) + layer[:, i + 1:i + 1 + W] * f


def over_pm(dst, src_pm):
    """预乘 alpha 叠加"""
    a = src_pm[..., 3:4]
    dst *= 1 - a
    dst += src_pm[..., :3]


# ---------- 色板（日落） ----------
SKY_STOPS = [(0.0, "#16123a"), (0.30, "#3d2a7a"), (0.55, "#9b3f80"), (0.75, "#e2705e"), (0.90, "#f9b77a"), (1.0, "#ffe2ad")]
HAZE = C("#e9a8a4")
WARM = C("#ffc59a")
SUN_X = 640

LW = W + int(PAN * 1.5) + 40     # 图层比画面宽，留出横移余量


# ---------- 山 ----------
def mountain(base_y, amp, length, ridge_hex, base_hex, mist, rim, snow=False, smooth_w=0.3):
    ridge_c, base_c = C(ridge_hex), C(base_hex)
    ridged = 1 - np.abs(fbm1d(LW, 7, length))
    smooth = fbm1d(LW, 3, length * 2) * 0.5 + 0.5
    prof = base_y - amp * ((1 - smooth_w) * ridged ** 2.2 + smooth_w * smooth)
    y0 = int(prof.min()) - 3
    Y = np.arange(y0, HZ, dtype=np.float32)[:, None]
    X = np.arange(LW, dtype=np.float32)[None, :]
    cov = np.clip(Y - prof[None] + 0.5, 0, 1)
    depth = np.clip((Y - prof) / (base_y - prof + 80), 0, 1)
    col = lerp(ridge_c, base_c, depth[..., None] ** 0.8)
    # 山体里再叠两道暗一点的内山脊，增加层次
    for k in range(2):
        p2 = prof + amp * (0.16 + 0.17 * k) + amp * 0.12 * fbm1d(LW, 5, length * 0.6)
        col *= (1 - 0.07 * smoothstep(-1.5, 1.5, Y - p2[None]))[..., None]
    tex = fbm2d(HZ - y0, LW, 4, 90)
    col *= (1 + 0.10 * (tex - 0.5))[..., None]
    if snow:
        sn = 10 + 22 * (fbm1d(LW, 4, 60) * 0.5 + 0.5)
        hi = smoothstep(base_y - amp * 0.45, base_y - amp * 0.75, prof)        # 只有高处积雪
        s = smoothstep(sn + 3, sn - 3, Y - prof[None]) * hi[None]
        col = lerp(col, C("#f6d6e2"), (0.85 * s)[..., None])
    col = lerp(col, HAZE, (mist * smoothstep(base_y - amp * 0.4, base_y + 10, Y))[..., None])
    sunw = np.exp(-((X - SUN_X - 60) / 380) ** 2)
    col += WARM * (rim * np.exp(-np.maximum(Y - prof[None], 0) / 2.2) * (0.35 + 0.65 * sunw))[..., None]
    rgba = np.concatenate([col * cov[..., None], cov[..., None]], -1).astype(np.float32)
    return y0, rgba, prof


def pine(d, x, base, h, w, col):
    d.line([(x, base), (x, base - h)], fill=col, width=max(2, int(w * 0.08)))
    tiers = 6
    for k in range(tiers):
        y_bot = base - h * (0.18 + 0.82 * k / tiers)
        y_top = y_bot - h * 0.30
        half = w * (1 - k / tiers) * 0.5 + 2
        d.polygon([(x - half, y_bot), (x + half, y_bot), (x, y_top)], fill=col)


def shore_layer(deer_lx):
    ss, top = 2, HZ - 280
    img = Image.new("RGBA", (LW * ss, (HZ - top) * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    land = (22, 17, 42, 255)
    tree = (16, 11, 30, 255)
    edge = HZ - 20 + 6 * fbm1d(LW, 4, 120)
    pts = [(x * ss, (edge[x] - top) * ss) for x in range(0, LW, 4)]
    d.polygon([(0, (HZ - top) * ss)] + pts + [(LW * ss, (HZ - top) * ss)], fill=land)
    dens = fbm1d(LW, 3, 260) * 0.5 + 0.5
    x = 0.0
    while x < LW:
        x += rng.uniform(10, 34)
        if deer_lx - 150 < x < deer_lx + 190:      # 鹿身后留空，剪影才看得清
            continue
        if dens[int(min(x, LW - 1))] < 0.35:
            continue
        h = rng.uniform(70, 120) + 140 * dens[int(min(x, LW - 1))] * rng.uniform(0.6, 1.0)
        base = edge[int(min(x, LW - 1))] + 2
        pine(d, x * ss, (base - top) * ss, h * ss, h * 0.38 * ss, tree)
    img = img.resize((LW, HZ - top), Image.LANCZOS)
    a = np.asarray(img, np.float32) / 255
    return top, np.concatenate([a[..., :3] * a[..., 3:4], a[..., 3:4]], -1)


# ---------- 天空 ----------
def sky(sun_y):
    y = np.linspace(0, 1, HZ, dtype=np.float32)
    col = np.zeros((HZ, 3), np.float32)
    for (p0, h0), (p1, h1) in zip(SKY_STOPS, SKY_STOPS[1:]):
        m = (y >= p0) & (y <= p1)
        col[m] = lerp(C(h0), C(h1), ((y[m] - p0) / (p1 - p0))[:, None])
    img = np.repeat(col[:, None, :], W, 1)
    Y, X = np.mgrid[0:HZ, 0:W].astype(np.float32)
    dist = np.hypot(X - SUN_X, Y - sun_y)
    glow = (0.55 * np.exp(-dist / 90) + 0.30 * np.exp(-dist / 320))[..., None] * C("#ffb46e")
    img += glow
    disc = smoothstep(56, 52, dist)[..., None]
    img = lerp(img, C("#fff4dc"), disc)
    bloom = (0.18 * np.exp(-dist / 260))[..., None] * C("#ffcf9a")   # 盖在山上的光晕
    return img, bloom


def clouds():
    y0, y1 = 100, 820
    n = fbm2d(y1 - y0, (W + 400) // 4, 6, 40)                      # 先在窄图上生成，再横向拉 4 倍：晚霞是横条状的
    n = np.asarray(Image.fromarray(n, "F").resize((W + 400, y1 - y0), Image.BICUBIC))
    Y = np.arange(y0, y1, dtype=np.float32)[:, None]
    env = smoothstep(y0, 260, Y) * smoothstep(y1, 600, Y)
    a = smoothstep(0.50, 0.68, n) * env * 0.92
    below = np.roll(a, -10, axis=0)
    lit = np.clip((a - below) * 2.5 + 0.25 + 0.6 * (Y - y0) / (y1 - y0), 0, 1)
    X = np.arange(W + 400, dtype=np.float32)[None, :]
    lit = np.clip(lit + 0.35 * np.exp(-((X - SUN_X - 200) / 300) ** 2) * (Y > 500), 0, 1)
    col = lerp(C("#5a3a7e"), C("#ff9f80"), lit[..., None])
    return y0, np.concatenate([col * a[..., None], a[..., None]], -1).astype(np.float32)


# ---------- 精灵（鸟、鹿、鱼、涟漪、芦苇），2 倍超采样画再缩小 ----------
class Canvas:
    def __init__(self, x0, y0, x1, y1, ss=2):
        self.x0, self.y0, self.w, self.h, self.ss = x0, y0, x1 - x0, y1 - y0, ss
        self.img = Image.new("RGBA", (self.w * ss, self.h * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def P(self, pts):
        return [((x - self.x0) * self.ss, (y - self.y0) * self.ss) for x, y in pts]

    def poly(self, pts, col):
        self.d.polygon(self.P(pts), fill=col)

    def line(self, pts, col, w):
        self.d.line(self.P(pts), fill=col, width=max(1, round(w * self.ss)), joint="curve")

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=1.0):
        (x0, y0), (x1, y1) = self.P([(cx - rx, cy - ry), (cx + rx, cy + ry)])
        self.d.ellipse([x0, y0, x1, y1], fill=fill, outline=outline, width=max(1, round(width * self.ss)))

    def composite(self, frame):
        a = np.asarray(self.img.resize((self.w, self.h), Image.LANCZOS), np.float32) / 255
        reg = frame[self.y0:self.y0 + self.h, self.x0:self.x0 + self.w]
        al = a[..., 3:4]
        reg *= 1 - al
        reg += a[..., :3] * al


def bird(cv, x, y, s, phase, col):
    dy = s * 0.55 * math.sin(phase)
    pts = [(x - s, y + dy), (x - s * 0.45, y - s * 0.16 + dy * 0.35), (x, y),
           (x + s * 0.45, y - s * 0.16 + dy * 0.35), (x + s, y + dy)]
    cv.line(pts, col, max(1.6, s * 0.11))
    cv.ellipse(x, y + 0.5, s * 0.10, s * 0.07, fill=col)


DEER_LX, DEER_S = 330.0, 0.95
DEER_KEYS = [(0, 1.1), (2.4, 1.1), (3.2, -0.95), (6.6, -0.95), (7.4, 1.1), (DUR, 1.1)]


def neck_angle(t):
    for (t0, a0), (t1, a1) in zip(DEER_KEYS, DEER_KEYS[1:]):
        if t0 <= t <= t1:
            a = a0 + (a1 - a0) * float(smoothstep(0, 1, (t - t0) / (t1 - t0)))
            break
    else:
        a = DEER_KEYS[-1][1]
    if a > 0.9:
        a += 0.05 * math.sin(TAU * 1.4 * t)          # 喝水时轻轻一点一点
    return a


TAU = 2 * math.pi


def deer_parts(a, t):
    """鹿的局部坐标（朝右，地面 y=0，向上为负）。返回 (多边形们, 线们, 椭圆们, 嘴的位置)"""
    v = lambda ang: np.array([math.cos(ang), math.sin(ang)])
    perp = lambda ang: np.array([-math.sin(ang), math.cos(ang)])
    ells = [(0, -62, 40, 17), (30, -63, 17, 16), (-32, -64, 16, 17)]
    legs = [[(27, -52), (29, -26), (28, 0)], [(36, -52), (39, -27), (41, 0)],
            [(-34, -58), (-27, -38), (-37, -21), (-33, 0)], [(-26, -58), (-19, -38), (-29, -21), (-25, 0)]]
    fl = 4 * max(0.0, math.sin(t * 3.1)) ** 8
    polys = [[(-45, -74), (-55, -69 - fl), (-46, -63)]]
    base = np.array([38.0, -68.0])
    Hh = base + 44 * v(a)
    sd = perp(a)
    polys.append([(28, -79), tuple(Hh - sd * 6.5), tuple(Hh + sd * 6.5), (47, -55)])
    b = a + lerp(1.3, 0.4, (a + 0.95) / 2.05)
    db, sb = v(b), perp(b)
    polys.append([tuple(p) for p in (Hh - sb * 6.5 - db * 3, Hh + db * 22 - sb * 3, Hh + db * 27,
                                     Hh + db * 22 + sb * 3.5, Hh + sb * 6.5 - db * 2)])
    ea = b - 2.5 + 0.18 * math.sin(t * 6.0) * (a < 0)
    root = Hh - sb * 4
    polys.append([tuple(root - perp(ea) * 3), tuple(root + v(ea) * 13), tuple(root + perp(ea) * 3)])
    lines = [legs[0], legs[1], legs[2], legs[3]]
    for k, dd in enumerate((0.0, 0.18)):
        aa = b - 1.95 + dd
        p0 = Hh - sb * 5 + db * (4 + 2 * k)
        p1 = p0 + v(aa) * 15
        p2 = p1 + v(aa - 0.55) * 13
        p3 = p2 + v(aa - 0.25) * 8
        lines.append([tuple(p) for p in (p0, p1, p2, p3)])
        lines.append([tuple(p1), tuple(p1 + v(aa + 0.75) * 8)])
        lines.append([tuple(p2), tuple(p2 + v(aa + 0.6) * 7)])
    muzzle = Hh + db * 27
    return polys, lines, ells, muzzle


def draw_deer(cv, ox, oy, a, t):
    polys, lines, ells, _ = deer_parts(a, t)
    s = DEER_S
    for col, (sx, sy) in (((255, 176, 128, 210), (1.4, -1.4)), ((14, 9, 26, 255), (0, 0))):   # 先画逆光描边，再盖剪影
        T = lambda p: (ox + p[0] * s + sx, oy + p[1] * s + sy)
        for cx, cy, rx, ry in ells:
            x, y = T((cx, cy))
            cv.ellipse(x, y, rx * s, ry * s, fill=col)
        if sx == 0:                                    # 腿细，描边会像重影，只画剪影
            for L in lines[:4]:
                cv.line([T(p) for p in L], col, 5.5 * s)
        for L in lines[4:]:
            cv.line([T(p) for p in L], col, 2.6 * s)
        for P in polys:
            cv.poly([T(p) for p in P], col)


def ripple(cv, x, y, age, life, r0, grow, flat, alpha0):
    if 0 <= age < life:
        r = r0 + grow * age
        al = int(alpha0 * (1 - age / life) ** 1.5)
        cv.ellipse(x, y, r, r * flat, outline=(255, 214, 176, al), width=1.3)


FISH_T0, FISH_DUR, FISH_X, FISH_Y, FISH_H = 4.3, 1.0, 700.0, 1490.0, 115.0
splash_rng = np.random.default_rng(5)
SPLASH = {k: (splash_rng.uniform(-70, 70, 14), splash_rng.uniform(-190, -70, 14), splash_rng.uniform(1.5, 3.2, 14))
          for k in ("out", "in")}


def fish_and_splash(cv, t, off):
    x0 = FISH_X - off
    tau = (t - FISH_T0) / FISH_DUR
    if 0 <= tau <= 1:
        fx = x0 + 85 * tau
        fy = FISH_Y - 4 * FISH_H * tau * (1 - tau)
        ang = math.atan2(-4 * FISH_H * (1 - 2 * tau), 85)
        c, s = math.cos(ang), math.sin(ang)
        R = lambda px, py: (fx + px * c - py * s, fy + px * s + py * c)
        body = [R(27 * math.cos(q), 9.5 * math.sin(q)) for q in np.linspace(0, TAU, 28)]
        tail = [R(-22, 0), R(-40, -11), R(-36, 0), R(-40, 11)]
        for col, dy in (((255, 190, 140, 200), -1.3), ((20, 14, 34, 255), 0)):
            cv.poly([(p[0], p[1] + dy) for p in body], col)
            cv.poly([(p[0], p[1] + dy) for p in tail], col)
    for key, te, xe in (("out", FISH_T0, x0), ("in", FISH_T0 + FISH_DUR, x0 + 85)):
        age = t - te
        vx, vy, rr = SPLASH[key]
        if 0 <= age < 0.75:
            for i in range(len(vx)):
                px, py = xe + vx[i] * age, FISH_Y + vy[i] * age + 420 * age * age
                if py <= FISH_Y + 2:
                    cv.ellipse(px, py, rr[i], rr[i], fill=(255, 220, 185, int(230 * (1 - age / 0.75))))
        for k in range(3):
            ripple(cv, xe, FISH_Y + 2, age - 0.16 * k, 1.8, 8, 60, 0.20, 190)


REEDS = []
for side, xs in (("L", np.linspace(-30, 230, 9)), ("R", np.linspace(850, 1110, 8))):
    for x in xs:
        REEDS.append(dict(x=x + rng.uniform(-15, 15), h=rng.uniform(320, 640), lean=rng.uniform(-0.12, 0.12)
                          + (0.08 if side == "L" else -0.08), ph=rng.uniform(0, TAU), w=rng.uniform(6, 10),
                          cat=rng.random() < 0.35))


def reeds(cv, t, off):
    for r in REEDS:
        sway = 0.05 * math.sin(1.2 * t + r["ph"]) + 0.02 * math.sin(2.9 * t + r["ph"] * 2)
        pts, x, y, ang = [], r["x"] - off, H + 20, -math.pi / 2 + r["lean"]
        n = 14
        for i in range(n + 1):
            pts.append((x, y))
            ang += (r["lean"] * 0.08 + sway * 0.25) * (i / n)
            x += math.cos(ang) * r["h"] / n
            y += math.sin(ang) * r["h"] / n
        left, right = [], []
        for i, (px, py) in enumerate(pts):
            w = r["w"] * (1 - i / (n + 1)) + 0.8
            left.append((px - w / 2, py))
            right.append((px + w / 2, py))
        cv.poly(left + right[::-1], (9, 6, 18, 255))
        if r["cat"]:
            px, py = pts[-4]
            cv.ellipse(px, py, 5, 18, fill=(20, 12, 22, 255))


# ---------- 水 ----------
WN = tile_noise(512, 5, 128)
ROWS = H - HZ
_d = np.arange(ROWS, dtype=np.float32)[:, None] + 6
PERSP = _d / ROWS
U0 = 256 + (np.arange(W, dtype=np.float32)[None, :] - W / 2) * 210 / _d     # 透视：近处一个像素对应的水面小，远处大
V0 = 210000 / _d
XG = np.arange(W, dtype=np.float32)[None, :]
DEEP = lerp(C("#1c1636"), C("#0a0716"), PERSP[..., None])
GLIT_MASK = np.exp(-((XG - SUN_X) / (18 + 170 * PERSP)) ** 2) * (1 - 0.55 * PERSP)


def water(above, t):
    u, v = U0 + 4 * t, V0 - 14 * t
    n1 = sample(WN, u, v)
    n2 = sample(WN, u * 0.5 + 91, v * 0.5 + 37)
    dx = (1.0 + 18 * PERSP ** 1.3) * (n1 - 0.5) * 2
    dy = (0.5 + 9 * PERSP) * (n2 - 0.5) * 2
    sy = np.clip(np.rint(HZ - 1 - (_d - 6) * 1.0 + dy), 0, HZ - 1).astype(np.int64)
    sx = np.clip(np.rint(XG + dx), 0, W - 1).astype(np.int64)
    refl = above[sy, sx] * C("#e8e0ff")
    k = (0.93 - 0.42 * PERSP)[..., None]
    col = refl * k + DEEP * (1 - k)
    crest = np.clip((sample(WN, u, v + 2.5) - n1) * 7 - 0.05, 0, 1) * (0.25 + 0.75 * PERSP)
    col += (0.16 * crest)[..., None] * WARM
    g = np.clip((sample(WN, u * 1.9 + 17, v * 1.9 + 3) - 0.60) * 7, 0, 1) * GLIT_MASK
    col += (1.15 * g)[..., None] * C("#fff0d0")
    return col


# ---------- 合成 ----------
def build_scene():
    t0 = time.time()
    layers = []
    for p, args in ((0.10, dict(base_y=1000, amp=430, length=900, ridge_hex="#a184bd", base_hex="#d9a2b2", mist=0.55, rim=0.55, snow=True)),
                    (0.22, dict(base_y=1065, amp=300, length=620, ridge_hex="#6f5490", base_hex="#b07f9f", mist=0.50, rim=0.45)),
                    (0.38, dict(base_y=1112, amp=220, length=460, ridge_hex="#4a3a6e", base_hex="#7d5c86", mist=0.45, rim=0.35)),
                    (0.56, dict(base_y=1150, amp=130, length=380, ridge_hex="#2c2448", base_hex="#544067", mist=0.40, rim=0.25, smooth_w=0.6))):
        y0, rgba, prof = mountain(**args)
        layers.append((p, y0, rgba))
        if p == 0.10:
            sun_y = float(prof[SUN_X + int(PAN * 0.10 * 0.5)]) - 64
    sky_img, bloom = sky(sun_y)
    cy0, cloud = clouds()
    sy0, shore = shore_layer(DEER_LX)
    layers.append((0.75, sy0, shore))
    print(f"场景生成 {time.time() - t0:.1f}s，太阳 y={sun_y:.0f}")
    return sky_img, bloom, (cy0, cloud), layers


def drink_ripples():
    out, t = [], 0.3
    while t < DUR:
        if neck_angle(t) > 0.9:
            out.append(t)
        t += 1.25
    return out


def render_frame(scene, t):
    sky_img, bloom, (cy0, cloud), layers = scene
    e = ease(t / DUR)
    above = sky_img.copy()
    over_pm(above[cy0:cy0 + cloud.shape[0]], shift_crop(cloud, 40 + 7 * t + 0.05 * PAN * e))
    for p, y0, rgba in layers:
        over_pm(above[y0:HZ], shift_crop(rgba, p * PAN * e))
    above += bloom
    shore_off = 0.75 * PAN * e

    cv = Canvas(0, 300, W, HZ)
    lead = (-140 + 88 * t, 720 - 10 * t)
    for k, (ox, oy) in enumerate([(0, 0), (-30, -15), (-30, 15), (-60, -30), (-60, 30), (-90, -45), (-90, 45)]):
        bird(cv, lead[0] + ox + 3 * math.sin(t * 1.3 + k), lead[1] + oy + 2.5 * math.sin(t * 2 + k * 1.7),
             17, TAU * 2.6 * t + k * 0.7, (24, 16, 40, 255))
    for k, (ox, oy) in enumerate([(0, 0), (22, -9), (40, 6)]):
        bird(cv, 1150 - 46 * t + ox, 470 + oy + 2 * math.sin(t * 1.7 + k), 10, TAU * 3.2 * t + k, (40, 28, 70, 230))
    a = neck_angle(t)
    draw_deer(cv, DEER_LX - shore_off, HZ - 6, a, t)
    cv.composite(above)

    frame = np.concatenate([above, water(above, t)], 0)
    Y = np.arange(HZ - 160, HZ + 160, dtype=np.float32)[:, None, None]
    frame[HZ - 160:HZ + 160] = lerp(frame[HZ - 160:HZ + 160], C("#f4b48e"), 0.16 * np.exp(-((Y - HZ) / 50) ** 2))
    frame[HZ:HZ + 2] = lerp(frame[HZ:HZ + 2], WARM, 0.35)

    cv2 = Canvas(0, HZ - 10, W, H)
    _, _, _, muzzle = deer_parts(1.1, 0)
    mx = DEER_LX + muzzle[0] * DEER_S - shore_off
    for t0 in DRINK:
        for k in range(2):
            ripple(cv2, mx, HZ + 4, t - t0 - 0.25 * k, 2.2, 3, 26, 0.13, 200)
    fish_and_splash(cv2, t, 0.85 * PAN * e)
    reeds(cv2, t, 1.25 * PAN * e)
    cv2.composite(frame)

    frame *= VIGNETTE
    frame += GRAIN[int(t * 30) % len(GRAIN)]
    return np.clip(frame, 0, 1)


DRINK = drink_ripples()
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.38 * (((_xx - W / 2) / (W * 0.75)) ** 2 + ((_yy - H * 0.55) / (H * 0.62)) ** 2))[..., None].clip(0.55, 1)
GRAIN = [np.random.default_rng(i).normal(0, 0.012, (H, W, 1)).astype(np.float32) for i in range(6)]


def main(out_dir) -> None:
    OUT_DIR = Path(out_dir)
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--still", type=float, default=None, help="只渲染这一秒的一帧 PNG")
    ap.add_argument("--out", default=str(OUT_DIR / "landscape.mp4"))
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    if args.still is not None:
        img = render_frame(scene, args.still)
        p = OUT_DIR / f"landscape_still_{args.still:.1f}s.png"
        Image.fromarray((img * 255).astype(np.uint8)).save(p)
        print("静帧 →", p)
        return
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    n = int(DUR * args.fps)
    proc = subprocess.Popen([ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(args.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(n):
        proc.stdin.write((render_frame(scene, i / args.fps) * 255).astype(np.uint8).tobytes())
        if i % 30 == 0:
            print(f"  帧 {i}/{n}  {time.time() - t0:.0f}s")
    proc.stdin.close()
    proc.wait()
    print(f"成片 → {args.out}（{n} 帧，用时 {time.time() - t0:.0f}s）")


if __name__ == "__main__":
    main(Path.cwd() / "renders")
