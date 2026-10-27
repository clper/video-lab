"""009《他比我重一倍，我借了他的力》的动作编排（剧本 v0.2，2026-10-27 确认）。

坐标、角度的约定见 vlab/stick/rig.py。时间有两套（见 vlab/stick/scene.py）：
    动作时间 —— 关键帧和物理用；真实时间 —— 成片用，120 BPM 拍格，关键动作落在小节第一拍。
两者的对应关系在 timemap()：三处定格（撞上、拳头逼近、—）、两处慢放（踉跄、过肩摔）。

角色：金 = 小个子，60 kg，1.70 m；青 = 大块头，120 kg，2.05 m。
"""
import math

from vlab.stick.rig import BODY, GROUND, K, Track, com
from vlab.stick.scene import Figure, Scene

FPS = 30
TOTAL = 120.0
GOLD, CYAN, WHITE, RED = "#f3c14b", "#49e3d1", "#e8f0ff", "#ff5b5b"
HERO = BODY.scaled(1.70 / 1.75)
BIG = BODY.scaled(2.05 / 1.75, width=15.0)
M_HERO, M_BIG = 60.0, 120.0

# —— 动作时间上的关键时刻 ——
A_HIT = 16.0          # 第一回合：拳打在交叉的小臂上（真实 16.0，之后定格 6 秒）
OFF = 6.0             # 定格之后：动作时间 = 真实时间 - 6
A_PUSH = 32.0         # 一掌推飞（真实 38.0）
A_SWAT = 44.0         # 扇羽毛（真实 50.0）
A_PUNCH = 58.6        # 拳头逼近、定格（真实 67–72）
A_PARRY = 58.72       # 轻轻一拨（真实 ≈ 72.1）
A_TOPPLE = 64.0       # 重心越过前脚，交给物理（真实 ≈ 78）
A_FALL = 65.3         # 预计砸地（真实 80.0；以物理算出来的为准，见 timemap）
A_GRAB = A_FALL + 13.5   # 抓住手腕（真实 93.5）
A_END = 140.0


def timemap(fall_hit, land):
    """真实秒 → 动作秒。fall_hit、land 是物理算出来的砸地时刻：让它们正好落在 80.0、100.0 秒"""
    return [(0.0, 0.0), (16.0, A_HIT), (22.0, A_HIT),            # S04 末撞上 → S05 定格
            (64.0, 58.0), (67.0, A_PUNCH), (72.0, A_PUNCH),      # S14 拳头逼近放慢 → S15 定格
            (77.0, A_PUNCH + 5.0), (79.1, fall_hit - 0.9),       # S17 踉跄慢放：重心越过脚尖
            (80.0, fall_hit),                                    # 正常速度砸地
            (93.5, A_GRAB), (98.0, A_GRAB + 0.25),               # S20 抓住、转身、沉腰：极慢
            (99.6, A_GRAB + 0.65), (100.0, land),                # S21 翻过去慢放 → 砸地
            (120.0, land + 20.0)]


# —— 姿势工具 ——
ARMS = {
    "relax": dict(aF=6, fF=14, aB=-8, fB=4),
    "guard": dict(aF=35, fF=155, aB=18, fB=165),
    "block": dict(aF=72, fF=176, aB=58, fB=178),
    "open": dict(aF=28, fF=70, aB=14, fB=50),
    "low": dict(aF=14, fF=40, aB=-4, fB=24),
}


def leg(body):
    return body.thigh + body.shin


def feet(body, x, face, spread=0.28, front=None, back=None):
    L = leg(body)
    f = spread * L if front is None else front
    b = spread * L if back is None else back
    return (x + face * f, body.foot_y), (x - face * b, body.foot_y)


def hip(body, spread=0.28, bend=6.0):
    L = leg(body)
    return body.foot_y - L * math.sqrt(1 - spread * spread) + bend


def P(t, body, x, face, ease="inout", spread=0.28, bend=6.0, lean=4.0, head=0.0, arms="relax", ft=None, lift=26.0,
      **kw):
    """一个站姿关键帧：两脚踩地（IK），骨盆高度按两脚的距离算"""
    fF, fB = ft if ft else feet(body, x, face, spread)
    ch = dict(x=x, y=hip(body, spread, bend), lean=lean, head=head)
    if arms:
        ch.update(ARMS[arms])
    ch.update(kw)
    for k in ("footF", "footB"):
        kw.pop(k, None)
    return K(t, ease, face=face, lift=lift, footF=ch.pop("footF", fF), footB=ch.pop("footB", fB), **ch)


def walk(body, face, t0, x0, x1, n, dur, first="F", lean=5.0, swing=24.0, lift=0.12, heavy=False, head=0.0,
         arms=None):
    """从站姿走到 x1：每一步一个"摆腿过身体"的关键帧 + 一个"落脚"的关键帧（两脚着地）。
    落脚时前脚在骨盆前半步、后脚在后半步，骨盆高度按两脚分开的距离算（腿够得着，不会飘）；
    摆腿时支撑脚正好在骨盆下面、腿几乎伸直，骨盆自然升高——走路的起伏就是这么来的。"""
    keys = []
    L = leg(body)
    d = 1 if x1 >= x0 else -1
    stride = (x1 - x0) / n
    reach = abs(stride) / 2
    y_c = body.foot_y - math.sqrt(max(L * L - reach * reach, (0.6 * L) ** 2)) + (8 if heavy else 4)
    y_m = body.foot_y - 0.975 * L
    mover = first
    for i in range(n):
        tm, te = t0 + (i + 0.5) * dur, t0 + (i + 1) * dur
        pm, pe = x0 + stride * (i + 0.5), x0 + stride * (i + 1)
        sw = swing if (mover == "F") == (d == face) else -swing
        arm_c = dict(aF=-sw, fF=-sw * 0.4 + 12, aB=sw, fB=sw * 0.6 + 12) if arms is None else ARMS[arms]
        arm_m = dict(aF=4, fF=16, aB=4, fB=16) if arms is None else ARMS[arms]
        keys.append(K(tm, "linear", face=face, lift=0, x=pm, y=y_m, lean=lean, head=head,
                      **{"foot" + mover: (pm + d * 0.04 * L, body.foot_y - lift * L)}, **arm_m))
        keys.append(K(te, "out2" if heavy else "linear", face=face, lift=0, x=pe, y=y_c, lean=lean, head=head,
                      **{"foot" + mover: (pe + d * reach, body.foot_y)}, **arm_c))
        mover = "B" if mover == "F" else "F"
    return keys


def run(body, face, t0, x0, x1, durs, first="F", lean=16.0, head=0.0, arms_swing=50.0, fly=14.0):
    """跑：每步一个"落脚"关键帧（一只脚着地在前、另一只在后面抬起）和一个"腾空"关键帧。durs 是每步的时长"""
    keys = []
    L = leg(body)
    d = 1 if x1 >= x0 else -1
    total = sum(durs)
    y0 = hip(body, 0.22, 10)
    mover = first
    t = t0
    for i, du in enumerate(durs):
        a = sum(durs[:i]) / total
        b = sum(durs[:i + 1]) / total
        # 位移按时间的二次方分配：越跑越快
        pm = x0 + (x1 - x0) * ((a + b) / 2) ** 1.4
        pe = x0 + (x1 - x0) * b ** 1.4
        other = "B" if mover == "F" else "F"
        sw = arms_swing if (mover == "F") == (d == face) else -arms_swing
        keys.append(K(t + du * 0.5, "linear", face=face, lift=0, x=pm, y=y0 - fly, lean=lean, head=head,
                      **{"foot" + mover: (pm + d * 0.18 * L, body.foot_y - 0.22 * L),
                         "foot" + other: (pm - d * 0.32 * L, body.foot_y - 0.2 * L)},
                      aF=0, fF=70, aB=0, fB=70))
        keys.append(K(t + du, "linear", face=face, lift=0, x=pe, y=y0, lean=lean, head=head,
                      **{"foot" + mover: (pe + d * 0.2 * L, body.foot_y),
                         "foot" + other: (pe - d * 0.42 * L, body.foot_y - 0.16 * L)},
                      aF=-sw, fF=-sw * 0.3 + 70, aB=sw, fB=sw * 0.3 + 70))
        mover = other
        t += du
    return keys


def getup_back(body, face, t0, pose, x_end, ease_t=(0.6, 1.2, 1.9), arms_end="relax"):
    """仰面躺着 → 坐起 → 蹲 → 站。pose 是布偶最后的姿势"""
    L = leg(body)
    xp = pose["x"]
    # 头在骨盆的哪一边：头朝后（-face 方向）躺的是仰面倒下，坐起来时脚伸向 face 方向
    t1, t2, t3 = (t0 + d for d in ease_t)
    sit = K(t1, "out", face=face, x=xp, y=GROUND - 12, lean=-24, head=14,
            handF=(xp - face * 46, body.foot_y), handB=(xp - face * 36, body.foot_y),
            footF=(xp + face * 0.62 * L, body.foot_y), footB=(xp + face * 0.5 * L, body.foot_y))
    crouch = K(t2, "inout", face=face, x=xp + face * 0.3 * L, y=body.foot_y - 0.52 * L, lean=34, head=10,
               aF=30, fF=40, aB=24, fB=36,
               footF=(xp + face * 0.42 * L, body.foot_y), footB=(xp + face * 0.18 * L, body.foot_y))
    stand = P(t3, body, x_end, face, arms=arms_end)
    return [K(t0, "linear", face=face, **pose), sit, crouch, stand]


def getup_front(body, face, t0, pose, x_end, ease_t=(0.7, 1.4, 2.2)):
    """趴着 → 撑起 → 单膝跪 → 站"""
    L = leg(body)
    xp = pose["x"]
    t1, t2, t3 = (t0 + d for d in ease_t)
    push = K(t1, "out", face=face, x=xp, y=GROUND - 0.32 * L, lean=70, head=-20,
             handF=(xp + face * 0.95 * body.torso, body.foot_y), handB=(xp + face * 0.85 * body.torso, body.foot_y),
             footF=(xp - face * 0.55 * L, body.foot_y), footB=(xp - face * 0.65 * L, body.foot_y))
    kneel = K(t2, "inout", face=face, x=xp + face * 0.15 * L, y=body.foot_y - 0.48 * L, lean=30, head=-6,
              aF=40, fF=60, aB=30, fB=50,
              footF=(xp + face * 0.45 * L, body.foot_y), footB=(xp - face * 0.25 * L, body.foot_y - 0.02 * L))
    stand = P(t3, body, x_end, face, arms="low")
    return [K(t0, "linear", face=face, **pose), push, kneel, stand]


def lying(t0, t1, pose, face, breathe=1.6):
    """躺着喘气：只动躯干一点点"""
    return [K(t0, "linear", face=face, **pose), K(t1, "linear", face=face, **pose)]


def mid(a, b, k=0.5):
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)


def chest(J, k=0.55):
    return mid(J[0], J[1], k)


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


STOMPS = (0.5, 1.5, 2.5, 3.5)          # 大块头进场的四步重脚步（在拍上）
FLURRY = (26.0, 26.5, 27.0, 27.5)      # 小个子连打四拳（真实 32.0–33.5，在拍上）


# ============================== 金：小个子 ==============================

def hero_base():
    """0 → 16.0：被大块头的气势压着，最后举起双臂硬挡"""
    b, f = HERO, 1

    def extra(t):
        w = max(0.0, min(1.0, (t - 9.6) / 0.3, (13.2 - t) / 0.3))                 # 举起拳头以后紧张地颠
        flinch = sum(5.0 * math.exp(-((t - s) / 0.09) ** 2) for s in STOMPS)       # 每一声重脚步，头一缩
        return {"y": 3.0 * w * math.sin(2 * math.pi * 2.0 * t), "head": flinch}

    keys = [P(0.0, b, 720, f, spread=0.24, lean=2, head=-4),
            P(2.3, b, 720, f, spread=0.24, lean=1, head=-6),
            P(2.9, b, 702, f, spread=0.26, lean=-3, head=-8, lift=12),             # 被吓得退了小半步
            P(4.8, b, 702, f, spread=0.26, lean=-3, head=-16),                      # 抬头看他
            P(8.7, b, 702, f, spread=0.26, lean=-2, head=-14),
            P(9.5, b, 704, f, spread=0.31, bend=12, lean=8, head=-6, arms="guard"),
            P(13.4, b, 704, f, spread=0.31, bend=12, lean=8, head=-6, arms="guard"),
            P(15.0, b, 698, f, spread=0.35, bend=20, lean=12, head=6, arms="block"),   # 看他冲过来，交叉双臂硬挡
            P(A_HIT, b, 698, f, spread=0.35, bend=20, lean=13, head=8, arms="block")]
    return Track(keys, face=f, body=b, extra=extra)


def kick_hit(i):
    """120 kg 的拳头连着冲劲打在交叉的小臂上：小个子约 3.5 m/s 往后飞，上身比脚快，会向后翻"""
    back = {2: 760, 1: 740, 3: 720, 4: 720, 5: 720, 6: 720, 0: 600, 7: 480, 9: 480, 8: 380, 10: 380}
    up = {2: 430, 1: 440, 3: 440, 4: 440, 5: 440, 6: 440, 0: 330, 7: 230, 9: 230, 8: 130, 10: 130}
    return -back[i], -up[i]


def kick_push(i):
    """一掌推在胸口：约 4.5 m/s，比第一次飞得远"""
    back = {2: 940, 1: 920, 3: 900, 4: 900, 5: 900, 6: 900, 0: 760, 7: 580, 9: 580, 8: 440, 10: 440}
    up = {2: 560, 1: 560, 3: 560, 4: 560, 5: 560, 6: 560, 0: 420, 7: 260, 9: 260, 8: 140, 10: 140}
    return -back[i], -up[i]


def hero_after_hit(tg):
    """第一次被打飞以后：爬起来、甩甩头、冲回去连打四拳、打累了"""
    def then(pose, t0):
        b, f = HERO, 1
        x_up = pose["x"] + 30
        keys = getup_back(b, f, t0, pose, x_up, (0.6, 1.2, 1.8))
        t = t0 + 1.8
        keys += [K(t + 0.2, "inout", face=f, head=-16), K(t + 0.4, "inout", face=f, head=12),
                 K(t + 0.6, "inout", face=f, head=-8), K(t + 0.8, "inout", face=f, head=0, lean=8)]   # 甩甩头
        xf = tg["flurry_x"]
        keys += run(b, f, 23.9, x_up, xf - 24, [0.42, 0.36, 0.33, 0.30], lean=18)
        keys.append(P(25.65, b, xf, f, spread=0.30, bend=14, lean=14, head=0, arms="guard"))
        for i, th in enumerate(FLURRY):
            hand = "handF" if i % 2 == 0 else "handB"
            keys.append(K(th - 0.13, "inout", face=f, lean=12, **ARMS["guard"]))
            keys.append(K(th, "snap", face=f, lean=19, **{hand: tg["flurry"][i]}))
        keys += [P(27.95, b, xf - 16, f, spread=0.30, bend=14, lean=10, arms="guard"),
                 # 打累了：弯腰喘气，抬头看他
                 P(28.7, b, xf - 28, f, spread=0.32, bend=24, lean=42, head=-36, aF=24, fF=8, aB=18, fB=4),
                 P(29.9, b, xf - 28, f, spread=0.32, bend=22, lean=38, head=-32, aF=24, fF=8, aB=18, fB=4),
                 P(30.7, b, xf - 28, f, spread=0.30, bend=12, lean=10, head=-10, arms="guard"),
                 P(A_PUSH, b, xf - 28, f, spread=0.30, bend=12, lean=8, head=-8, arms="guard")]
        return keys
    return then


def hero_after_push(tg):
    """第二次被推飞以后，一直到片尾：躺着、看见、站起来、拨、过肩摔、伸手"""
    def then(pose, t0):
        b, f = HERO, 1
        L = leg(b)
        keys = [K(t0, "linear", face=f, **pose), K(47.2, "linear", face=f, **pose)]
        up = dict(pose, head=pose["head"] + 40)
        keys += [K(48.8, "inout", face=f, head=up["head"]),         # 仰面躺着，把头抬起来看过去
                 K(50.8, "linear", face=f, head=up["head"])]
        xc = tg["calm_x"]
        keys += getup_back(b, f, 50.8, up, xc, (0.9, 1.9, 3.0), arms_end="open")[1:]
        keys += [P(54.6, b, xc, f, spread=0.27, bend=6, lean=1, head=0, arms="open"),
                 P(55.7, b, xc, f, spread=0.27, bend=1, lean=-2, head=-5, arms="open"),     # 吸一口气
                 P(56.9, b, xc, f, spread=0.28, bend=10, lean=3, head=0, arms="open"),      # 呼出来，沉下去
                 P(58.15, b, xc, f, spread=0.30, bend=14, lean=5, head=-2, arms="open")]
        px, py = tg["parry"]
        keys += [K(A_PUNCH, "inout", face=f, x=xc - 4, y=hip(b, 0.30, 20), lean=-8, head=-6,
                   handF=(px + 4, py + 24), aB=10, fB=40),
                 K(A_PARRY, "snap", face=f, x=xc - 10, y=hip(b, 0.31, 26), lean=-16, head=-10, handF=(px, py),
                   footB=(xc - 0.30 * L - 36, b.foot_y), lift=10),
                 K(58.98, "out", face=f, x=xc - 20, lean=-20, head=-14, handF=(px - 8, py - 60)),
                 P(59.5, b, xc - 24, f, spread=0.30, bend=12, lean=-4, head=-4, arms="open")]
        xw = xc - 24
        keys += [P(59.85, b, xw, -1, spread=0.28, bend=8, lean=2, head=2, arms="low"),     # 转过身，看他冲过去
                 P(63.4, b, xw, -1, spread=0.28, bend=8, lean=4, head=4, arms="low"),
                 P(66.2, b, xw, -1, spread=0.28, bend=8, lean=2, head=10, arms="low"),
                 P(72.6, b, xw, -1, spread=0.28, bend=8, lean=1, head=2, arms="open"),
                 P(74.6, b, tg["throw_x"], -1, spread=0.32, bend=14, lean=6, head=0, arms="open", lift=16),
                 P(78.25, b, tg["throw_x"], -1, spread=0.33, bend=20, lean=8, head=0, arms="open")]
        # 最后一刻：转身背对他，沉腰，双手从肩上抓住他伸过来的手腕
        xt = tg["throw_x"]
        wx, wy = tg["wrist"]
        fy = b.foot_y
        keys += [K(78.62, "in", face=f, x=xt + 4, y=hip(b, 0.30, 34), lean=22, head=-12,
                   handF=(wx + 18, wy + 10), handB=(wx + 26, wy + 20),
                   footF=(xt + 0.25 * L, fy), footB=(xt - 0.25 * L, fy)),
                 K(A_GRAB, "linear", face=f, x=xt + 4, y=hip(b, 0.30, 42), lean=30, head=-6,
                   handF=(wx, wy), handB=(wx + 8, wy + 10)),
                 # 往前下方拉：手从肩上拉到身前，上身前俯，髋部顶在他的重心下面——支点
                 K(A_GRAB + 0.25, "inout", face=f, x=xt + 2, y=hip(b, 0.30, 38), lean=46, head=0,
                   handF=(xt + 60, 600), handB=(xt + 70, 612)),
                 K(A_GRAB + 0.6, "inout", face=f, x=xt + 6, y=hip(b, 0.30, 34), lean=62, head=6,
                   handF=(xt + 140, 690), handB=(xt + 150, 700)),
                 K(A_GRAB + 0.95, "out", face=f, x=xt + 10, y=hip(b, 0.30, 32), lean=66, head=10,
                   handF=(xt + 175, 790), handB=(xt + 185, 798))]
        land, hx = tg["land"], tg["help_x"]
        keys += [P(land + 0.9, b, xt + 10, f, spread=0.30, bend=16, lean=24, head=14, arms="low"),
                 P(land + 1.9, b, xt + 10, f, spread=0.28, bend=6, lean=3, head=16, arms="relax"),
                 P(land + 8.0, b, xt + 10, f, spread=0.28, bend=6, lean=3, head=14, arms="relax")]
        keys += walk(b, f, land + 8.0, xt + 10, hx, 1, 0.6, lean=4, head=16)
        c0, c1, c2 = tg["clasp0"], tg["clasp1"], tg["clasp2"]
        keys += [K(land + 9.1, "inout", face=f, lean=22, head=22, handF=c0, aB=-12, fB=6),
                 K(land + 9.9, "linear", face=f, lean=24, head=22, handF=c0),
                 K(land + 10.45, "inout", face=f, lean=-4, y=hip(b, 0.30, 14), head=6, handF=c1),   # 身体往后一仰
                 K(land + 11.3, "out", face=f, lean=-16, y=hip(b, 0.30, 16), head=-4, handF=c2),
                 P(land + 11.9, b, hx, f, spread=0.28, bend=6, lean=0, head=-8, arms="relax"),
                 P(land + 40.0, b, hx, f, spread=0.28, bend=6, lean=0, head=-8, arms="relax")]
        return keys
    return then


def hero_breath(tg):
    def extra(t):
        if t < 50.8:                                      # 躺着喘气：先急后缓
            k = 2.2 if t < 42.0 else 1.4
            return {"lean": k * math.sin(2 * math.pi * (0.55 if t < 42.0 else 0.35) * t)}
        land = tg["land"]
        if land + 1.9 < t < land + 8.0:                    # 摔完人以后站着喘
            return {"y": 2.6 * math.sin(2 * math.pi * 0.5 * t)}
        if t > land + 12.0:
            return {"y": 1.4 * math.sin(2 * math.pi * 0.25 * t)}
        return {}
    return extra


# ============================== 青：大块头 ==============================

def big_base(tg):
    """0 → 64.0：进场、出拳、推人、扇羽毛、出拳被拨、踉跄、晃，最后重心越过前脚"""
    b, f = BIG, -1
    L = leg(b)

    def extra(t):
        hit = sum(6.0 * math.exp(-(t - th) / 0.14) for th in FLURRY if t >= th)    # 挨了四拳：几乎不动
        breath = 2.4 * math.sin(2 * math.pi * 0.28 * t) if 4.5 < t < 12.0 else 0.0
        return {"x": hit, "y": breath, "head": -0.5 * hit}

    keys = [P(-0.5, b, 1930, f, spread=0.25, bend=8, lean=5, head=6)]
    keys += walk(b, f, -0.5, 1930, 1262, 4, 1.0, first="F", heavy=True, swing=22, lean=5, head=6)
    keys += [P(4.4, b, 1262, f, spread=0.26, bend=8, lean=3, head=10),                  # 站定，低头看金
             P(8.3, b, 1262, f, spread=0.26, bend=8, lean=3, head=10),
             P(9.2, b, 1264, f, spread=0.32, bend=10, lean=10, head=6, arms="guard"),    # 摆架势
             P(12.0, b, 1264, f, spread=0.32, bend=10, lean=10, head=6, arms="guard"),
             P(12.7, b, 1280, f, spread=0.33, bend=22, lean=18, head=4, arms="guard")]   # 蓄力：重心下沉
    keys += walk(b, f, 12.7, 1280, 1000, 2, 0.9, first="F", heavy=True, swing=30, lean=18, head=2, arms="guard")
    bx, by = tg["block"]
    keys += [K(15.4, "inout", face=f, x=985, lean=20, head=2, aF=-24, fF=70, aB=22, fB=160),        # 拳头往后收
             K(A_HIT, "snap", face=f, x=958, y=hip(b, 0.34, 18), lean=22, head=0, handF=(bx, by), aB=26, fB=160,
               footF=(958 - 0.36 * L, b.foot_y), lift=16),                                            # 出拳
             K(16.25, "out", face=f, x=992, lean=10, head=-6, aF=48, fF=110),                           # 被反作用力顶回来一点
             P(16.9, b, 1000, f, spread=0.30, bend=8, lean=6, head=6, arms="guard"),
             P(17.9, b, 1000, f, spread=0.28, bend=6, lean=1, head=12, arms="low"),
             K(18.6, "inout", face=f, aF=150, fF=170),                                                   # 活动肩膀
             K(19.2, "inout", face=f, aF=-40, fF=-30),
             K(19.7, "inout", face=f, **ARMS["low"]),
             P(22.0, b, 1000, f, spread=0.28, bend=6, lean=-4, head=12, arms="low"),                    # 挺着胸，等他打
             P(28.0, b, 1000, f, spread=0.28, bend=6, lean=-4, head=14, arms="low"),
             K(28.5, "inout", face=f, head=26, aB=56, fB=150),                                           # 低头拍拍胸口
             K(28.75, "inout", face=f, aB=48, fB=136),
             K(29.0, "inout", face=f, aB=56, fB=150),
             K(29.25, "inout", face=f, aB=48, fB=136),
             K(29.7, "inout", face=f, head=10, **ARMS["low"]),
             P(30.8, b, 1004, f, spread=0.30, bend=8, lean=-6, head=8, aF=-12, fF=60, aB=-4, fB=24),   # 往后一靠
             K(A_PUSH, "snap", face=f, x=972, y=hip(b, 0.33, 10), lean=12, head=4, handF=tg["hero_chest"],
               aB=-10, fB=20, footF=(972 - 0.36 * L, b.foot_y), lift=18),                               # 一掌推出
             K(32.55, "out", face=f, aF=72, fF=82),
             P(33.8, b, 990, f, spread=0.28, bend=6, lean=2, head=10, arms="low"),
             P(41.6, b, 1000, f, spread=0.28, bend=6, lean=1, head=6, arms="low"),
             K(42.7, "inout", face=f, head=-26),                                     # 抬头：有东西飘下来
             K(43.3, "inout", face=f, head=-16, aF=40, fF=150),                      # 不耐烦，抬手
             K(43.78, "inout", face=f, handF=tg["swat0"], head=-14),                 # 手往后收
             K(44.12, "in", face=f, handF=tg["swat1"], head=-10),                    # 一巴掌扫过去
             K(44.6, "out", face=f, aF=66, fF=70, head=-4),                          # 扫空了
             K(45.5, "inout", face=f, head=12, aF=56, fF=118),                       # 低头看自己的手，愣了一下
             K(46.7, "inout", face=f, head=0, aF=30, fF=60),
             P(49.5, b, 1000, f, spread=0.28, bend=6, lean=2, head=12, arms="low"),  # 看着金爬起来
             P(54.8, b, 1000, f, spread=0.28, bend=6, lean=4, head=6, arms="low")]
    xp = tg["punch_x"]
    keys += walk(b, f, 54.8, 1000, xp + 30, 2, 0.75, first="F", heavy=True, swing=20, lean=8, head=4)
    keys += [P(56.9, b, xp + 30, f, spread=0.31, bend=12, lean=12, head=4, arms="guard"),
             K(57.85, "inout", face=f, x=xp + 40, lean=14, aF=-26, fF=64),                    # 拳头往后收
             K(A_PUNCH, "in", face=f, x=xp, lean=24, head=0, handF=tg["fist_at"],             # 拳头逼近（定格在这里）
               footF=(xp - 0.36 * L, b.foot_y), lift=14),
             K(A_PARRY, "linear", face=f, x=xp - 14, lean=26, handF=tg["fist_hit"]),          # 被拨的那一下
             K(58.98, "out", face=f, x=xp - 70, lean=32, head=-8, aF=150, fF=160)]            # 拳头被拨偏，人被冲劲带着往前
    x0 = xp - 70
    keys += [K(59.3, "linear", face=f, lift=40, x=x0 - 110, y=hip(b, 0.36, 18), lean=34, footB=(x0 - 200, b.foot_y),
               aF=130, fF=100, aB=-30, fB=10),
             K(59.62, "linear", face=f, lift=34, x=x0 - 210, y=hip(b, 0.36, 16), lean=30, footF=(x0 - 290, b.foot_y),
               aF=60, fF=40, aB=100, fB=150),
             K(59.98, "linear", face=f, lift=26, x=x0 - 285, y=hip(b, 0.34, 14), lean=26, footB=(x0 - 350, b.foot_y),
               aF=120, fF=160, aB=20, fB=60),
             K(60.4, "out", face=f, lift=20, x=x0 - 330, y=hip(b, 0.34, 12), lean=22, footF=(x0 - 420, b.foot_y),
               aF=40, fF=90, aB=140, fB=190)]
    # 晃：两脚撑着，重心在前脚上前后晃，两臂乱划；最后一下越过前脚
    xt = x0 - 330
    for tt, ln, aF, aB in ((60.9, 18, 160, 20), (61.45, 30, 30, 170), (61.95, 20, 170, 40),
                           (62.5, 33, 20, 160), (63.0, 24, 175, 30), (63.6, 36, 40, 175)):
        keys.append(K(tt, "inout", face=f, lean=ln, x=xt - (ln - 18) * tg["teeter_k"], aF=aF, fF=aF + 30,
                      aB=aB, fB=aB + 30))
    keys.append(K(A_TOPPLE, "in", face=f, lean=46, x=xt - 40, aF=150, fF=170, aB=140, fB=160))
    return Track(keys, face=f, body=b, extra=extra)


def kick_topple(i):
    """重心越过前脚以后：上身再往前送一点（约 0.5 m/s），剩下的交给重力"""
    return (-110 if i in (1, 2, 3, 4, 5, 6) else -40), 0.0


def big_after_fall(tg):
    """趴在地上 → 撑起来 → 转身 → 气得发抖 → 往后退 → 像斗牛一样刨地 → 全速冲过来"""
    def then(pose, t0):
        b = BIG
        L = leg(b)
        x_up = pose["x"] - 30
        keys = getup_front(b, -1, t0, pose, x_up, (0.7, 1.4, 2.2))
        t = t0 + 2.2
        keys += [P(t + 0.4, b, x_up, 1, spread=0.30, bend=10, lean=8, head=6, arms="guard"),     # 转身
                 P(t + 2.2, b, x_up, 1, spread=0.30, bend=12, lean=10, head=4, arms="guard")]
        xb = tg["charge_x0"]
        keys += walk(b, 1, t + 2.4, x_up, xb, 4, 0.5, first="B", heavy=True, swing=10, lean=10, head=4, arms="guard")
        t2 = t + 4.4
        keys += [P(t2 + 0.4, b, xb, 1, spread=0.34, bend=30, lean=32, head=22, aF=-30, fF=20, aB=-40, fB=10),
                 K(t2 + 0.8, "inout", face=1, footB=(xb - 0.34 * L - 60, b.foot_y), lift=10),     # 后脚刨地
                 K(t2 + 1.1, "inout", face=1, footB=(xb - 0.34 * L, b.foot_y), lift=10),
                 K(t2 + 1.5, "inout", face=1, footB=(xb - 0.34 * L - 60, b.foot_y), lift=10),
                 K(t2 + 1.8, "inout", face=1, footB=(xb - 0.34 * L, b.foot_y), lift=10)]
        durs = [0.42, 0.36, 0.32, 0.29, 0.27, 0.25, 0.24]
        keys += run(b, 1, A_GRAB - sum(durs), xb, tg["grab_x"] - 20, durs, lean=24, head=6)
        keys.append(K(A_GRAB, "linear", face=1, x=tg["grab_x"], lean=22, head=0, handF=tg["reach"], aB=-40, fB=20))
        return keys
    return then


def kick_throw(i):
    """髋部顶在他重心下面：腿被往上掀，上身被手臂拽着往下——整个人绕着支点翻过去"""
    return {0: (0, -380), 1: (0, 120), 2: (0, 200), 3: (0, 0), 4: (0, 0), 5: (0, 60), 6: (0, 60),
            7: (0, -650), 9: (0, -650), 8: (0, -760), 10: (0, -760)}[i]


def big_after_throw(tg):
    """仰面躺着（发愣）→ 翻过身来跪着 → 握住金伸过来的手 → 被拉起来 → 面对面，点头"""
    def then(pose, t0):
        from vlab.stick.rig import fk, pose_from_joints
        b = BIG
        L = leg(b)
        J = fk(pose, 1, b)
        mirror = pose_from_joints(J, -1)            # 翻身：同样的关节位置，朝向换成左边
        land = tg["land"]
        xk = tg["kneel_x"]
        c0, c1, c2 = tg["clasp0"], tg["clasp1"], tg["clasp2"]
        fy = b.foot_y
        keys = [K(t0, "linear", face=1, **pose), K(t0 + 0.02, "linear", face=-1, **mirror),
                K(t0 + 0.7, "out", face=-1, x=xk + 0.2 * L, y=GROUND - 0.3 * L, lean=72, head=-24,
                  handF=(xk - 0.75 * b.torso, fy), handB=(xk - 0.65 * b.torso, fy),
                  footF=(xk + 0.75 * L, fy), footB=(xk + 0.85 * L, fy)),                     # 撑起来
                K(t0 + 1.35, "inout", face=-1, x=xk, y=fy - b.thigh - 4, lean=6, head=-18, aF=20, fF=30, aB=10, fB=24,
                  footF=(xk - 0.42 * L, fy), footB=(xk + 0.9 * b.shin, fy)),                  # 单膝跪着，抬头看
                K(land + 9.45, "inout", face=-1, head=-14, handF=(c0[0] + 10, c0[1] + 30)),     # 愣了一下，伸手
                K(land + 9.9, "linear", face=-1, head=-12, handF=c0),                         # 握住
                K(land + 10.45, "inout", face=-1, x=xk - 18, y=hip(b, 0.30, 46), lean=16, head=-8, handF=c1,
                  footF=(xk - 0.36 * L, fy), footB=(xk + 0.3 * L, fy)),                      # 被拉起来
                K(land + 11.3, "out", face=-1, x=xk - 26, y=hip(b, 0.28, 8), lean=4, head=-4, handF=c2),
                P(land + 11.9, b, xk - 26, -1, spread=0.27, bend=6, lean=2, head=6, arms="relax"),
                K(land + 12.35, "inout", face=-1, head=22),                                   # 点头
                K(land + 12.9, "inout", face=-1, head=6),
                P(land + 40.0, b, xk - 26, -1, spread=0.27, bend=6, lean=2, head=6, arms="relax")]
        return keys
    return then


# ============================== 羽毛：跟着气流走 ==============================

PALM = 30.0       # 手掌当成一个半径 30 px 的圆柱（约 16 cm），算它推开的绕流


def air_around_hand(x, y, hx, hy, hvx, hvy):
    """手掌以速度 (hvx, hvy) 扫过静止空气时，(x, y) 处的空气速度：圆柱绕流的偶极子解（示意，不做黏性）"""
    U = math.hypot(hvx, hvy)
    if U < 5:
        return 0.0, 0.0
    ex, ey = hvx / U, hvy / U
    rx, ry = x - hx, y - hy
    r = max(math.hypot(rx, ry), PALM)
    c = (rx * ex + ry * ey) / r
    s = (-rx * ey + ry * ex) / r
    k = U * PALM * PALM / (r * r)
    ur, ut = k * c, k * s
    vxp, vyp = ur * c - ut * s, ur * s + ut * c
    return vxp * ex - vyp * ey, vxp * ey + vyp * ex


def feather_sim(big_track, t0, t1, x0, y0):
    """动作时间 t0 → t1 的羽毛轨迹：dv/dt = (空气速度 - v)/τ + g'，静止空气里匀速下落 82 px/s（0.43 m/s）"""
    dt = 1.0 / 240
    tau = 0.05
    g_eff = 82.0 / tau
    x, y, vx, vy = x0, y0, 0.0, 82.0
    out = []
    t = t0
    prev = big_track.joints(t - dt)[0][4]
    while t <= t1:
        hand = big_track.joints(t)[0][4]
        hvx, hvy = (hand[0] - prev[0]) / dt, (hand[1] - prev[1]) / dt
        prev = hand
        ux = 14.0 * math.sin(1.3 * t) + 6.0
        uy = 0.0
        ax_, ay_ = air_around_hand(x, y, hand[0], hand[1], hvx, hvy)
        ux, uy = ux + ax_, uy + ay_
        vx += ((ux - vx) / tau) * dt
        vy += ((uy - vy) / tau + g_eff) * dt
        x += vx * dt
        y += vy * dt
        if y > GROUND - 4:                     # 落地就停住
            y, vx, vy = GROUND - 4, 0.0, 0.0
        rot = math.degrees(math.atan2(vy, vx)) * 0.25 + 16 * math.sin(4.2 * t) if y < GROUND - 4 else 4.0
        out.append((t, x, y, rot))
        t += dt
    return out


def streamlines(dirn, n_side=(0.5, 1.25, 2.2, 3.4)):
    """手掌坐标系里的流线（圆柱绕流 ψ = y'(1 - a²/r²) = c），转到世界方向 dirn"""
    ex, ey = dirn
    lines = []
    for sgn in (1, -1):
        for c in n_side:
            pts = []
            for i in range(41):
                xp = -4.2 * PALM + 8.4 * PALM * i / 40
                yp = sgn * c * PALM
                for _ in range(30):                     # 解 y'(1 - a²/(x'²+y'²)) = c
                    r2 = xp * xp + yp * yp
                    fval = yp * (1 - PALM * PALM / r2) - sgn * c * PALM
                    d = (1 - PALM * PALM / r2) + yp * (2 * PALM * PALM * yp / (r2 * r2))
                    yp -= fval / d
                pts.append((xp * ex - yp * ey, xp * ey + yp * ex))
            lines.append(pts)
    return lines


# ============================== 组装 ==============================

REPLAY = (52.0, 57.0, 43.45, 0.24)     # S12：真实 52–57 秒，大块头和羽毛倒回动作 43.45 秒、0.24 倍速重放


def replay_clock(t):
    r0, r1, a0, k = REPLAY
    return a0 + (t - r0) * k if r0 <= t < r1 else None


def first_impact(ep, after, min_speed=420):
    hits = [e for e in sorted(ep.events) if e[0] >= after and e[2] >= min_speed]
    return hits[0][0] if hits else None


def make(tg):
    """按落点表 tg 搭两个人（含布偶段落），算好物理"""
    hero = Figure("gold", hero_base(), GOLD, mass=M_HERO)
    hero.ragdoll(A_HIT, kick=kick_hit, until=21.0, then=hero_after_hit(tg))
    hero.ragdoll(A_PUSH, kick=kick_push, until=34.6, then=hero_after_push(tg), extra=hero_breath(tg))
    big = Figure("cyan", big_base(tg), CYAN, core="#e9fffb", mass=M_BIG)
    big.ragdoll(A_TOPPLE, kick=kick_topple, until=tg["fall"] + 2.1, then=big_after_fall(tg), friction=0.1)

    def pivot(ta):
        J = hero.joints(ta)
        p, n = J[0], J[1]
        return p[0] + (n[0] - p[0]) * 0.22 - 14, p[1] + (n[1] - p[1]) * 0.22 - 6   # 腰后侧：支点

    big.ragdoll(A_GRAB, kick=kick_throw, until=tg["land"] + 8.15, then=big_after_throw(tg), friction=0.12,
                bounce=0.16,
                pins=[{"i": 4, "t0": A_GRAB, "t1": A_GRAB + 0.55, "k": 0.5, "target": lambda ta: hero.joints(ta)[4]}],
                obstacles=[{"t0": A_GRAB, "t1": A_GRAB + 0.5, "r": 34, "only": [0, 1, 7, 9], "center": pivot}])
    hero.prepare(FPS, A_END)
    big.prepare(FPS, A_END)
    return hero, big, pivot


def measure(hero, big, tg):
    """从算好的两个人身上量出下一轮的落点"""
    t = dict(tg)
    J = hero.joints(A_HIT)
    t["block"] = (mid(J[3], J[4])[0] + 8, mid(J[3], J[4])[1])
    Jb = big.joints(FLURRY[0])
    t["flurry_x"] = chest(Jb, 0.6)[0] - 135
    t["flurry"] = [(chest(big.joints(th), 0.6)[0] - 8, chest(big.joints(th), 0.6)[1]) for th in FLURRY]
    Jh = hero.joints(A_PUSH)
    t["hero_chest"] = (chest(Jh, 0.62)[0] + 8, chest(Jh, 0.62)[1])
    Jb = big.joints(43.6)
    nx, ny = Jb[1]
    t["swat0"], t["swat1"] = (nx + 55, ny - 20), (nx - 140, ny + 16)
    t["calm_x"] = hero.joints(40.0)[0][0] + 40
    hx, hy = hero.joints(A_PUNCH)[2]
    t["fist_at"] = (hx + HERO.head_r + 24, hy + 4)
    t["fist_hit"] = (hx + HERO.head_r - 6, hy - 2)
    t["punch_x"] = t["fist_at"][0] + 186
    Jb = big.joints(A_PARRY)
    t["parry"] = (mid(Jb[3], Jb[4], 0.55)[0], mid(Jb[3], Jb[4], 0.55)[1] + 10)
    ep_fall, ep_throw = big.episodes
    fall = first_impact(ep_fall, A_TOPPLE + 0.3)
    if fall:
        t["fall"] = fall
    x_up = big.joints(t["fall"] + 2.1)[0][0] - 30
    t["charge_x0"] = x_up - 480
    t["throw_x"] = 640.0
    t["grab_x"] = t["throw_x"] - 150
    Jg = big.joints(A_GRAB - 0.2)
    t["reach"] = (t["grab_x"] + 150, Jg[1][1] + 26)
    t["wrist"] = big.joints(A_GRAB)[4]
    land = first_impact(ep_throw, A_GRAB + 0.3, 500)
    if land:
        t["land"] = land
    Jl = big.joints(t["land"] + 7.0)
    head_x = Jl[2][0]
    t["kneel_x"] = head_x + 70
    t["help_x"] = t["kneel_x"] - 215
    m = (t["help_x"] + t["kneel_x"]) / 2
    t["clasp0"], t["clasp1"], t["clasp2"] = (m + 6, 700), (m - 4, 650), (m - 14, 628)
    return t


TG0 = {"block": (800, 580), "flurry_x": 830, "flurry": [(980, 600)] * 4, "hero_chest": (860, 620),
       "swat0": (1020, 520), "swat1": (830, 556), "calm_x": 560, "fist_at": (620, 560), "fist_hit": (590, 554),
       "punch_x": 806, "parry": (680, 570), "fall": A_FALL, "teeter_k": 1.6, "charge_x0": -300, "throw_x": 640.0,
       "grab_x": 490, "reach": (640, 560), "wrist": (640, 560), "land": A_GRAB + 0.95, "kneel_x": 800,
       "help_x": 585, "clasp0": (700, 700), "clasp1": (690, 650), "clasp2": (680, 628)}


def build():
    tg = dict(TG0)
    for _ in range(3):
        hero, big, pivot = make(tg)
        tg = measure(hero, big, tg)
    hero, big, pivot = make(tg)
    tg_check = measure(hero, big, tg)
    drift = {k: tg_check[k] for k in ("fall", "land") if abs(tg_check[k] - tg[k]) > 1e-6}

    sc = Scene(TOTAL, FPS)
    sc.timemap(timemap(tg["fall"], tg["land"]))
    sc.add(hero)
    sc.add(big)
    big.clock = replay_clock

    # —— 羽毛：先算不受手影响时的漂移，反推起点，让它在手扫得最快的那一刻正好在路径上（偏一点点） ——
    target_t = 44.06
    hand_target = big.track.joints(target_t)[0][4]
    x0, y0 = hand_target[0] + 30, 170.0
    for _ in range(3):
        path = feather_sim(big.track, 40.4, target_t, x0, y0)
        _, fx, fy, _ = path[-1]
        x0 += hand_target[0] - 6 - fx
        y0 += hand_target[1] + 14 - fy
    path = feather_sim(big.track, 40.4, 54.0, x0, y0)

    def feather_at(t_real):
        ta = replay_clock(t_real)
        ta = sc.anim(t_real) if ta is None else ta
        if ta < path[0][0]:
            return None
        i = min(len(path) - 1, int((ta - path[0][0]) * 240))
        _, x, y, r = path[i]
        return (x, y, r)
    sc.feather(feather_at, "#f6efd8", size=30)

    overlays(sc, hero, big, tg, pivot)
    effects(sc, hero, big, tg)
    camera(sc, hero, big, tg, pivot)
    info = {"砸地": round(tg["fall"], 3), "摔地": round(tg["land"], 3), "抓住": A_GRAB, "没收敛": drift,
            "羽毛起点": (round(x0), round(y0))}
    return sc, info


def overlays(sc, hero, big, tg, pivot):
    """物理标注和屏上字（真实时间）。所有文字以 SCRIPT.md 为准，一个字都不能自己改"""
    a = sc.anim
    # S02：质量
    hx, bx = hero.joints(6.0)[0][0], big.joints(6.0)[0][0]
    sc.label(4.8, 12.3, hx, GROUND + 60, "60 kg", size=34, color=GOLD)
    sc.label(4.8, 12.3, bx, GROUND + 60, "120 kg", size=34, color=CYAN)
    # S05：撞上的一瞬，两支一样长、方向相反的力
    cx, cy = tg["block"]
    sc.arrow(17.0, 22.0, (cx - 4, cy - 16, -170, 0), GOLD, width=7, grow=12)
    sc.arrow(17.0, 22.0, (cx + 4, cy + 16, 170, 0), CYAN, width=7, grow=12)
    sc.label(18.0, 22.0, cx, cy - 96, "两边受的力一样大", size=44, color=WHITE)
    # S12：手掌推开的气流（示意）
    s0, s1 = tg["swat0"], tg["swat1"]
    dx, dy = s1[0] - s0[0], s1[1] - s0[1]
    dn = math.hypot(dx, dy)
    lines = streamlines((dx / dn, dy / dn))

    def hand_r(t):
        ta = replay_clock(t)
        return big.joints(ta if ta is not None else a(t))[4]
    sc.flow(52.5, 56.9, hand_r, lines, WHITE)
    sx, sy = mid(s0, s1, 0.6)
    sc.label(53.0, 56.9, sx + 150, sy - 120, "示意", size=26, color="#9fb0c8")
    # S14–S15：拳头的动量；挡住要抵消全部，拨偏 10° 只要约六分之一
    def fist_dir(ta):
        J1, J0 = big.joints(ta), big.joints(ta - 1.0 / 60)
        vx, vy = (J1[4][0] - J0[4][0]) * 60, (J1[4][1] - J0[4][1]) * 60
        return J1[4], vx, vy
    (fx0, fy0), _, _ = fist_dir(A_PUNCH)
    p_len = 190.0

    def momentum(t):
        (fx, fy), vx, vy = fist_dir(min(a(t), A_PUNCH))
        sp = math.hypot(vx, vy) or 1.0
        k = min(1.0, sp / 700.0)
        L = p_len * (0.35 + 0.65 * k) if t < 67.0 else p_len
        ux, uy = (vx / sp, vy / sp) if t < 67.0 else (-1.0, 0.0)
        return (fx - ux * L, fy - uy * L, ux * L, uy * L)
    sc.arrow(64.0, 72.0, momentum, CYAN, width=7, grow=10)
    sc.arrow(67.5, 72.0, (fx0 - p_len - 12, fy0 - 6, p_len, 0), WHITE, width=7, grow=14)       # 挡：等长、反向
    sc.label(67.9, 72.0, fx0 - p_len / 2 - 12, fy0 - 52, "挡住它，要这么多", size=36, color=WHITE)
    short = p_len * 2 * math.sin(math.radians(5))                                              # ≈ 0.17
    sc.arrow(69.3, 72.0, (fx0 + 2, fy0 + short + 18, 0, -short), GOLD, width=7, grow=10)        # 拨：垂直、很短
    sc.label(69.6, 72.0, fx0 + 10, fy0 + short + 70, "拨开它，只要这么点", size=36, color=GOLD)
    sc.label(69.0, 72.0, fx0 + 230, fy0 + short + 70, "示意", size=24, color="#9fb0c8")
    ang = math.radians(10)
    sc.layers["paths"].append({"color": GOLD, "f0": round(69.9 * FPS), "f1": round(70.5 * FPS), "opacity": 0.75,
                               "pts": [[round(fx0 - 300 * i / 20 * math.cos(ang), 1),
                                        round(fy0 - 300 * i / 20 * math.sin(ang), 1)] for i in range(21)]})
    # S17：重心和两脚之间的支撑面
    def com_at(t):
        return com(big.joints(a(t)))

    def base_at(t):
        J = big.joints(a(t))
        return (min(J[8][0], J[10][0]), max(J[8][0], J[10][0]))
    t_cross = None
    for i in range(round(77.0 * FPS), round(80.5 * FPS)):
        t = i / FPS
        if com_at(t)[0] < base_at(t)[0] - 1:
            t_cross = t
            break
    sc.dot(77.2, 80.3, com_at, WHITE, r=10)
    sc.bar(77.2, 80.3, base_at, WHITE, alt=RED, t_alt=t_cross or 78.4)
    c77 = com_at(77.6)
    sc.label(77.6, 80.3, c77[0] + 70, c77[1] - 40, "重心", size=34, color=WHITE)
    sc.label(78.0, 82.3, 960, 1000, "重心出了两脚之间，就会倒", size=42, color=WHITE, screen=True)
    sc.t_cross = t_cross
    # S19：冲过来的动量越来越大
    def charge_p(t):
        ta = a(t)
        J1, J0 = big.joints(ta), big.joints(ta - 1.0 / 30)
        vx = (J1[0][0] - J0[0][0]) * 30
        c = chest(J1, 0.6)
        return (c[0], c[1], max(0.0, vx) * 0.2, 0.0)
    sc.arrow(90.8, 93.6, charge_p, CYAN, width=7, grow=6)
    # S20：支点，和绕着它弯过去的动量
    pv = pivot(A_GRAB)
    sc.tri(94.0, 99.6, (pv[0], pv[1] + 6), GOLD, size=26)
    sc.label(94.6, 99.4, pv[0] - 90, pv[1] + 86, "支点", size=36, color=GOLD)
    sc.layers["arcs"].append({"f0": round(94.6 * FPS), "f1": round(99.4 * FPS), "x": pv[0], "y": pv[1],
                              "r": 150, "a0": 205, "a1": 335, "color": CYAN, "head": True, "width": 6,
                              "grow": 40})
    # S24：落点
    sc.label(112.6, 121.0, 960, 300, "力气比不过的时候，你可以借力。", size=64, color=WHITE, screen=True)


def effects(sc, hero, big, tg):
    """粒子、震屏、音效。动作事件写动作时间（会跟着定格、慢放走），剪辑上的声音写真实时间"""
    dust = "#c9cfdb"
    # S01：四步重脚步，每一步地上亮一下、起尘、镜头一震
    for i, t in enumerate(STOMPS):
        J = big.joints(t + 0.02)
        foot = J[8] if i % 2 == 0 else J[10]
        sc.burst(t, foot[0], GROUND, "dust", n=10, speed=200, angle=-90, spread=170, life=22, size=10, color=dust)
        sc.burst(t, foot[0], GROUND - 2, "flare", size=46, life=10, color=CYAN)
        sc.sfx(t, "stomp", 0.95)
        sc.shake(t, 5, 0.3, anim=True)
    sc.sfx(2.9, "step", 0.25)
    # S04：冲两步、出拳、撞上
    for t in (13.6, 14.5):
        sc.sfx(t, "stomp", 0.8)
        J = big.joints(t + 0.02)
        sc.burst(t, J[8][0], GROUND, "dust", n=8, speed=170, angle=-90, spread=160, life=20, size=9, color=dust)
    sc.sfx(15.62, "whoosh", 0.55, dur=0.38, f0=260, f1=1500)
    bx, by = tg["block"]
    sc.burst(A_HIT, bx, by, "spark", n=26, speed=950, angle=180, spread=160, life=16, size=4.5, color=GOLD)
    sc.burst(A_HIT, bx, by, "spark", n=16, speed=820, angle=0, spread=140, life=14, size=3.6, color=CYAN, seed=4242)
    sc.burst(A_HIT, bx, by, "ring", size=12, speed=170, life=14, color="#fff2cf")
    sc.burst(A_HIT, bx, by, "flare", size=70, life=8, color=GOLD)
    sc.sfx(A_HIT, "block", 1.0)
    sc.sfx(A_HIT, "punch", 0.8)
    sc.sfx(A_HIT, "impact", 0.45)
    sc.shake(A_HIT, 12, 0.35, anim=True)
    sc.sfx(16.15, "hum", 0.42, real=True, dur=5.9, f=98.0)
    # S06/S09：被打飞落地；S07 跑回去；S08 连打四拳；S09 一掌推飞
    ep1, ep2 = hero.episodes
    for t, x, v in sc.impacts(hero, ep1, min_speed=450, gain=0.9):
        pass
    land1 = first_impact(ep1, A_HIT + 0.2) or (A_HIT + 0.7)
    sc.sfx(land1 + 0.05, "scrape", 0.5, dur=0.7)
    for t in (24.32, 24.68, 25.01, 25.31):
        sc.sfx(t, "step", 0.4)
    for i, th in enumerate(FLURRY):
        px, py = tg["flurry"][i]
        sc.burst(th, px, py, "spark", n=9, speed=520, angle=180 if i % 2 else 200, spread=120, life=10, size=3,
                 color=GOLD, seed=900 + i)
        sc.burst(th, px, py, "flare", size=24, life=5, color=GOLD)
        sc.sfx(th, "punch", 0.42)
    for t in (28.5, 28.75, 29.0, 29.25):
        sc.sfx(t, "slap", 0.22)
    sc.sfx(31.7, "whoosh", 0.5, dur=0.32, f0=300, f1=1700)
    cx, cy = tg["hero_chest"]
    sc.burst(A_PUSH, cx, cy, "ring", size=14, speed=190, life=14, color=CYAN)
    sc.burst(A_PUSH, cx, cy, "flare", size=60, life=7, color=CYAN)
    sc.burst(A_PUSH, cx, cy, "spark", n=14, speed=700, angle=180, spread=120, life=12, size=3.6, color=CYAN)
    sc.sfx(A_PUSH, "punch", 0.95)
    sc.sfx(A_PUSH, "impact", 0.4)
    sc.shake(A_PUSH, 10, 0.3, anim=True)
    sc.impacts(hero, ep2, min_speed=450, gain=0.95)
    land2 = first_impact(ep2, A_PUSH + 0.2) or (A_PUSH + 0.7)
    sc.sfx(land2 + 0.05, "scrape", 0.55, dur=0.8)
    # S10：音乐停，只剩喘息；S11 羽毛、扇空；S12 慢镜头的风
    for t in (42.8, 44.3, 45.9):
        sc.sfx(t, "pulse", 0.32, real=True)
    sc.sfx(47.2, "wind", 0.22, real=True, dur=3.0, f0=600, f1=900)
    sc.sfx(43.9, "whoosh", 0.7, dur=0.32, f0=420, f1=2200)
    sc.sfx(52.2, "wind", 0.45, real=True, dur=4.6, f0=180, f1=420)
    sc.sfx(52.9, "whoosh", 0.4, real=True, dur=2.6, f0=90, f1=420)
    # S13：站起来；S14 走过来、慢下来的拳风；S15 定格；S16 一拨
    for t in (55.55, 56.3):
        sc.sfx(t, "stomp", 0.55)
    sc.sfx(64.0, "whoosh", 0.5, real=True, dur=2.8, f0=80, f1=380)
    sc.sfx(67.1, "hum", 0.38, real=True, dur=4.9, f=82.0)
    px, py = tg["parry"]
    sc.burst(A_PARRY, px, py, "spark", n=10, speed=480, angle=-90, spread=90, life=10, size=3, color=GOLD)
    sc.burst(A_PARRY, px, py, "ring", size=8, speed=80, life=10, color=GOLD)
    sc.sfx(A_PARRY, "slap", 0.85)
    sc.sfx(A_PARRY + 0.04, "whoosh", 0.55, dur=0.3, f0=500, f1=2400)
    for t in (59.3, 59.62, 59.98, 60.4):
        sc.sfx(t, "stomp", 0.45)
        J = big.joints(t + 0.02)
        sc.burst(t, min(J[8][0], J[10][0]), GROUND, "dust", n=6, speed=150, angle=-90, spread=150, life=16, size=8,
                 color=dust)
    for t in (60.9, 61.95, 63.0):
        sc.sfx(t, "whoosh", 0.18, dur=0.4, f0=200, f1=700)
    # S17：倒地（真实 80.0）
    ep_fall, ep_throw = big.episodes
    sc.impacts(big, ep_fall, min_speed=450, sfx_kind="thud", gain=1.0)
    sc.sfx(tg["fall"], "impact", 0.5)
    # S18：爬起来、气得发抖
    sc.sfx(tg["fall"] + 4.8, "rumble", 0.6, dur=2.0)
    # S19：往后退、刨地、冲锋（越来越快的重脚步）
    t_back = tg["fall"] + 2.1 + 2.2 + 2.4
    for k in range(4):
        sc.sfx(t_back + 0.5 * (k + 1), "stomp", 0.4)
    t2 = tg["fall"] + 2.1 + 2.2 + 4.4
    for t in (t2 + 0.8, t2 + 1.5):
        J = big.joints(t)
        sc.sfx(t, "scrape", 0.4, dur=0.3)
        sc.burst(t, J[10][0], GROUND, "dust", n=8, speed=180, angle=-160, spread=50, life=18, size=9, color=dust)
    durs = [0.42, 0.36, 0.32, 0.29, 0.27, 0.25, 0.24]
    t = A_GRAB - sum(durs)
    for k, du in enumerate(durs):
        t += du
        sc.sfx(t, "stomp", 0.55 + 0.06 * k)
        sc.shake(t, 2 + k, 0.2, anim=True)
        J = big.joints(t)
        sc.burst(t, min(J[8][0], J[10][0]), GROUND, "dust", n=8, speed=200, angle=-150, spread=70, life=20,
                 size=9, color=dust)
    sc.sfx(90.6, "riser", 0.35, real=True, dur=2.9)
    # S20–S21：抓住、慢下来的风声、落地前一拍静音、一声巨响
    wx, wy = tg["wrist"]
    sc.burst(A_GRAB, wx, wy, "flare", size=34, life=8, color=GOLD)
    sc.sfx(A_GRAB, "slap", 0.95)
    sc.sfx(93.6, "hum", 0.32, real=True, dur=4.3, f=66.0)
    sc.sfx(94.4, "whoosh", 0.5, real=True, dur=3.6, f0=70, f1=420)
    sc.sfx(98.0, "whoosh", 0.55, real=True, dur=1.5, f0=120, f1=900)
    land = tg["land"]
    J = big.joints(land + 0.05)
    lx = (J[0][0] + J[1][0]) / 2
    sc.burst(land, lx, GROUND, "dust", n=34, speed=520, angle=-90, spread=176, life=40, size=18, g=-50, color=dust)
    sc.burst(land, lx, GROUND - 4, "ring", size=20, speed=420, life=22, color=CYAN)
    sc.burst(land, lx, GROUND - 10, "flare", size=110, life=10, color=CYAN)
    sc.sfx(land, "crash", 1.0)
    sc.shake(land, 20, 0.6, anim=True)
    for t, x, v in sc.impacts(big, ep_throw, min_speed=650, sfx_kind="thud", dust=True, shake=False, gain=0.5):
        pass
    sc.sfx(101.2, "wind", 0.2, real=True, dur=3.0, f0=300, f1=500)
    for t in (103.6, 105.4):
        sc.sfx(t, "pulse", 0.25, real=True)
    # S23：走过去、握手、拉起来
    sc.sfx(land + 8.6, "step", 0.35)
    sc.sfx(land + 9.9, "slap", 0.6)
    sc.sfx(land + 10.3, "whoosh", 0.3, dur=0.6, f0=200, f1=700)
    sc.sfx(land + 11.3, "step", 0.4)


def camera(sc, hero, big, tg, pivot):
    """每一镜一个取景意图（跟着人走、推近、拉远），镜内平滑、镜间硬切"""
    n = round(TOTAL * FPS)
    H, B = [], []
    for f in range(n):
        t = f / FPS
        ta = sc.anim(t)
        own = big.clock(t) if big.clock else None
        H.append(hero.joints(ta))
        B.append(big.joints(ta if own is None else own))
    sw = mid(tg["swat0"], tg["swat1"], 0.6)
    fist = tg["fist_at"]
    pv = pivot(A_GRAB)
    cuts = [0.0, 4.0, 8.0, 12.0, 16.0, 22.0, 27.0, 32.0, 37.0, 42.0, 47.0, 52.0, 55.6, 57.0, 62.0, 67.0, 72.0,
            77.0, 82.0, 87.0, 93.0, 98.0, 103.0, 108.0, 112.0, 120.0]

    def want(f):
        t = f / FPS
        hx, bx = H[f][0][0], B[f][0][0]
        mx = (hx + bx) / 2
        gap = abs(bx - hx)
        fit = max(0.95, min(1.45, 1300.0 / (gap + 650.0)))
        if t < 4.0:
            u = t / 4.0
            return 1120 + 60 * u, 612, 1.0 + 0.05 * u
        if t < 8.0:
            return mx, 615, 1.14 + 0.04 * (t - 4.0) / 4.0
        if t < 12.0:
            return mx, 612, 1.2 + 0.1 * (t - 8.0) / 4.0
        if t < 16.0:
            return mx, 600, 1.3 + 0.12 * (t - 12.0) / 4.0
        if t < 22.0:
            u = ease((t - 16.0) / 6.0)
            cx, cy = tg["block"]
            return mx + (cx - mx) * u, 600 + (cy - 600) * u, 1.42 + 0.48 * u
        if t < 27.0:
            return mx, 625, fit
        if t < 32.0:
            return mx, 618, max(1.15, fit)
        if t < 37.0:
            return mx, 600, 1.45
        if t < 42.0:
            return mx, 622, fit
        if t < 47.0:
            u = (t - 42.0) / 5.0
            return hx + 60, 760, 1.55 + 0.12 * u
        if t < 52.0:
            return bx - 70, 520, 1.42
        if t < 55.6:
            return sw[0], sw[1] + 10, 2.1 + 0.15 * (t - 52.0) / 3.6
        if t < 57.0:
            return hx + 40, 770, 1.8
        if t < 62.0:
            return mx, 622, 1.28
        if t < 67.0:
            u = ease((t - 62.0) / 5.0)
            return mx + (fist[0] - mx) * u * 0.5, 600 - 20 * u, 1.28 + 0.32 * u
        if t < 72.0:
            return fist[0] - 40, fist[1] + 30, 1.85
        if t < 77.0:
            return mx, 615, fit
        if t < 82.0:
            return bx - 50, 640, 1.32
        if t < 87.0:
            return mx, 622, fit
        if t < 93.0:
            u = ease((t - 90.6) / 2.9)
            return mx, 615, fit + 0.25 * u
        if t < 98.0:
            u = (t - 93.0) / 5.0
            return pv[0] - 10, pv[1] - 70, 1.62 + 0.12 * u
        if t < 103.0:
            if t < 100.0:
                c = chest(B[f])
                return (c[0] + pv[0]) / 2, (c[1] + pv[1]) / 2 - 40, 1.45
            return mx, 640, 1.08
        if t < 108.0:
            return mx, 640, 1.12 + 0.06 * (t - 103.0) / 5.0
        if t < 112.0:
            return mx, 632, 1.32
        u = (t - 112.0) / 8.0
        return mx, 560, 0.98 - 0.05 * u

    raw = [want(f) for f in range(n)]
    cam = []
    seg = [round(c * FPS) for c in cuts]
    for f in range(n):
        lo = max(s for s in seg if s <= f)
        hi = min(s for s in seg if s > f) if f < seg[-1] else n
        k0, k1 = max(lo, f - 9), min(hi - 1, f + 9)
        vals = raw[k0:k1 + 1]
        cam.append(tuple(sum(v[i] for v in vals) / len(vals) for i in range(3)))
    sc.camera_fn = lambda t: cam[min(n - 1, max(0, round(t * FPS)))]
