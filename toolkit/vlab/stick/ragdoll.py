"""布偶物理：火柴人被打飞、摔倒、被摔出去以后交给物理算。

Verlet 积分 + 骨长约束 + 关节角限制 + 地面碰撞（摩擦、反弹），另有两样"接触"：
    pins       —— 抓住：某个关节在一段时间里被拉向一个移动的目标（比如被对方的手抓着手腕）；
    obstacles  —— 顶住：一个移动的圆挡在那里，关节进不去（比如过肩摔时对方的髋部和后背）。
质点就是 rig 里的 11 个关节，骨头是长度约束——和关键帧用同一套骨架，切换那一帧不会跳。
重力用 rig.G（按 9.8 m/s² 换算），所以飞出去的轨迹就是真实的抛体。
"""
import math

from .rig import BODY, GROUND, ang

# (父, 子, 骨长字段)；head 的长度是颈部间隙 + 头半径
BONES = [(0, 1, "torso"), (1, 2, "head"), (1, 3, "uarm"), (3, 4, "farm"), (1, 5, "uarm"), (5, 6, "farm"),
         (0, 7, "thigh"), (7, 8, "shin"), (0, 9, "thigh"), (9, 10, "shin")]
MASS = [3.0, 3.0, 2.0, 1.0, 0.6, 1.0, 0.6, 1.4, 1.0, 1.4, 1.0]
# 关节角限制：(父, 关节, 子, 相对角下限, 上限)。相对角 = 子段绝对角 - 父段绝对角（度）
# 手肘只能往前弯，膝盖只能往后弯，头不能折到背后，大腿不能踢到背后去
LIMITS = [
    (1, 3, 4, -5.0, 160.0),       # 前臂 / 上臂
    (1, 5, 6, -5.0, 160.0),
    (0, 7, 8, -155.0, 5.0),       # 小腿 / 大腿
    (0, 9, 10, -155.0, 5.0),
    (1, 0, 7, -50.0, 150.0),      # 大腿 / 躯干向下
    (1, 0, 9, -50.0, 150.0),
    (0, 1, 2, -60.0, 45.0),       # 头 / 躯干向上
]


def _length(name, body):
    return body.neck_gap + body.head_r if name == "head" else getattr(body, name)


def simulate(J0, Jprev, dt_frame, face, frames, kick=None, body=BODY, g=None, substeps=8, iters=10,
             friction=0.06, bounce=0.22, air=0.999, pins=(), obstacles=()):
    """从关键帧最后两帧（J0、Jprev，相隔 dt_frame 秒）接手，往后算 frames 帧。

    kick(i) -> (vx, vy)：第 i 个关节额外加的速度（px/s），就是那一拳给的冲量。
    pins：[{"i": 关节, "t0": 秒, "t1": 秒, "target": f(t) -> (x, y), "k": 0~1 拉得多紧}]，t 从接手那一刻算起。
    obstacles：[{"t0", "t1", "center": f(t) -> (x, y), "r": 半径, "only": [关节号]（可省）}]。
    返回 (每帧关节坐标列表, 落地事件列表)；事件是 (秒, x, 下落速度 px/s, 关节号)。
    """
    from .rig import G
    g = G if g is None else g
    n = len(J0)
    dt = dt_frame / substeps
    x = [list(p) for p in J0]
    v0 = [((J0[i][0] - Jprev[i][0]) / dt_frame, (J0[i][1] - Jprev[i][1]) / dt_frame) for i in range(n)]
    if kick:
        v0 = [(v0[i][0] + kick(i)[0], v0[i][1] + kick(i)[1]) for i in range(n)]
    xp = [[x[i][0] - v0[i][0] * dt, x[i][1] - v0[i][1] * dt] for i in range(n)]
    inv = [1.0 / m for m in MASS]
    rad = [body.width / 2] * n
    rad[2] = body.head_r
    lens = [(a, b, _length(nm, body)) for a, b, nm in BONES]
    out, events = [[tuple(p) for p in x]], []
    last_hit = [-1.0] * n

    def limit_angles():
        for p, j, c, lo, hi in LIMITS:
            a1 = ang(x[j][0] - x[p][0], x[j][1] - x[p][1], face)
            a2 = ang(x[c][0] - x[j][0], x[c][1] - x[j][1], face)
            rel = (a2 - a1 + 180.0) % 360.0 - 180.0
            if lo <= rel <= hi:
                continue
            target = a1 + (lo if rel < lo else hi)
            L = math.hypot(x[c][0] - x[j][0], x[c][1] - x[j][1])
            r = math.radians(target)
            x[c][0] = x[j][0] + face * math.sin(r) * L
            x[c][1] = x[j][1] + math.cos(r) * L

    def contacts(t):
        for pin in pins:
            if pin["t0"] <= t <= pin["t1"]:
                tx, ty = pin["target"](t)
                k = pin.get("k", 1.0)
                i = pin["i"]
                x[i][0] += (tx - x[i][0]) * k
                x[i][1] += (ty - x[i][1]) * k
        for ob in obstacles:
            if ob["t0"] <= t <= ob["t1"]:
                cx, cy = ob["center"](t)
                for i in ob.get("only") or range(n):
                    dx, dy = x[i][0] - cx, x[i][1] - cy
                    d = math.hypot(dx, dy) or 1e-6
                    rr = ob["r"] + rad[i]
                    if d < rr:
                        x[i][0] = cx + dx / d * rr
                        x[i][1] = cy + dy / d * rr

    for f in range(frames):
        for s in range(substeps):
            t_now = (f * substeps + s + 1) * dt
            for i in range(n):
                vx, vy = (x[i][0] - xp[i][0]) * air, (x[i][1] - xp[i][1]) * air
                xp[i] = [x[i][0], x[i][1]]
                x[i][0] += vx
                x[i][1] += vy + g * dt * dt
            for _ in range(iters):
                for a, b, L in lens:
                    dx, dy = x[b][0] - x[a][0], x[b][1] - x[a][1]
                    d = math.hypot(dx, dy) or 1e-6
                    k = (d - L) / d / (inv[a] + inv[b])
                    x[a][0] += dx * k * inv[a]
                    x[a][1] += dy * k * inv[a]
                    x[b][0] -= dx * k * inv[b]
                    x[b][1] -= dy * k * inv[b]
                limit_angles()
                contacts(t_now)
                for i in range(n):
                    floor = GROUND - rad[i]
                    if x[i][1] > floor:
                        x[i][1] = floor
            # 地面：反弹 + 摩擦（在约束之后统一处理速度，避免反复抵消）
            for i in range(n):
                floor = GROUND - rad[i]
                if x[i][1] >= floor - 0.01:
                    vy = (x[i][1] - xp[i][1]) / dt
                    vx = (x[i][0] - xp[i][0]) / dt
                    if vy > 260 and t_now - last_hit[i] > 0.12:
                        events.append((t_now, x[i][0], vy, i))
                    if vy > 0:
                        last_hit[i] = t_now if vy > 260 else last_hit[i]
                        xp[i][1] = x[i][1] + vy * bounce * dt
                    xp[i][0] = x[i][0] - vx * (1 - friction) * dt
        out.append([tuple(p) for p in x])
    return out, events
