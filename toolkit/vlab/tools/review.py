"""成片体检：节奏硬指标 + 逐帧质检 + 响度。

两件事：
  1. 节奏体检——镜头数、平均镜长、最长镜、单镜 action beat、同款连镜、组件覆盖。
     这些是"像不像头部 UP 主"的可量化部分，写成数字就不靠感觉了。
  2. 逐帧质检——每个镜头抽首/中/尾三帧，量亮度/对比/边缘密度，专抓"只在某几帧坏掉"的问题。
     （整片抽帧拼图看整体，逐帧质检抓局部，两个都要。）

  3. 画面运动量——motion 基线（灰度逐帧差均值）、每 10 秒段、静止段、无主体段（STYLE-IMPACT 规矩 3）。

用法（任意目录）:
    uv run vlab-review archive/005-emergence/project.yaml
    uv run vlab-review <project.yaml> --video renders/xxx.mp4 --loudness
    uv run vlab-review <project.yaml> --no-frames --no-motion   # 只查节奏

判定规则见 process/STYLE-RHYTHM.md 和 STYLE-IMPACT.md。全部通过（或没过的都写了破例理由）退出码 0，否则 1。

破例：观感优先、有意破了某条硬指标的，在 project.yaml 里写明理由，体检照样列出来，但不算没过：
    review:
      waive:
        same_run: 全片是一场连续的打斗……          # 整条破例：key → 理由
        shot_max: {S19: 冲锋一气呵成……}            # 按镜头破例：key → {镜头: 理由}
key 见下面 HARD 旁边的注释（duration / shots_min / shot_max / shot_avg / beats / same_run / coverage / fx_layers /
frames / loudness / motion / motion_10s / still / empty）。
"""

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from vlab.tools.preview import grab, probe_duration
from vlab.videokit.project import Project, _code_hash  # noqa: F401  (保持与 build 同一份指纹实现)

# 硬指标（写死在这里，也是 process/STYLE-RHYTHM.md 里那张表的唯一来源）
HARD = {
    # 片长区间：2–6 分钟。质量优先，但两头都封口 —— 太短说不透，太长观众跟不上
    "dur_min": 120.0,
    "dur_max": 360.0,
    "shots_min": 13,          # 镜头数下限（短片的兜底；长片按片长反算，见下）
    "shot_max": 5.2,          # 单镜最长（秒）
    "shot_avg": 4.5,          # 平均镜长上限（秒）
    "beats_min": 2,           # 单镜 action beat 下限
    "same_run_max": 2,        # 同款视觉最多连续几个镜头
    "coverage_min": 0.80,     # 来自公共镜头卡/模板的镜头占比
    "fx_layers_min": 7,       # 全局特效层数
    "loudness_target": -14.0,  # 整片整合响度 LUFS
    "loudness_tol": 1.0,
    # 画面运动量（STYLE-IMPACT 规矩 3）：灰度逐帧差的均值（0–255，短边缩到 270 像素量）
    "motion_min": 1.5,        # 全片
    "motion_10s_min": 1.0,    # 任意 10 秒段
    "still_max": 2.0,         # 连续"几乎不动"（逐帧差 < MOTION_STILL）最长几秒
    "empty_max": 2.0,         # 连续"无主体"（几乎全黑 / 整帧没内容 / 缺结构）最长几秒
}
MOTION_STILL = 0.15
# 没过的项的 key（破例按它对上）：
#   duration 片长  shots_min 镜头数  shot_max 单镜最长（按镜头）  shot_avg 平均镜长  beats 动作数（按镜头）
#   same_run 同款连镜  coverage 公共组件覆盖  fx_layers 特效层数  frames 逐帧质检（按镜头）  loudness 响度
#   motion 全片运动量  motion_10s 10 秒段运动量  still 静止段  empty 无主体段

# 逐帧质检的判定线（一帧就够用，先抓"黑屏/空屏"这类硬伤）
FRAME_MEAN_MIN = 6.0        # 平均亮度低于此值 = 几乎全黑
FRAME_STD_MIN = 2.5         # 亮度标准差低于此值 = 整帧没内容
EDGE_RATIO_MIN = 0.0035     # 边缘像素占比低于此值 = 缺结构

FX_NAMES = ["handheld", "sweep", "flash", "breathing", "grain", "stardust", "subtitleBar"]


def _fail(key: str, msg: str, sid: str | None = None) -> dict:
    return {"key": key, "sid": sid, "msg": msg}


def split_waived(fails: list[dict], waive: dict | None) -> tuple[list[dict], list[dict]]:
    """按 project.yaml 的 review.waive 分出"写了理由的破例"和"真没过"。
    waive 的值是理由（整条破例）或 {镜头: 理由}（只对这几个镜头破例）。"""
    hard, waived = [], []
    for f in fails:
        w = (waive or {}).get(f["key"])
        why = w.get(f["sid"]) if isinstance(w, dict) else w
        if why:
            waived.append({**f, "why": str(why).strip()})
        else:
            hard.append(f)
    return hard, waived


def component_of(scene: dict) -> str:
    """一个镜头用的"零件"名：卡片 / 模板 / 着色器。custom 镜头可以用 component 申报它画画用的公共卡。"""
    return str(scene.get("component") or scene.get("card") or scene.get("template")
               or Path(scene.get("frag", "")).name or "?")


def is_public(scene: dict) -> bool:
    """是否来自公共镜头库（toolkit 里的卡片/模板），而不是项目里一次性的代码。
    custom 镜头申报了 component、而且那张卡确实登记在公共卡库里，才算公共组件。"""
    if scene.get("renderer") == "glsl":
        return True
    if scene.get("component"):
        from vlab.videokit.project import remotion_cards
        return scene["component"] in remotion_cards()
    return bool(scene.get("card") or scene.get("template"))


def beat_count(scene: dict) -> int:
    """action beat：一个镜头里"有动作发生"的次数。
    manim 模板靠 cues 被动计数；remotion 卡片的动作在组件内部，由作者用 beats 字段申报。"""
    if "beats" in scene:
        return max(1, int(scene["beats"]))
    return 1 + len(scene.get("cues") or {})


def rhythm_report(P: Project, tl: dict, quiet: bool = False) -> tuple[list[dict], list[dict]]:
    say = (lambda *a: None) if quiet else print
    scenes = P.scenes
    tls = {s["id"]: s for s in tl["scenes"]}
    rows, fails = [], []

    durations = []
    for s in scenes:
        t = tls[s["id"]]
        durations.append(round(t["end"] - t["start"], 2))

    # 同款连镜：连续几个镜头用同一个零件
    runs, cur, prev, longest = [], 0, None, 0
    for s in scenes:
        c = component_of(s)
        if c == prev:
            cur += 1
        else:
            cur = 1
            prev = c
        longest = max(longest, cur)
    if longest > HARD["same_run_max"]:
        fails.append(_fail("same_run", f"同款视觉连续 {longest} 个镜头（上限 {HARD['same_run_max']}）"))

    covered = sum(1 for s in scenes if is_public(s))
    coverage = covered / max(1, len(scenes))
    components = {component_of(s) for s in scenes}

    for s, d in zip(scenes, durations):
        beats = beat_count(s)
        rows.append({
            "id": s["id"],
            "component": component_of(s),
            "renderer": s.get("renderer", "manim"),
            "dur": d,
            "beats": beats,
        })
        if beats < HARD["beats_min"]:
            fails.append(_fail("beats", f"[{s['id']}] 只有 {beats} 个 action beat（要求 ≥{HARD['beats_min']}）", s["id"]))
        if d > HARD["shot_max"]:
            fails.append(_fail("shot_max", f"[{s['id']}] 镜头 {d}s 超过 {HARD['shot_max']}s", s["id"]))

    n = len(scenes)
    total = sum(durations)
    avg = total / max(1, n)
    # 镜头数随片长走：13 只是短片兜底。2–6 分钟的片子至少要能填满“每镜 ≤5.2s”
    need = max(HARD["shots_min"], math.ceil(total / HARD["shot_max"]))
    if n < need:
        fails.append(_fail("shots_min", f"镜头数 {n} 少于 {need}（{total:.0f}s 按单镜 ≤{HARD['shot_max']}s 算）"))
    if not HARD["dur_min"] <= total <= HARD["dur_max"]:
        fails.append(_fail("duration", f"片长 {total:.1f}s 不在 {HARD['dur_min']:.0f}–{HARD['dur_max']:.0f}s（2–6 分钟）内"))
    if avg > HARD["shot_avg"]:
        fails.append(_fail("shot_avg", f"平均镜长 {avg:.2f}s 超过 {HARD['shot_avg']}s"))
    if coverage < HARD["coverage_min"]:
        fails.append(_fail("coverage", f"公共组件覆盖率 {coverage:.0%} 低于 {HARD['coverage_min']:.0%}"))

    say("节奏体检")
    say(f"  镜头数 {n}　总时长 {total:.2f}s　平均 {avg:.2f}s　最长 {max(durations):.2f}s")
    say(f"  零件 {len(components)} 种：{', '.join(sorted(components))}")
    say(f"  公共组件覆盖 {coverage:.0%}　同款最长连镜 {longest}")
    for r in rows:
        say(f"    {r['id']:<4} {r['component']:<14} {r['renderer']:<9} {r['dur']:>5.2f}s  {r['beats']} 拍")

    layers = P.data.get("fx") if isinstance(P.data.get("fx"), dict) else {k: True for k in FX_NAMES}
    enabled = [k for k, v in layers.items() if v is not False]
    # 字幕条由 finalize 烧 ASS 实现（Remotion 里那层会与烧字幕重叠，所以关掉），
    # 只要项目里生成了字幕，就算这一层在——不然硬指标永远数不够 7 层。
    if "subtitleBar" not in enabled and (P.build_dir / "subs.ass").exists():
        enabled.append("subtitleBar（烧字幕）")
    say(f"  全局特效 {len(enabled)} 层：{', '.join(enabled)}")
    if len(enabled) < HARD["fx_layers_min"]:
        fails.append(_fail("fx_layers", f"全局特效只有 {len(enabled)} 层（要求 ≥{HARD['fx_layers_min']}）"))
    return rows, fails


def frame_metrics(img: Image.Image) -> dict:
    a = np.asarray(img.convert("L"), dtype=np.float32)
    gx = np.abs(np.diff(a, axis=1))
    gy = np.abs(np.diff(a, axis=0))
    edge = ((gx[:-1, :] > 26) | (gy[:, :-1] > 26)).mean() if a.size else 0.0
    return {"mean": float(a.mean()), "std": float(a.std()), "edge": float(edge)}


def frames_report(P: Project, scenes: list[dict], tls: dict, width: int = 200) -> list[dict]:
    fails = []
    clip_dir = P.clip_dir()
    print("逐帧质检")
    for s in scenes:
        clip = clip_dir / f"{s['id']}.mp4"
        if not clip.exists():
            fails.append(_fail("frames", f"[{s['id']}] 没有渲染产物 {clip.name}", s["id"]))
            continue
        t = tls[s["id"]]
        # 镜头片段自己的时间从 0 开始（不是整片时间轴上的 start），跨度取片段实际长度
        span = probe_duration(clip)
        marks = [("首", 0.10), ("中", 0.5), ("尾", 0.94)]   # 首帧不取 0：镜头都是从暗场/空场进来的
        cells, bad = [], []
        for name, frac in marks:
            img = grab(clip, span * frac, width)
            m = frame_metrics(img)
            cells.append(f"{name} 亮{m['mean']:.0f} 差{m['std']:.1f} 边{m['edge']:.3f}")
            if m["mean"] < FRAME_MEAN_MIN:
                bad.append(f"{name}帧几乎全黑（亮度 {m['mean']:.1f}）")
            elif m["std"] < FRAME_STD_MIN:
                bad.append(f"{name}帧整帧无内容（标准差 {m['std']:.1f}）")
            elif m["edge"] < EDGE_RATIO_MIN:
                bad.append(f"{name}帧缺结构（边缘占比 {m['edge']:.4f}）")
        print(f"    {s['id']:<4} " + " | ".join(cells) + ("   ← " + "；".join(bad) if bad else ""))
        fails += [_fail("frames", f"[{s['id']}] {b}", s["id"]) for b in bad]
    return fails


def measure_loudness(video: Path) -> float | None:
    if not shutil.which("ffmpeg"):
        return None
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-filter_complex",
                        "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    hits = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", r.stderr or "")
    return float(hits[-1]) if hits else None


def motion_stats(video: Path, seg: float = 10.0) -> dict:
    """画面运动量：灰度逐帧差的均值（0–255，短边缩到 270 像素量），按帧流式读，长片也不占内存。
    返回全片均值、每 seg 秒段的均值、最长静止段和最长无主体段（秒, 结束时刻）。"""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,avg_frame_rate", "-of", "json", str(video)],
                         capture_output=True, text=True, check=True)
    st = json.loads(out.stdout)["streams"][0]
    w, h = (480, 270) if st["width"] >= st["height"] else (270, 480)
    fps = 0.0
    for key in ("r_frame_rate", "avg_frame_rate"):      # 读不出帧率时 ffprobe 给 "0/0"
        num, _, den = (st.get(key) or "0/0").partition("/")
        if float(num or 0) > 0 and float(den or 1) > 0:
            fps = float(num) / float(den or 1)
            break
    if fps <= 0:
        raise RuntimeError(f"读不出 {video.name} 的帧率：{st}")
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h},format=gray",
                             "-f", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    size, every = w * h, max(1, round(fps / 2))        # 无主体每 0.5 秒看一帧，用逐帧质检同一套判据
    diffs, empty, prev, i = [], [], None, 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            f = np.frombuffer(buf, np.uint8).reshape(h, w).astype(np.int16)
            diffs.append(0.0 if prev is None else float(np.abs(f - prev).mean()))   # d[i] = 第 i 帧和上一帧的差
            if i % every == 0:
                m = frame_metrics(Image.fromarray(f.astype(np.uint8)).resize((200 if w > h else 113, 113 if w > h else 200)))
                empty.append(m["mean"] < FRAME_MEAN_MIN or m["std"] < FRAME_STD_MIN or m["edge"] < EDGE_RATIO_MIN)
            prev, i = f, i + 1
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not diffs:              # 解码中途出错的话，不能拿半截片子的数报告
            raise RuntimeError(f"解码 {video.name} 失败：{err[-500:]}")
    finally:
        if proc.poll() is None:
            proc.kill()
    d = np.asarray(diffs)
    n = max(1, round(seg * fps))
    segs = [float(d[a:a + n].mean()) for a in range(0, len(d), n) if len(d[a:a + n]) >= n / 2]

    def longest(flags, step):
        best, cur, end = 0, 0, 0
        for k, f in enumerate(flags):
            cur = cur + 1 if f else 0
            if cur > best:
                best, end = cur, k
        return best * step, (end + 1) * step

    return {"avg": float(d[1:].mean()) if len(d) > 1 else 0.0, "segments": segs, "seg": seg, "fps": fps,
            "still_max": longest(d < MOTION_STILL, 1.0 / fps), "empty_max": longest(empty, every / fps)}


def motion_fails(m: dict) -> list[dict]:
    """motion_stats 的结果 → 没过的项。10 秒段每段单独一条（sid 是 "60–70s"），破例可以按段写，
    整条 key 写理由的话所有段都算破例。"""
    fails = []
    if m["avg"] < HARD["motion_min"]:
        fails.append(_fail("motion", f"motion 基线 {m['avg']:.2f}，要求 ≥{HARD['motion_min']}"))
    seg = int(m.get("seg", 10))
    for k, v in enumerate(m["segments"]):
        if v < HARD["motion_10s_min"]:
            sid = f"{k * seg}–{k * seg + seg}s"
            fails.append(_fail("motion_10s", f"{sid} 段 motion {v:.2f}，要求 ≥{HARD['motion_10s_min']}", sid))
    if m["still_max"][0] >= HARD["still_max"]:
        fails.append(_fail("still", f"画面静止 {m['still_max'][0]:.1f}s（到 {m['still_max'][1]:.1f}s），上限 {HARD['still_max']}s"))
    if m["empty_max"][0] >= HARD["empty_max"]:
        fails.append(_fail("empty", f"画面无主体 {m['empty_max'][0]:.1f}s（到 {m['empty_max'][1]:.1f}s），上限 {HARD['empty_max']}s"))
    return fails


def motion_report(video: Path) -> tuple[dict, list[dict]]:
    m = motion_stats(video)
    print("画面运动量（STYLE-IMPACT 规矩 3）")
    print(f"  全片 {m['avg']:.2f}（要求 ≥{HARD['motion_min']}）")
    print("  每 10 秒段 " + " ".join(f"{v:.2f}" for v in m["segments"]))
    print(f"  最长静止 {m['still_max'][0]:.2f}s（到 {m['still_max'][1]:.1f}s）　"
          f"最长无主体 {m['empty_max'][0]:.1f}s（到 {m['empty_max'][1]:.1f}s）")
    return m, motion_fails(m)


def main() -> None:
    ap = argparse.ArgumentParser(description="成片体检：节奏 + 逐帧 + 运动量 + 响度")
    ap.add_argument("project", help="project.yaml")
    ap.add_argument("--style")
    ap.add_argument("--video", help="成片路径，默认 renders/<id>_<style>.mp4")
    ap.add_argument("--no-frames", action="store_true", help="跳过逐帧质检")
    ap.add_argument("--no-motion", action="store_true", help="跳过画面运动量（要整片解码一遍，120 秒的片子约十几秒）")
    ap.add_argument("--loudness", action="store_true", help="测整片整合响度（-14 LUFS）")
    ap.add_argument("--json")
    args = ap.parse_args()

    P = Project(args.project, args.style)
    tl_path = P.timeline_path
    if not tl_path.exists():
        sys.exit(f"没有 {tl_path}：先跑 uv run vlab-build {args.project}（会先生成配音与时间轴）")
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    tls = {s["id"]: s for s in tl["scenes"]}

    rows, fails = rhythm_report(P, tl)
    if not args.no_frames:
        fails += frames_report(P, P.scenes, tls)

    video = Path(args.video) if args.video else P.dir / "renders" / f"{P.id}_{P.style['name']}.mp4"
    motion = None
    if not args.no_motion:
        if video.exists():
            motion, more = motion_report(video)
            fails += more
        elif args.video:
            fails.append(_fail("motion", f"没有成片 {video}，量不了画面运动量"))
        else:                  # archive / research 的成片不入库：没拼过就只查节奏和逐帧，不算没过
            print(f"画面运动量：没有成片 {video.name}，跳过（先 vlab-build 拼出成片再查）")
    loud = None
    if args.loudness:
        if not video.exists():
            fails.append(_fail("loudness", f"没有成片 {video}"))
        else:
            loud = measure_loudness(video)
            print("响度")
            if loud is None:
                fails.append(_fail("loudness", "测不到响度（ffmpeg ebur128 没输出）"))
            else:
                ok = abs(loud - HARD["loudness_target"]) <= HARD["loudness_tol"]
                print(f"  整合响度 {loud:.1f} LUFS（目标 {HARD['loudness_target']}±{HARD['loudness_tol']}）"
                      + ("" if ok else "  ← 不在范围内"))
                if not ok:
                    fails.append(_fail("loudness", f"响度 {loud:.1f} LUFS，目标 {HARD['loudness_target']}±{HARD['loudness_tol']}"))

    if video.exists():
        print(f"成片 {video.name}　{probe_duration(video):.2f}s")

    review_cfg = P.data.get("review") if isinstance(P.data.get("review"), dict) else {}
    fails, waived = split_waived(fails, review_cfg.get("waive"))
    if args.json:
        Path(args.json).write_text(json.dumps({"shots": rows, "fails": [f["msg"] for f in fails],
                                               "waived": [{"msg": f["msg"], "why": f["why"]} for f in waived],
                                               "loudness": loud, "motion": motion},
                                              ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    if waived:
        print(f"[破例] {len(waived)} 项没过、但写了理由（project.yaml 的 review.waive）：")
        for f in waived:
            print(f"  - {f['msg']}")
            print(f"      理由：{f['why']}")
    if fails:
        print(f"[NG] {len(fails)} 项没过：")
        for f in fails:
            print("  - " + f["msg"])
        sys.exit(1)
    print("[OK] 硬指标全绿" + ("（含写明理由的破例）" if waived else ""))


if __name__ == "__main__":
    main()
