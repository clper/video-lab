"""火柴人骨架：姿势 → 关节坐标（正向运动学）、两段骨的反向运动学、关键帧插值、重心。

坐标：1920×1080 设计舞台，y 向下（和 Remotion 卡 stickScene 一致），地面 y = GROUND。
角度一律是"绝对角"，单位度：0 = 朝下，90 = 朝前（脸朝的方向），180 = 朝上，-90 = 朝后。
肢体角不随躯干转（不是层级骨骼），摆姿势时"手朝正前"就是 90，不用先算躯干。
躯干 lean：0 = 直立，正 = 前倾；头 head：相对躯干的点头角，正 = 低头。
朝向 face：+1 朝右，-1 朝左。肢体分前后：F 是靠近镜头的一侧（画在上层），B 是远的一侧。
"""
import math
from dataclasses import dataclass, field, replace

GROUND = 860.0


@dataclass(frozen=True)
class Body:
    head_r: float = 26.0
    neck_gap: float = 4.0
    torso: float = 112.0
    uarm: float = 62.0
    farm: float = 60.0
    thigh: float = 84.0
    shin: float = 80.0
    width: float = 11.0      # 线宽；脚点离地半个线宽，圆头正好落在地面上

    def scaled(self, k, width=None):
        """等比放大缩小（线宽单独给，粗一点显得重）"""
        return replace(self, head_r=self.head_r * k, neck_gap=self.neck_gap * k, torso=self.torso * k,
                       uarm=self.uarm * k, farm=self.farm * k, thigh=self.thigh * k, shin=self.shin * k,
                       width=self.width * k if width is None else width)

    @property
    def height(self):
        return self.thigh + self.shin + self.torso + self.neck_gap + 2 * self.head_r

    @property
    def foot_y(self):
        return GROUND - self.width / 2

    @property
    def stand_y(self):
        """站直时骨盆高度（膝盖微屈一点）"""
        return self.foot_y - (self.thigh + self.shin) + 4 * self.torso / 112


BODY = Body()
FOOT_Y = BODY.foot_y
STAND_Y = BODY.stand_y
HEIGHT = BODY.height
PX_PER_M = HEIGHT / 1.75                               # 默认火柴人按 1.75 米算，1 米 ≈ 190 px
G = 9.8 * PX_PER_M                                     # 重力加速度（px/s²），球、布偶、羽毛共用

JOINTS = ("pelvis", "neck", "head", "elbowF", "handF", "elbowB", "handB", "kneeF", "footF", "kneeB", "footB")
CORE = ("x", "y", "lean", "head")
LIMBS = {  # 肢体 → (两节角的通道名, 根部, 两节骨长, IK 的弯曲偏好)
    "armF": (("aF", "fF"), "neck", ("uarm", "farm"), "down"),
    "armB": (("aB", "fB"), "neck", ("uarm", "farm"), "down"),
    "legF": (("tF", "sF"), "pelvis", ("thigh", "shin"), "front"),
    "legB": (("tB", "sB"), "pelvis", ("thigh", "shin"), "front"),
}
TARGET_KEY = {"armF": "handF", "armB": "handB", "legF": "footF", "legB": "footB"}

# 各段占体重的比例（Dempster / Winter 的人体测量表，取整）：头 8%、躯干 50%、上臂 2.8%、前臂连手 2.2%、
# 大腿 10%、小腿连脚 6.1%。重心 = 各段中点按这个比例加权
SEG_MASS = [((2,), 0.08), ((0, 1), 0.50), ((1, 3), 0.028), ((3, 4), 0.022), ((1, 5), 0.028), ((5, 6), 0.022),
            ((0, 7), 0.10), ((7, 8), 0.061), ((0, 9), 0.10), ((9, 10), 0.061)]


def com(J):
    """11 个关节坐标 → 重心"""
    sx = sy = sw = 0.0
    for idx, w in SEG_MASS:
        px = sum(J[i][0] for i in idx) / len(idx)
        py = sum(J[i][1] for i in idx) / len(idx)
        sx, sy, sw = sx + px * w, sy + py * w, sw + w
    return sx / sw, sy / sw


def vec(a_deg, face):
    a = math.radians(a_deg)
    return face * math.sin(a), math.cos(a)


def ang(vx, vy, face):
    """向量 → 绝对角（vec 的反函数）"""
    return math.degrees(math.atan2(face * vx, vy))


def unwrap(a, ref):
    """把角 a 换成离 ref 最近的等价角（插值时不绕远路）"""
    return a + 360.0 * round((ref - a) / 360.0)


def neck_of(x, y, lean, face, body=BODY):
    L = math.radians(lean)
    return x + face * math.sin(L) * body.torso, y - math.cos(L) * body.torso


def fk(p, face, body=BODY):
    """姿势通道 → 11 个关节坐标（顺序见 JOINTS）"""
    x, y = p["x"], p["y"]
    nx, ny = neck_of(x, y, p["lean"], face, body)
    H = math.radians(p["lean"] + p["head"])
    d = body.neck_gap + body.head_r
    head = (nx + face * math.sin(H) * d, ny - math.cos(H) * d)

    def chain(base, a1, a2, l1, l2):
        v1 = vec(a1, face)
        j = (base[0] + v1[0] * l1, base[1] + v1[1] * l1)
        v2 = vec(a2, face)
        return j, (j[0] + v2[0] * l2, j[1] + v2[1] * l2)

    eF, hF = chain((nx, ny), p["aF"], p["fF"], body.uarm, body.farm)
    eB, hB = chain((nx, ny), p["aB"], p["fB"], body.uarm, body.farm)
    kF, fF = chain((x, y), p["tF"], p["sF"], body.thigh, body.shin)
    kB, fB = chain((x, y), p["tB"], p["sB"], body.thigh, body.shin)
    return [(x, y), (nx, ny), head, eF, hF, eB, hB, kF, fF, kB, fB]


def pose_from_joints(J, face):
    """关节坐标 → 姿势通道（布偶倒地后接回关键帧时用）"""
    (px, py), (nx, ny), (hx, hy) = J[0], J[1], J[2]
    lean = ang(nx - px, -(ny - py), face)          # 躯干竖直向上为 0
    head = ang(hx - nx, -(hy - ny), face) - lean
    head = (head + 180.0) % 360.0 - 180.0
    p = {"x": px, "y": py, "lean": lean, "head": head}
    for limb, base_i, mid_i, end_i in (("armF", 1, 3, 4), ("armB", 1, 5, 6), ("legF", 0, 7, 8), ("legB", 0, 9, 10)):
        c1, c2 = LIMBS[limb][0]
        b, m, e = J[base_i], J[mid_i], J[end_i]
        p[c1] = ang(m[0] - b[0], m[1] - b[1], face)
        p[c2] = unwrap(ang(e[0] - m[0], e[1] - m[1], face), p[c1])
    return p


def ik2(base, target, l1, l2, face, bend, ref=None):
    """两段骨 IK：根在 base、末端够到 target，返回两节的绝对角。
    bend：中间关节偏向哪边——front 朝脸的方向（膝盖），down 朝下（出拳的手肘），back 朝后，up 朝上。"""
    dx, dy = target[0] - base[0], target[1] - base[1]
    dist = math.hypot(dx, dy)
    d = max(abs(l1 - l2) + 1e-3, min(l1 + l2 - 1e-3, dist))
    th = math.atan2(dy, dx)
    A = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    want = {"front": (face, 0.0), "back": (-face, 0.0), "down": (0.0, 1.0), "up": (0.0, -1.0)}[bend]
    best = None
    for s in (1, -1):
        a = th + s * A
        j = (base[0] + math.cos(a) * l1, base[1] + math.sin(a) * l1)
        score = (j[0] - base[0]) * want[0] + (j[1] - base[1]) * want[1]
        if best is None or score > best[0]:
            best = (score, j)
    j = best[1]
    end = (base[0] + math.cos(th) * d, base[1] + math.sin(th) * d)   # 够不到时沿方向伸直
    a1 = ang(j[0] - base[0], j[1] - base[1], face)
    a2 = ang(end[0] - j[0], end[1] - j[1], face)
    if ref is not None:
        a1 = unwrap(a1, ref[0])
    a2 = unwrap(a2, a1)
    return a1, a2


EASE = {
    "linear": lambda u: u,
    "in": lambda u: u ** 3,
    "in2": lambda u: u ** 2,
    "out": lambda u: 1 - (1 - u) ** 3,
    "out2": lambda u: 1 - (1 - u) ** 2,
    "inout": lambda u: 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2,
    "sine": lambda u: 0.5 - 0.5 * math.cos(math.pi * u),
    "snap": lambda u: 1 - (1 - u) ** 5,          # 出拳：起手就快
    "back": lambda u: 1 + 2.70158 * (u - 1) ** 3 + 1.70158 * (u - 1) ** 2,   # 过冲再回来
    "hold": lambda u: 0.0 if u < 1 else 1.0,
}


@dataclass
class Key:
    t: float
    ch: dict                     # 姿势通道（可只写一部分，没写的沿用上一帧）
    ease: str = "inout"          # 从上一个关键帧走到这里用的缓动
    face: int | None = None
    targets: dict = field(default_factory=dict)   # handF/handB/footF/footB → (x, y)
    lift: float = 26.0           # 脚从一个落点换到另一个落点时抬多高
    bend: dict = field(default_factory=dict)      # 某条肢体 IK 的弯曲偏好


def K(t, ease="inout", face=None, lift=26.0, bend=None, **kw):
    """写关键帧的简写：K(1.2, "snap", x=500, lean=10, footF=(520, FOOT_Y), handF=(...))"""
    targets = {k: kw.pop(k) for k in list(kw) if k in TARGET_KEY.values()}
    return Key(t, kw, ease, face, targets, lift, bend or {})


class Track:
    """一个角色的关键帧轨。肢体每一帧要么按角度插值，要么（前后两帧都给了落点时）按落点插值再解 IK，
    这样站着的脚不会在地上滑、出拳的手正好打到目标上。"""

    def __init__(self, keys, face=1, body=BODY, extra=None):
        self.body = body
        self.extra = extra                      # extra(t) -> 通道增量（呼吸、拳击步的上下颠）
        self.keys = self._resolve(sorted(keys, key=lambda k: k.t), face)

    def _resolve(self, keys, face0):
        out, prev = [], None
        for k in keys:
            face = k.face if k.face is not None else (prev["face"] if prev else face0)
            ch = dict(prev["ch"]) if prev else {}
            ch.update(k.ch)
            modes = dict(prev["modes"]) if prev else {}
            turned = prev is not None and prev["face"] != face
            for limb, (chs, _, _, _) in LIMBS.items():
                tk = TARGET_KEY[limb]
                if tk in k.targets:
                    modes[limb] = ("ik", k.targets[tk])
                elif chs[0] in k.ch or chs[1] in k.ch or limb not in modes or turned:
                    modes[limb] = ("ang", None)
            bend = dict(prev["bend"]) if prev else {}
            bend.update(k.bend)
            r = {"t": k.t, "ease": k.ease, "face": face, "ch": ch, "modes": modes, "lift": k.lift, "bend": bend}
            r["ang"] = self._solve(ch, modes, face, bend, ref=prev["ang"] if prev else None)
            for c, v in r["ang"].items():           # IK 解出来的角写回通道，后面的关键帧沿用
                ch[c] = v
            out.append(r)
            prev = r
        return out

    def _solve(self, core, modes, face, bend, ref=None):
        """按通道和落点解出四条肢体的角度"""
        b = self.body
        res = {}
        neck = neck_of(core["x"], core["y"], core["lean"], face, b)
        for limb, (chs, base, lens, bend0) in LIMBS.items():
            mode, target = modes[limb]
            if mode == "ik":
                root = neck if base == "neck" else (core["x"], core["y"])
                r = (ref[chs[0]], ref[chs[1]]) if ref else None
                a1, a2 = ik2(root, target, getattr(b, lens[0]), getattr(b, lens[1]), face, bend.get(limb, bend0), r)
            else:
                a1, a2 = core[chs[0]], core[chs[1]]
            res[chs[0]], res[chs[1]] = a1, a2
        return res

    @property
    def t_end(self):
        return self.keys[-1]["t"]

    def pose(self, t):
        """t 时刻的姿势通道 + 朝向"""
        ks = self.keys
        if t <= ks[0]["t"]:
            k0 = k1 = ks[0]
            e = 0.0
        elif t >= ks[-1]["t"]:
            k0 = k1 = ks[-1]
            e = 1.0
        else:
            i = max(j for j in range(len(ks)) if ks[j]["t"] <= t)
            k0, k1 = ks[i], ks[i + 1]
            u = (t - k0["t"]) / (k1["t"] - k0["t"])
            e = EASE[k1["ease"]](u)
        face = k1["face"] if e >= 1 else k0["face"]
        p = {c: k0["ch"][c] + (k1["ch"][c] - k0["ch"][c]) * e for c in CORE}
        add = (self.extra(t) or {}) if self.extra else {}
        for c in CORE:
            p[c] += add.get(c, 0.0)
        neck = neck_of(p["x"], p["y"], p["lean"], face, self.body)
        for limb, (chs, base, lens, bend0) in LIMBS.items():
            m0, m1 = k0["modes"][limb], k1["modes"][limb]
            a = [k0["ang"][c] + (k1["ang"][c] - k0["ang"][c]) * e for c in chs]
            if m0[0] == "ik" and m1[0] == "ik" and k0["face"] == k1["face"]:
                (x0, y0), (x1, y1) = m0[1], m1[1]
                tx, ty = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
                if base == "pelvis" and math.hypot(x1 - x0, y1 - y0) > 1:
                    ty -= k1["lift"] * math.sin(math.pi * min(1.0, max(0.0, e)))   # 迈步：脚走一条弧线
                root = neck if base == "neck" else (p["x"], p["y"])
                a = list(ik2(root, (tx, ty), getattr(self.body, lens[0]), getattr(self.body, lens[1]), face,
                             k1["bend"].get(limb, bend0), ref=a))
            p[chs[0]], p[chs[1]] = a[0] + add.get(chs[0], 0.0), a[1] + add.get(chs[1], 0.0)
        return p, face

    def joints(self, t):
        p, face = self.pose(t)
        return fk(p, face, self.body), face
