"""样片 B · 两个火柴人对打：四个回合，测打击感（顿帧、火花、震屏、音效）和布偶物理。

    1. 青冲上来一记直拳，金后仰躲过（拳头打在金刚才头所在的位置）；
    2. 金压低身子上步，一拳打在青的肚子上——顿帧 + 火花，青被打得后仰退步；
    3. 青跳起侧踢，金双臂格挡，被踢得在地上滑出去一截；
    4. 金冲刺上勾拳，青被打飞——从这一帧起青交给物理算（Verlet 布偶，g = 9.8 m/s²），落地、弹、滑，躺下。

出拳、出腿的落点都是按对方那一刻的关节位置算出来的（IK 去够），所以拳头正好打在肚子、下巴和小臂上。
"""
import math

from vlab.stick.rig import FOOT_Y, STAND_Y, K, Track
from vlab.stick.scene import Figure, Scene

FPS = 30
GOLD, CYAN = "#f3c14b", "#49e3d1"
GUARD_Y = FOOT_Y - 146          # 拳击架势：膝盖微屈，重心低一点
T_PUNCH, T_COUNTER, T_KICK, T_UPPER = 1.30, 1.56, 2.48, 3.70
END = 6.5


def window(t, a, b, ramp=0.18):
    """[a, b] 区间里为 1、两头平滑过渡的包络（只在对峙的时候颠拳击步）"""
    return max(0.0, min(1.0, (t - a) / ramp, (b - t) / ramp))


def guard(t, x, face, ease="inout", dy=0.0, front=52, back=56, **kw):
    ch = dict(x=x, y=GUARD_Y + dy, lean=10, head=4, aF=35, fF=155, aB=18, fB=165,
              footF=(x + face * front, FOOT_Y), footB=(x - face * back, FOOT_Y))
    ch.update(kw)
    return K(t, ease, face=face, **ch)


def tracks(tg):
    """tg：各次打击的落点（由对方的动作算出来，见 build 里的两遍迭代）"""
    def bob_gold(t):
        w = max(window(t, -1, 1.12), window(t, 3.05, 3.46))
        return {"y": 4.5 * w * math.sin(2 * math.pi * 2.0 * t)}

    def bob_cyan(t):
        w = max(window(t, -1, 1.0), window(t, 3.10, 3.64))
        return {"y": 4.5 * w * math.sin(2 * math.pi * 2.0 * t + 1.9)}

    gold = [
        guard(0.0, 780, 1),
        guard(1.16, 780, 1),
        # 1 看到拳来才后仰：脚不动，重心往后、上身后仰
        K(T_PUNCH, "out", x=752, y=GUARD_Y + 18, lean=-34, head=-20, aF=62, fF=150, aB=42, fB=160),
        # 2 压低身子扑回来，上步一拳打肚子
        K(1.44, "in", x=800, y=GUARD_Y + 26, lean=14, head=6, aF=30, fF=150, aB=20, fB=165),
        K(T_COUNTER, "snap", lift=14, x=842, y=GUARD_Y + 30, lean=30, head=8, handF=tg["belly"], aB=12, fB=168,
          footF=(900, FOOT_Y)),
        K(1.80, x=806, y=GUARD_Y, lean=10, head=4, aF=35, fF=155, aB=18, fB=165, footF=(858, FOOT_Y)),
        guard(2.10, 800, 1),
        # 3 双臂格挡，被踢得往后滑
        K(2.32, "out", x=800, y=GUARD_Y + 10, lean=12, head=10, aF=72, fF=176, aB=58, fB=178),
        K(T_KICK, "linear", x=802, y=GUARD_Y + 12, lean=14, head=12),
        K(2.74, "out", lift=0, x=728, y=GUARD_Y + 16, lean=6, head=8, footF=(780, FOOT_Y), footB=(672, FOOT_Y)),
        guard(3.05, 734, 1),
        guard(3.40, 738, 1, dy=4),
        # 4 下沉蓄力 → 冲刺 → 上勾拳 → 拳头送上去、踮脚
        K(3.52, x=728, y=GUARD_Y + 22, lean=22, head=6, aF=10, fF=40, aB=30, fB=150),
        K(3.635, "in", lift=18, x=930, y=GUARD_Y + 40, lean=26, head=4, aF=-12, fF=28,
          footF=(992, FOOT_Y), footB=(880, FOOT_Y)),
        # 贴到青身前：肩膀在下巴前下方，拳头才是从下往上打，不是平着打脸
        K(T_UPPER, "snap", lift=8, x=982, y=GUARD_Y + 10, lean=2, head=-8, handF=tg["chin"], aB=-30, fB=20,
          footF=(1026, FOOT_Y), footB=(922, FOOT_Y)),
        K(3.90, "out", x=996, y=GUARD_Y - 26, lean=-6, head=-16, aF=172, fF=178, aB=-40, fB=10),
        K(4.20, x=992, y=GUARD_Y, lean=8, head=0, aF=35, fF=155, aB=18, fB=165,
          footF=(1042, FOOT_Y), footB=(936, FOOT_Y)),
        K(5.0, x=992, y=GUARD_Y + 2, lean=8, head=-4),
        # 收：站直、放下手
        K(5.55, x=996, y=STAND_Y + 2, lean=2, head=6, aF=8, fF=20, aB=-6, fB=8,
          footF=(1028, FOOT_Y), footB=(956, FOOT_Y)),
        K(END, x=996, y=STAND_Y + 3, lean=2, head=10),
    ]
    cyan = [
        guard(0.0, 1160, -1),
        guard(1.0, 1160, -1),
        # 1 下沉 → 冲上来 → 直拳打向金头所在的位置（金这时才开始后仰）
        K(1.08, x=1166, y=GUARD_Y + 10, lean=16, head=6),
        K(1.20, "out", lift=20, x=1012, y=GUARD_Y + 4, lean=20, head=4, footF=(957, FOOT_Y), footB=(1070, FOOT_Y)),
        K(T_PUNCH, "snap", x=994, y=GUARD_Y + 2, lean=24, head=2, handF=tg["gold_head"]),
        K(1.46, x=1004, y=GUARD_Y, lean=6, head=0, aF=40, fF=140, aB=18, fB=160),
        K(T_COUNTER, "linear", x=1004, y=GUARD_Y, lean=6, head=0),
        # 2 被打中：上身后仰、头往后甩、两臂甩开，退一步
        K(1.66, "snap", lift=12, x=1050, y=GUARD_Y + 12, lean=-22, head=-26, aF=-35, fF=-5, aB=-60, fB=-20,
          footF=(1000, FOOT_Y), footB=(1108, FOOT_Y)),
        K(1.92, "out", x=1080, y=GUARD_Y + 6, lean=4, head=0, aF=30, fF=140, aB=15, fB=160,
          footF=(1030, FOOT_Y), footB=(1138, FOOT_Y)),
        guard(2.04, 1085, -1),
        # 3 下蹲 → 跳起 → 侧踢踢到金的小臂 → 被弹回 → 落地
        K(2.14, x=1090, y=GUARD_Y + 34, lean=16, head=6, aF=-25, fF=15, aB=-35, fB=5),
        K(2.28, "out", x=1066, y=GUARD_Y - 70, lean=-2, head=0, aF=50, fF=140, aB=25, fB=130,
          tF=88, sF=10, tB=45, sB=-85),
        K(T_KICK, "out", x=1044, y=GUARD_Y - 110, lean=-26, head=-6, footF=tg["block"], bend={"legF": "up"},
          tB=35, sB=-95, aF=30, fF=90, aB=-30, fB=20),
        K(2.64, "out", x=1076, y=GUARD_Y - 80, lean=-12, head=-2, tF=60, sF=-30, tB=30, sB=-70),
        K(2.86, "in", x=1096, y=GUARD_Y + 30, lean=18, head=8, footF=(1046, FOOT_Y), footB=(1150, FOOT_Y),
          bend={"legF": "front"}, aF=30, fF=120, aB=10, fB=150),
        guard(3.10, 1096, -1),
        guard(3.58, 1096, -1),
        K(T_UPPER, x=1094, y=GUARD_Y + 4, lean=8, head=2),
        K(END, x=1094, y=GUARD_Y + 4),
    ]
    return Track(gold, face=1, extra=bob_gold), Track(cyan, face=-1, extra=bob_cyan)


def targets(g, c):
    """按对方那一刻的关节位置算落点"""
    jc, _ = c.joints(T_COUNTER)
    belly = (jc[0][0] + (jc[1][0] - jc[0][0]) * 0.45, jc[0][1] + (jc[1][1] - jc[0][1]) * 0.45)
    jc, _ = c.joints(T_UPPER)
    chin = (jc[2][0] - 14, jc[2][1] + 26)          # 青朝左：下巴在头的左下方
    jg, _ = g.joints(1.16)
    jk, _ = g.joints(T_KICK)
    block = ((jk[3][0] + jk[4][0]) / 2 + 8, (jk[3][1] + jk[4][1]) / 2)
    return {"belly": belly, "chin": chin, "gold_head": jg[2], "block": block}


def build():
    tg = {"belly": (998, 662), "chin": (1059, 594), "gold_head": (807, 569), "block": (894, 595)}
    for _ in range(2):
        g, c = tracks(tg)
        tg = targets(g, c)
    g, c = tracks(tg)

    # 三次打中各顿几帧（动作时间停住、真实时间照走）
    stops = [(T_COUNTER, 0.07), (T_KICK, 0.06), (T_UPPER, 0.12)]
    tm, off = [(0.0, 0.0)], 0.0
    for ta, h in stops:
        tm += [(ta + off, ta), (ta + off + h, ta)]
        off += h
    tm.append((END + off, END))
    sc = Scene(END + off, FPS)
    sc.timemap(tm)
    sc.add(Figure("gold", g, GOLD))
    cyan = sc.add(Figure("cyan", c, CYAN, core="#e9fffb"))

    # 上勾拳打中：青交给物理。上身给得多、腿给得少，整个人会向后翻
    def kick(i):
        up = {2: 1100, 1: 1040, 0: 860, 3: 980, 4: 980, 5: 980, 6: 980, 7: 700, 9: 700, 8: 540, 10: 540}[i]
        back = {2: 380, 1: 350, 0: 290}.get(i, 260 if i in (3, 4, 5, 6) else 200)
        return back, -up
    ep = cyan.ragdoll(T_UPPER, kick)

    # —— 打击点：粒子、震屏、音效 ——
    hx, hy = tg["belly"]
    sc.burst(T_COUNTER, hx, hy, "spark", n=18, speed=900, angle=-10, spread=130, life=14, size=4, color=GOLD)
    sc.burst(T_COUNTER, hx, hy, "ring", size=10, speed=120, life=12, color=GOLD)
    sc.burst(T_COUNTER, hx, hy, "flare", size=44, life=6, color=GOLD)
    sc.shake(T_COUNTER, 7, 0.3, anim=True)
    bx, by = tg["block"]
    sc.burst(T_KICK, bx, by, "spark", n=14, speed=820, angle=-120, spread=150, life=14, size=3.6, color=CYAN)
    sc.burst(T_KICK, bx, by, "spark", n=12, speed=760, angle=-60, spread=150, life=14, size=3.6, color=GOLD, seed=777)
    sc.burst(T_KICK, bx, by, "ring", size=10, speed=130, life=12, color="#dfe9f5")
    sc.burst(T_KICK, bx, by, "flare", size=40, life=6, color=CYAN)
    sc.shake(T_KICK, 6, 0.3, anim=True)
    for t in (2.52, 2.59, 2.66):                    # 被踢得滑出去：脚下一路起尘
        sc.burst(t, 780 - (t - T_KICK) * 300, 860, "dust", n=6, speed=150, angle=-150, spread=60, life=18, size=8,
                 color="#c9cfdb")
    ux, uy = tg["chin"]
    sc.burst(T_UPPER, ux, uy, "spark", n=30, speed=1150, angle=-65, spread=120, life=18, size=5, color=GOLD)
    sc.burst(T_UPPER, ux, uy, "spark", n=12, speed=800, angle=-40, spread=90, life=14, size=3.4, color=CYAN, seed=999)
    sc.burst(T_UPPER, ux, uy, "ring", size=14, speed=230, life=16, color=GOLD)
    sc.burst(T_UPPER, ux, uy, "flare", size=80, life=8, color=GOLD)
    sc.shake(T_UPPER, 14, 0.4, anim=True)
    for t, x in ((1.20, 1070), (2.28, 1100), (2.86, 1100), (3.635, 850)):
        sc.burst(t, x, 860, "dust", n=7, speed=160, angle=-90, spread=160, life=18, size=8, color="#c9cfdb")

    for t, kind, gn in ((1.12, "whoosh", 0.45), (1.20, "step", 0.5), (1.25, "whip", 0.5), (1.48, "whip", 0.35),
                        (T_COUNTER, "punch", 1.0), (1.66, "step", 0.45), (1.92, "step", 0.35),
                        (2.28, "step", 0.6), (2.28, "whoosh", 0.4), (2.42, "whip", 0.4), (T_KICK, "block", 1.0),
                        (2.55, "step", 0.4), (2.86, "step", 0.7), (3.55, "whoosh", 0.6), (3.635, "step", 0.55),
                        (3.66, "whip", 0.5), (T_UPPER, "punch", 1.0), (T_UPPER, "impact", 0.6), (4.20, "step", 0.5)):
        sc.sfx(t, kind, gn)

    # 相机按动作时间排的，换算成真实时间
    for ta, cx, cy, z, *ease in ((0.0, 970, 615, 1.3), (1.0, 965, 610, 1.36), (T_COUNTER, 930, 612, 1.5),
                                 (2.1, 950, 600, 1.34), (T_KICK, 940, 588, 1.45), (3.05, 950, 610, 1.32),
                                 (3.6, 960, 610, 1.42, "sine"), (T_UPPER, 1010, 588, 1.52),
                                 (4.25, 1200, 540, 1.0, "out"), (5.0, 1250, 615, 1.06), (END, 1190, 630, 1.15, "sine")):
        sc.camera(sc.real(ta), cx, cy, z, *(ease or ["inout"]))

    # 布偶要先算出来才知道落地时刻：先算一遍，再按落地事件补尘土、闷响、震屏
    cyan.prepare(sc.fps, END + 0.5)
    sc.impacts(cyan, ep, min_speed=420)
    info = {k: str(tuple(round(v) for v in tg[k])) for k in ("belly", "chin", "block")}
    info["落地"] = ", ".join(f"{t:.2f}s/{v:.0f}" for t, _, v, _ in sorted(ep.events)[:6])
    return sc, info
