"""样片 A · 火柴人 VS 物理：一脚把球踢出去，球撞墙、落地、弹回来，被一脚停在脚下。

画面上的物理全是算出来的（g = 9.8 m/s²，火柴人按 1.75 米换算成像素）：
    - 踢中那一刻，预测的抛物线（虚线）先画出来，球再沿着它飞；
    - 每 1/15 秒留一个残影（频闪照片）。同一段飞行里残影的水平间距相等——水平匀速、竖直匀加速；
    - 撞墙、落地按恢复系数反弹（墙 0.7、地面 0.6），每一段都是新的抛物线。
停球的时间和位置也是解出来的：火柴人的脚按算出的落点去接。
"""
import math

from vlab.stick.rig import FOOT_Y, G, GROUND, PX_PER_M, STAND_Y, K, Track
from vlab.stick.scene import Figure, Scene

FPS = 30
GOLD, CYAN = "#f3c14b", "#49e3d1"
R = 22.0                      # 球半径：0.116 m，约一个足球
BALL_X = 640.0
REST_Y = GROUND - R
WALL_X = 1700.0
T_KICK = 2.0
V0, ANGLE = 1700.0, 45.0      # 出球速度（px/s，约 9 m/s）和仰角
E_WALL, E_FLOOR = 0.7, 0.6    # 墙、地面的恢复系数


def flight():
    """从踢中开始逐段解析求解：自由飞行 → 撞墙或落地 → 按恢复系数反弹。
    返回每段 (t0, x0, y0, vx, vy, t1, 结束事件)。屏幕坐标 y 向下。"""
    segs = []
    t, x, y = T_KICK, BALL_X, REST_Y
    a = math.radians(ANGLE)
    vx, vy = V0 * math.cos(a), -V0 * math.sin(a)
    for _ in range(3):                     # 踢出 → 撞墙 → 落地 → 再落地（停球）
        cands = []
        if vx > 0:
            cands.append(((WALL_X - R - x) / vx, "wall"))
        A, B, C = 0.5 * G, vy, y - REST_Y
        s = (-B + math.sqrt(max(0.0, B * B - 4 * A * C))) / (2 * A)
        if s > 1e-6:
            cands.append((s, "floor"))
        s, ev = min(cands)
        segs.append((t, x, y, vx, vy, t + s, ev))
        x, y, vy = x + vx * s, y + vy * s + 0.5 * G * s * s, vy + G * s
        if ev == "wall":
            vx = -E_WALL * vx
        else:
            vy = -E_FLOOR * vy
        t += s
    return segs


def at(segs, t):
    if t < segs[0][0]:
        return BALL_X, REST_Y
    for t0, x0, y0, vx, vy, t1, _ in segs:
        if t <= t1:
            s = t - t0
            return x0 + vx * s, y0 + vy * s + 0.5 * G * s * s
    t0, x0, y0, vx, vy, t1, _ = segs[-1]
    s = t1 - t0
    return x0 + vx * s, y0 + vy * s + 0.5 * G * s * s


def build():
    segs = flight()
    t_wall = segs[0][5]
    t_bounce = segs[1][5]
    t_trap = segs[2][5]
    x_wall, y_wall = at(segs, t_wall)
    x_bounce, _ = at(segs, t_bounce)
    x_trap, _ = at(segs, t_trap)
    end = t_trap + 2.2
    sc = Scene(end, FPS)
    sc.grid = True

    def breath(t):
        return {"y": 1.6 * math.sin(2 * math.pi * 0.35 * t), "head": 1.2 * math.sin(2 * math.pi * 0.35 * t + 1.0)}

    keys = [
        K(0.00, x=380, y=STAND_Y, lean=2, head=16, aF=-4, fF=6, aB=8, fB=16,
          footF=(402, FOOT_Y), footB=(356, FOOT_Y)),
        K(0.85, x=380, y=STAND_Y + 2, lean=3, head=18),
        # 预备：重心下沉、两臂往后
        K(1.05, x=372, y=STAND_Y + 10, lean=-3, head=12, aF=-28, fF=-12, aB=-32, fB=-18),
        # 助跑两步
        K(1.25, x=440, y=STAND_Y + 2, lean=13, head=8, aF=38, fF=75, aB=-40, fB=-22, footB=(472, FOOT_Y)),
        K(1.45, "linear", x=508, y=STAND_Y, lean=15, head=8, aF=-42, fF=-18, aB=40, fB=78, footF=(545, FOOT_Y)),
        # 支撑脚踩在球旁，踢球腿往后摆
        K(1.68, x=556, y=STAND_Y + 12, lean=6, head=20, aF=-50, fF=-34, aB=58, fB=84,
          footB=(588, FOOT_Y), tF=-38, sF=-108),
        K(1.82, "out", x=566, y=STAND_Y + 14, lean=2, head=22, aF=-58, fF=-40, aB=70, fB=92, tF=-52, sF=-118),
        # 踢中：脚背从球的左下方铲上去
        K(T_KICK, "in", x=578, y=STAND_Y + 10, lean=-6, head=16, aF=-66, fF=-48, aB=78, fB=100, footF=(619, 854)),
        # 随球：腿顺势踢高，人后仰、抬头看球
        K(2.22, "out", x=598, y=STAND_Y - 6, lean=-14, head=-12, aF=-30, fF=10, aB=95, fB=120, tF=112, sF=128),
        K(2.55, x=616, y=STAND_Y + 6, lean=2, head=-20, aF=6, fF=26, aB=-6, fB=12, footF=(660, FOOT_Y)),
        K(t_wall, x=618, y=STAND_Y + 4, lean=0, head=-12),
        K(t_bounce, x=620, y=STAND_Y + 6, head=4),
        K(t_bounce + 0.3, x=622, y=STAND_Y + 8, lean=4, head=6, aF=10, fF=30),
        # 停球：先抬脚等球，球落地那一刻脚掌正好压在球顶上
        K(t_trap - 0.2, x=630, y=STAND_Y + 10, lean=6, head=22, aF=-10, fF=20, aB=20, fB=40,
          footF=(x_trap + 12, FOOT_Y - 74)),
        K(t_trap, "in", lift=8, x=636, y=STAND_Y + 12, lean=8, head=30, footF=(x_trap, REST_Y - R - 5)),
        # 停住了：握拳往下一拉（"漂亮"），然后放松，两臂离开身体一点，侧面也看得见手
        K(t_trap + 0.30, "out", x=632, y=STAND_Y + 6, lean=2, head=14, aF=62, fF=152, aB=-14, fB=0),
        K(t_trap + 0.46, "snap", x=630, y=STAND_Y + 10, lean=9, head=26, aF=48, fF=100, aB=-16, fB=-4),
        K(t_trap + 1.1, x=630, y=STAND_Y + 6, lean=3, head=18, aF=16, fF=30, aB=-14, fB=-6),
    ]
    sc.add(Figure("gold", Track(keys, face=1, extra=breath), GOLD))

    # —— 球：逐帧位置 + 旋转、频闪残影、预测虚线 ——
    n = round(sc.total * FPS)
    ball, ghosts = [], []
    spin = 0.0
    for f in range(n):
        t = f / FPS
        x, y = at(segs, min(t, t_trap))
        if T_KICK <= t <= t_trap:
            spin -= 14.0
            if f % 2 == 0:
                ghosts.append([f, round(x, 1), round(y, 1)])
        ball.append([round(x, 1), round(y, 1), round(spin, 1)])
    sc.layers["balls"].append({"color": CYAN, "r": R, "p": ball})
    sc.layers["ghosts"].append({"color": CYAN, "r": R, "pts": ghosts})
    for seg in segs:
        t0, t1 = seg[0], seg[5]
        pts = [[round(v, 1) for v in at(segs, t0 + (t1 - t0) * i / 60)] for i in range(61)]
        sc.layers["paths"].append({"color": CYAN, "f0": t0 * FPS, "f1": t0 * FPS + 0.3 * FPS, "pts": pts})
    sc.layers["walls"].append({"x": WALL_X, "y0": 300, "y1": GROUND})
    fk = T_KICK * FPS
    sc.layers["arcs"].append({"f0": fk, "f1": fk + 50, "x": BALL_X, "y": REST_Y, "r": 64, "a0": 0, "a1": -ANGLE})
    sc.layers["labels"].append({"f0": fk + 4, "f1": fk + 50, "x": BALL_X + 112, "y": REST_Y - 30, "text": "45°", "size": 36})
    sc.layers["labels"].append({"f0": (t_trap + 0.5) * FPS, "x": 1180, "y": 330, "text": "残影间隔 1/15 秒",
                                "size": 30, "color": "#9fb0c8"})

    # —— 粒子、震屏、音效（全部绑在算出来的事件时刻上）——
    sc.burst(1.68, 588, GROUND, "dust", n=8, speed=140, angle=-90, spread=140, life=22, size=9, color="#c9cfdb")
    sc.burst(T_KICK, 624, 850, "flare", size=34, life=7, color=CYAN)
    sc.burst(T_KICK, 624, 850, "ring", size=12, speed=96, life=12, color=CYAN)
    sc.burst(T_KICK, 600, GROUND, "dust", n=10, speed=200, angle=-60, spread=90, life=20, size=8, color="#c9cfdb")
    sc.burst(t_wall, WALL_X, y_wall, "spark", n=16, speed=720, angle=180, spread=110, life=16, size=3.6, color=CYAN, g=900)
    sc.burst(t_wall, WALL_X, y_wall, "ring", size=8, speed=110, life=14, color=CYAN)
    sc.burst(t_wall, WALL_X, y_wall, "flare", size=30, life=6, color=CYAN)
    sc.burst(t_bounce, x_bounce, GROUND, "dust", n=10, speed=190, angle=-90, spread=170, life=20, size=9, color="#c9cfdb")
    sc.burst(t_bounce, x_bounce, GROUND - 2, "ring", size=6, speed=70, life=10, color=CYAN)
    sc.burst(t_trap, x_trap, GROUND, "dust", n=7, speed=120, angle=-90, spread=170, life=18, size=8, color="#c9cfdb")
    sc.shake(T_KICK, 3, 0.25)
    sc.shake(t_wall, 4, 0.3)
    for t, g in ((1.25, 0.45), (1.45, 0.5), (1.68, 0.7), (2.55, 0.5)):
        sc.sfx(t, "step", g)
    sc.sfx(1.86, "whip", 0.3)
    sc.sfx(T_KICK, "kick", 1.0)
    sc.sfx(t_wall, "knock", 0.85)
    sc.sfx(t_bounce, "bounce", 0.75)
    sc.sfx(t_trap, "bounce", 0.4)
    sc.sfx(t_trap, "step", 0.55)

    sc.camera(0.0, 600, 650, 1.32)
    sc.camera(1.5, 612, 650, 1.32)
    sc.camera(T_KICK, 640, 640, 1.28)
    sc.camera(2.7, 1010, 575, 1.0)
    sc.camera(t_trap, 1000, 580, 1.0)
    sc.camera(end, 985, 590, 1.05, "sine")

    info = {"t_wall": t_wall, "y_wall": GROUND - y_wall, "t_bounce": t_bounce, "x_bounce": x_bounce,
            "t_trap": t_trap, "x_trap": x_trap, "px_per_m": PX_PER_M, "g": G}
    return sc, info
