"""火柴人场景：角色（关键帧 + 布偶）、时间、相机、粒子、物理标注、音效事件 → Remotion 卡 stickScene 的数据。

时间有两套：
    动作时间（ta）—— 写关键帧和物理用的时间，连续；
    真实时间（t） —— 成片的时间。两者的关系是一条分段直线（timemap）：
                    斜率 1 是正常播放，0 是定格（打中时顿几帧、讲物理时定住），小于 1 是慢镜头，
                    往回跳再慢放就是"重放"。物理按动作时间算，所以定格、慢放时画面里的物理照样是对的。
关键帧、布偶、粒子、动作音效写动作时间；相机、物理标注、屏上字是剪辑层面的东西，写真实时间。
"""
import math

from . import ragdoll
from .rig import EASE, GROUND, Track, com, pose_from_joints


class Episode:
    """一段布偶：动作时间 t0 起交给物理，until 时刻用 then(姿势, until) 返回的关键帧接回来（爬起来）"""

    def __init__(self, t0, kick=None, until=None, then=None, pins=(), obstacles=(), friction=0.06, bounce=0.22,
                 extra=None, lead=None):
        self.t0, self.kick, self.until, self.then = t0, kick, until, then
        self.pins, self.obstacles = list(pins), list(obstacles)
        self.friction, self.bounce, self.extra = friction, bounce, extra
        # lead = (起始动作时间, factory)：布偶接手之前，先用一段脚本动作（比如绕着支点翻过去）；
        # factory(当时的关键帧轨) 返回 f(动作时间) -> 关节坐标。布偶从脚本最后两帧接手，速度连续
        self.lead = lead
        self.frames, self.events, self.face = None, [], 1


class Figure:
    def __init__(self, name, track, color, core="#fff7e0", mass=60.0):
        self.name, self.track, self.color, self.core, self.mass = name, track, color, core, mass
        self.body = track.body
        self.episodes = []
        self.segments = []
        self.fps = 30
        self.clock = None       # 单独的时钟 f(真实秒) -> 动作秒，返回 None 时跟场景走（重放时只让一个人倒回去慢放）

    def ragdoll(self, ta, kick=None, until=None, then=None, **kw):
        ep = Episode(ta, kick, until, then, **kw)
        self.episodes.append(ep)
        return ep

    def prepare(self, fps, ta_end):
        """依次算每一段布偶，接回来的关键帧再作为下一段布偶的起点"""
        self.fps = fps
        self.segments = []
        cur, t_prev = self.track, -1e9
        for ep in sorted(self.episodes, key=lambda e: e.t0):
            if ep.lead:
                ts, factory = ep.lead
                fn = factory(cur)
                face = cur.joints(ts)[1]
                self.segments.append((t_prev, ts, "track", cur))
                self.segments.append((ts, ep.t0, "fn", fn))
                J0, Jp = fn(ep.t0), fn(ep.t0 - 1.0 / fps)
            else:
                self.segments.append((t_prev, ep.t0, "track", cur))
                J0, face = cur.joints(ep.t0)
                Jp, _ = cur.joints(ep.t0 - 1.0 / fps)
            end = ep.until if ep.until is not None else ta_end
            n = int(math.ceil((end - ep.t0) * fps)) + 2
            t0 = ep.t0
            pins = [dict(p, t0=p["t0"] - t0, t1=p["t1"] - t0, target=(lambda t, f=p["target"]: f(t0 + t)))
                    for p in ep.pins]
            obs = [dict(o, t0=o["t0"] - t0, t1=o["t1"] - t0, center=(lambda t, f=o["center"]: f(t0 + t)))
                   for o in ep.obstacles]
            ep.frames, ev = ragdoll.simulate(J0, Jp, 1.0 / fps, face, n, kick=ep.kick, body=self.body,
                                             pins=pins, obstacles=obs, friction=ep.friction, bounce=ep.bounce)
            ep.events = [(t0 + e[0], e[1], e[2], e[3]) for e in ev]
            ep.face = face
            self.segments.append((ep.t0, end, "rag", ep))
            if ep.until is None or ep.then is None:
                return
            pose = pose_from_joints(self._rag_at(ep, end), face)
            cur = Track(ep.then(pose, end), face=face, body=self.body, extra=ep.extra)
            t_prev = end
        self.segments.append((t_prev, 1e9, "track", cur))

    def _rag_at(self, ep, ta):
        fr = ep.frames
        k = max(0.0, (ta - ep.t0) * self.fps)
        i = min(int(k), len(fr) - 2)
        u = min(1.0, k - i)
        return [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for a, b in zip(fr[i], fr[i + 1])]

    def joints(self, ta):
        if not self.segments:
            return self.track.joints(ta)[0]
        for t0, t1, kind, obj in self.segments:
            if t0 <= ta < t1:
                return self._seg(kind, obj, ta)
        t0, t1, kind, obj = self.segments[-1]
        return self._seg(kind, obj, ta)

    def _seg(self, kind, obj, ta):
        if kind == "track":
            return obj.joints(ta)[0]
        if kind == "fn":
            return obj(ta)
        return self._rag_at(obj, ta)

    def touchdown(self, ep, joints=(0, 1), margin=40.0):
        """这段布偶里，躯干第一次落到离地面 margin 以内的动作时间（"整个人砸到地上"的那一刻）"""
        floor = GROUND - self.body.width / 2 - margin
        for k, J in enumerate(ep.frames):
            if any(J[i][1] >= floor for i in joints):
                return ep.t0 + k / self.fps
        return None

    def com(self, ta):
        return com(self.joints(ta))


class Scene:
    def __init__(self, total, fps=30):
        self.total = total                  # 成片时长（真实时间，秒）
        self.fps = fps
        self.figures = []
        self.tmap = [(0.0, 0.0), (total, total)]
        self.cam_keys = []                  # (真实时间, cx, cy, zoom, 缓动, 是否硬切)
        self.shakes = []                    # (真实时间, 幅度 px, 持续秒)
        self.bursts = []
        self.sfx_events = []
        self.layers = {k: [] for k in ("balls", "ghosts", "paths", "labels", "arcs", "walls", "arrows", "dots",
                                        "bars", "tris", "flows", "feathers")}
        self.grid = False
        self.trail = 7
        self.reflect = 0.16
        self.freeze_min = 0.3               # 定住超过这么久才压暗去色（短的顿帧不算）
        self.camera_fn = None               # f(真实秒) -> (cx, cy, zoom)；给了就不用关键帧（自动取景之类）
        self.spot_fn = None                 # f(真实秒) -> (x, 亮度 0~1)：从上往下打的主光，跟着人走
        self.haze = False                   # 背景里慢慢飘的雾光

    # —— 时间 ——
    def timemap(self, pts):
        """[(真实秒, 动作秒), ...]，按真实时间递增；相邻两点之间线性"""
        self.tmap = sorted(pts)

    def anim(self, t):
        m = self.tmap
        if t <= m[0][0]:
            return m[0][1] + (t - m[0][0])
        for (r0, a0), (r1, a1) in zip(m, m[1:]):
            if t <= r1:
                return a0 + (a1 - a0) * (t - r0) / (r1 - r0) if r1 > r0 else a1
        return m[-1][1] + (t - m[-1][0])

    def real(self, ta, after=0.0):
        """动作时间 ta 第一次出现的真实时间（after 之后）；定格段取开头"""
        m = self.tmap
        for (r0, a0), (r1, a1) in zip(m, m[1:]):
            if r1 < after:
                continue
            lo, hi = min(a0, a1), max(a0, a1)
            if lo - 1e-9 <= ta <= hi + 1e-9:
                t = r0 if a1 == a0 else r0 + (ta - a0) * (r1 - r0) / (a1 - a0)
                if t >= after - 1e-9:
                    return t
        return m[-1][0] + (ta - m[-1][1])

    # —— 内容 ——
    def add(self, fig):
        self.figures.append(fig)
        return fig

    def camera(self, t, cx, cy, zoom=1.0, ease="inout"):
        self.cam_keys.append((t, cx, cy, zoom, ease, False))

    def cut(self, t, cx, cy, zoom=1.0):
        """硬切：t 之前停在上一个机位，t 起跳到这个机位"""
        self.cam_keys.append((t, cx, cy, zoom, "linear", True))

    def shake(self, t, amp, dur=0.35, anim=False):
        self.shakes.append((self.real(t) if anim else t, amp, dur))

    def burst(self, ta, x, y, kind, real=False, **kw):
        """粒子：spark 火花 / dust 尘土 / ring 冲击环 / flare 局部亮斑。参数见卡 StickScene.tsx"""
        b = {"t": ta, "real": real, "x": x, "y": y, "kind": kind, "seed": 1000 + len(self.bursts) * 7919}
        b.update(kw)
        self.bursts.append(b)

    def sfx(self, ta, kind, gain=1.0, real=False, **args):
        e = {"t": ta, "real": real, "kind": kind, "gain": gain}
        if args:
            e["args"] = args
        self.sfx_events.append(e)

    def impacts(self, fig, ep, min_speed=520, sfx_kind="thud", dust=True, shake=True, gain=1.0):
        """布偶落地：同一下撞击（0.1 秒内）合并成一个事件，按速度给尘土、闷响和震屏"""
        groups = []
        for e in sorted(ep.events):
            if groups and e[0] - groups[-1][-1][0] < 0.1:
                groups[-1].append(e)
            else:
                groups.append([e])
        out = []
        for gr in groups:
            t, x, v, _ = max(gr, key=lambda e: e[2])
            if v < min_speed:
                continue
            k = min(1.0, v / 1600.0)
            if dust:
                self.burst(t, x, GROUND, "dust", n=int(10 + 18 * k), speed=260 * k + 80, angle=-90, spread=170,
                           life=int(18 + 16 * k), size=10 + 10 * k, g=-60, color="#c9cfdb")
            self.sfx(t, sfx_kind, gain * (0.35 + 0.65 * k))
            if shake and k > 0.5:
                self.shake(t, 10 * k, 0.3, anim=True)
            out.append((t, x, v))
        return out

    # —— 物理标注（真实时间；pos 可以是常量，也可以是 f(真实秒) 的函数，逐帧采样） ——
    def _track(self, t0, t1, pos):
        f0, f1 = round(t0 * self.fps), round(t1 * self.fps)
        pts = []
        for f in range(f0, f1 + 1):
            v = pos(f / self.fps) if callable(pos) else pos
            pts.append([round(c, 1) for c in v])
        return f0, f1, pts

    def label(self, t0, t1, x, y, text, size=34, color=None, screen=False, anchor="middle"):
        d = {"f0": round(t0 * self.fps), "f1": round(t1 * self.fps), "x": x, "y": y, "text": text, "size": size,
             "anchor": anchor, "screen": screen}
        if color:
            d["color"] = color
        self.layers["labels"].append(d)

    def arrow(self, t0, t1, pos, color, width=6, grow=8):
        """pos -> (x, y, dx, dy)：箭尾在 (x, y)，箭身是 (dx, dy)"""
        f0, f1, pts = self._track(t0, t1, pos)
        self.layers["arrows"].append({"f0": f0, "f1": f1, "color": color, "width": width, "grow": grow, "pts": pts})

    def dot(self, t0, t1, pos, color, r=9, label=None, lsize=34, lx=22, ly=-22):
        """一个跟着走的光点（比如重心）；label 是挂在它旁边、跟着它走的字"""
        f0, f1, pts = self._track(t0, t1, pos)
        d = {"f0": f0, "f1": f1, "color": color, "r": r, "pts": pts}
        if label:
            d.update(label=label, lsize=lsize, lx=lx, ly=ly)
        self.layers["dots"].append(d)

    def bar(self, t0, t1, pos, color, alt=None, t_alt=None, y=GROUND):
        """地面上的一段（支撑面）：pos -> (x0, x1)；t_alt 起换成 alt 色"""
        f0, f1, pts = self._track(t0, t1, pos)
        self.layers["bars"].append({"f0": f0, "f1": f1, "color": color, "alt": alt or color,
                                    "falt": round(t_alt * self.fps) if t_alt is not None else 10 ** 9,
                                    "y": y, "pts": pts})

    def tri(self, t0, t1, pos, color, size=22):
        f0, f1, pts = self._track(t0, t1, pos)
        self.layers["tris"].append({"f0": f0, "f1": f1, "color": color, "size": size, "pts": pts})

    def flow(self, t0, t1, pos, lines, color):
        """跟着一个点移动的流线：lines 是相对这个点的折线 [[(dx, dy), ...], ...]"""
        f0, f1, pts = self._track(t0, t1, pos)
        self.layers["flows"].append({"f0": f0, "f1": f1, "color": color, "pts": pts,
                                     "lines": [[[round(a, 1), round(b, 1)] for a, b in ln] for ln in lines]})

    def feather(self, pos, color, size=34):
        """pos(真实秒) -> (x, y, 角度) 或 None"""
        n = round(self.total * self.fps)
        p = []
        for f in range(n):
            v = pos(f / self.fps)
            p.append(None if v is None else [round(c, 1) for c in v])
        self.layers["feathers"].append({"color": color, "size": size, "p": p})

    # —— 导出 ——
    def _camera_at(self, t):
        keys = sorted(self.cam_keys) or [(0, 960, 540, 1.0, "linear", False)]
        if self.camera_fn:
            cx, cy, z = self.camera_fn(t)
        elif t <= keys[0][0]:
            cx, cy, z = keys[0][1:4]
        else:
            i = max(j for j in range(len(keys)) if keys[j][0] <= t)
            a = keys[i]
            if i + 1 >= len(keys):
                cx, cy, z = a[1:4]
            else:
                b = keys[i + 1]
                if b[5]:                              # 下一个是硬切：之前一直停在当前机位
                    cx, cy, z = a[1:4]
                else:
                    e = EASE[b[4]]((t - a[0]) / (b[0] - a[0]))
                    cx, cy, z = (a[j] + (b[j] - a[j]) * e for j in (1, 2, 3))
        for ts, amp, dur in self.shakes:
            u = (t - ts) / dur
            if 0 <= u < 1:
                d = amp * (1 - u) ** 2
                cx += d * (math.sin(t * 2 * math.pi * 23 + ts * 7) + 0.5 * math.sin(t * 2 * math.pi * 37 + 1.3))
                cy += d * (math.cos(t * 2 * math.pi * 19 + ts * 3) + 0.5 * math.sin(t * 2 * math.pi * 31 + 0.4))
        return cx, cy, z

    def export(self):
        fps = self.fps
        n = round(self.total * fps)
        ta_end = max(a for _, a in self.tmap) + 1.0
        for fig in self.figures:
            if not fig.segments:
                fig.prepare(fps, ta_end)
        anims = [self.anim(f / fps) for f in range(n)]
        figs = []
        for fig in self.figures:
            js = []
            for f, ta in enumerate(anims):
                own = fig.clock(f / fps) if fig.clock else None
                js.append([round(c, 1) for p in fig.joints(ta if own is None else own) for c in p])
            figs.append({"name": fig.name, "color": fig.color, "core": fig.core, "width": fig.body.width,
                         "headR": fig.body.head_r, "j": js})
        cam = [[round(v, 2) for v in self._camera_at(f / fps)] for f in range(n)]
        # 定格：动作时间停住超过 freeze_min 的帧，画面压暗去色（短的顿帧不算）
        still = [abs(anims[f] - anims[f - 1]) < 1e-9 if f else False for f in range(n)]
        freeze = [0.0] * n
        f = 0
        while f < n:
            if still[f]:
                g = f
                while g < n and still[g]:
                    g += 1
                if (g - f) / fps >= self.freeze_min:
                    for k in range(f, g):
                        freeze[k] = round(min(1.0, (k - f + 1) / 6, (g - k) / 6), 3)
                f = g
            else:
                f += 1
        # 粒子按动作时间走：定格时火花悬在半空，慢镜头里飞得慢。clock = 每帧的动作时间（帧）
        clock = [round(a * fps, 3) for a in anims]
        bursts = []
        for b in self.bursts:
            d = dict(b)
            t = d.pop("t")
            d["f"] = round((self.anim(t) if d.pop("real") else t) * fps, 2)
            bursts.append(d)
        data = {"fps": fps, "frames": n, "offset": 0, "fabs0": 0, "ground": GROUND, "grid": self.grid,
                "trail": self.trail, "reflect": self.reflect, "haze": self.haze, "figures": figs, "camera": cam,
                "freeze": freeze, "clock": clock, "bursts": bursts, **self.layers}
        if self.spot_fn:
            data["spot"] = [[round(v, 3) for v in self.spot_fn(f / fps)] for f in range(n)]
        sfx = []
        for e in self.sfx_events:
            d = {"t": round(e["t"] if e["real"] else self.real(e["t"]), 4), "kind": e["kind"], "gain": e["gain"]}
            if "args" in e:
                d["args"] = e["args"]
            sfx.append(d)
        return data, sorted(sfx, key=lambda e: e["t"])


def slice_data(data, f0, f1, pad=8):
    """切出 [f0, f1) 这一镜要的数据，多带前 pad 帧（光迹、残影要看前几帧）。卡从 offset 那一帧开始画"""
    s0 = max(0, f0 - pad)
    out = {k: v for k, v in data.items() if not isinstance(v, list)}
    out["offset"] = f0 - s0
    out["frames"] = f1 - s0
    out["fabs0"] = s0                                       # 这段第 0 帧在全片的帧号：背景雾按它计时，切镜不跳
    out["figures"] = [dict(fig, j=fig["j"][s0:f1]) for fig in data["figures"]]
    out["camera"] = data["camera"][s0:f1]
    if "spot" in data:
        out["spot"] = data["spot"][s0:f1]
    out["freeze"] = data["freeze"][s0:f1]
    out["clock"] = data["clock"][s0:f1]
    lo, hi = min(out["clock"]), max(out["clock"])          # 粒子按动作时间算年龄，不用平移
    out["bursts"] = [b for b in data["bursts"] if b["f"] + b.get("life", 18) >= lo and b["f"] <= hi]
    for key in ("labels", "arcs"):
        out[key] = [dict(x, f0=x["f0"] - s0, **({"f1": x["f1"] - s0} if x.get("f1") is not None else {}))
                    for x in data.get(key, []) if (x.get("f1") is None or x["f1"] >= s0) and x["f0"] < f1]
    for key in ("arrows", "dots", "bars", "tris", "flows"):
        items = []
        for x in data.get(key, []):
            if x["f1"] < s0 or x["f0"] >= f1:
                continue
            k0 = max(x["f0"], s0)
            d = dict(x, f0=k0 - s0, f1=x["f1"] - s0, pts=x["pts"][k0 - x["f0"]: f1 - x["f0"]])
            if "falt" in x:
                d["falt"] = x["falt"] - s0
            d["age0"] = k0 - x["f0"]          # 切进来时这个标注已经出现了几帧（生长动画接着走）
            items.append(d)
        out[key] = items
    out["paths"] = [dict(p, f0=p["f0"] - s0, f1=p["f1"] - s0, **({"end": p["end"] - s0} if "end" in p else {}))
                    for p in data.get("paths", []) if p["f0"] < f1 and p.get("end", 10 ** 9) >= s0]
    out["ghosts"] = [dict(g, pts=[[a - s0, x, y] for a, x, y in g["pts"] if a < f1]) for g in data.get("ghosts", [])]
    out["balls"] = [dict(b, p=b["p"][s0:f1]) for b in data.get("balls", [])]
    out["feathers"] = [dict(fe, p=fe["p"][s0:f1]) for fe in data.get("feathers", [])]
    out["walls"] = data.get("walls", [])
    return out
