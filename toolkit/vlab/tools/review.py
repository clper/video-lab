"""成片体检：节奏硬指标 + 逐帧质检 + 响度。

两件事：
  1. 节奏体检——镜头数、平均镜长、最长镜、单镜 action beat、同款连镜、组件覆盖。
     这些是"像不像头部 UP 主"的可量化部分，写成数字就不靠感觉了。
  2. 逐帧质检——每个镜头抽首/中/尾三帧，量亮度/对比/边缘密度，专抓"只在某几帧坏掉"的问题。
     （整片抽帧拼图看整体，逐帧质检抓局部，两个都要。）

用法（任意目录）:
    uv run vlab-review archive/005-emergence/project.yaml
    uv run vlab-review <project.yaml> --video renders/xxx.mp4 --loudness
    uv run vlab-review <project.yaml> --no-frames        # 只查节奏

判定规则见 process/STYLE-RHYTHM.md。全部通过退出码 0，有硬指标没过退出码 1。
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
}

# 逐帧质检的判定线（一帧就够用，先抓"黑屏/空屏"这类硬伤）
FRAME_MEAN_MIN = 6.0        # 平均亮度低于此值 = 几乎全黑
FRAME_STD_MIN = 2.5         # 亮度标准差低于此值 = 整帧没内容
EDGE_RATIO_MIN = 0.0035     # 边缘像素占比低于此值 = 缺结构

FX_NAMES = ["handheld", "sweep", "flash", "breathing", "grain", "stardust", "subtitleBar"]


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


def rhythm_report(P: Project, tl: dict) -> tuple[list[dict], list[str]]:
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
        fails.append(f"同款视觉连续 {longest} 个镜头（上限 {HARD['same_run_max']}）")

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
            fails.append(f"[{s['id']}] 只有 {beats} 个 action beat（要求 ≥{HARD['beats_min']}）")
        if d > HARD["shot_max"]:
            fails.append(f"[{s['id']}] 镜头 {d}s 超过 {HARD['shot_max']}s")

    n = len(scenes)
    total = sum(durations)
    avg = total / max(1, n)
    # 镜头数随片长走：13 只是短片兜底。2–6 分钟的片子至少要能填满“每镜 ≤5.2s”
    need = max(HARD["shots_min"], math.ceil(total / HARD["shot_max"]))
    if n < need:
        fails.append(f"镜头数 {n} 少于 {need}（{total:.0f}s 按单镜 ≤{HARD['shot_max']}s 算）")
    if not HARD["dur_min"] <= total <= HARD["dur_max"]:
        fails.append(f"片长 {total:.1f}s 不在 {HARD['dur_min']:.0f}–{HARD['dur_max']:.0f}s（2–6 分钟）内")
    if avg > HARD["shot_avg"]:
        fails.append(f"平均镜长 {avg:.2f}s 超过 {HARD['shot_avg']}s")
    if coverage < HARD["coverage_min"]:
        fails.append(f"公共组件覆盖率 {coverage:.0%} 低于 {HARD['coverage_min']:.0%}")

    print("节奏体检")
    print(f"  镜头数 {n}　总时长 {total:.2f}s　平均 {avg:.2f}s　最长 {max(durations):.2f}s")
    print(f"  零件 {len(components)} 种：{', '.join(sorted(components))}")
    print(f"  公共组件覆盖 {coverage:.0%}　同款最长连镜 {longest}")
    for r in rows:
        print(f"    {r['id']:<4} {r['component']:<14} {r['renderer']:<9} {r['dur']:>5.2f}s  {r['beats']} 拍")

    layers = P.data.get("fx") if isinstance(P.data.get("fx"), dict) else {k: True for k in FX_NAMES}
    enabled = [k for k, v in layers.items() if v is not False]
    # 字幕条由 finalize 烧 ASS 实现（Remotion 里那层会与烧字幕重叠，所以关掉），
    # 只要项目里生成了字幕，就算这一层在——不然硬指标永远数不够 7 层。
    if "subtitleBar" not in enabled and (P.build_dir / "subs.ass").exists():
        enabled.append("subtitleBar（烧字幕）")
    print(f"  全局特效 {len(enabled)} 层：{', '.join(enabled)}")
    if len(enabled) < HARD["fx_layers_min"]:
        fails.append(f"全局特效只有 {len(enabled)} 层（要求 ≥{HARD['fx_layers_min']}）")
    return rows, fails


def frame_metrics(img: Image.Image) -> dict:
    a = np.asarray(img.convert("L"), dtype=np.float32)
    gx = np.abs(np.diff(a, axis=1))
    gy = np.abs(np.diff(a, axis=0))
    edge = ((gx[:-1, :] > 26) | (gy[:, :-1] > 26)).mean() if a.size else 0.0
    return {"mean": float(a.mean()), "std": float(a.std()), "edge": float(edge)}


def frames_report(P: Project, scenes: list[dict], tls: dict, width: int = 200) -> list[str]:
    fails = []
    clip_dir = P.clip_dir()
    print("逐帧质检")
    for s in scenes:
        clip = clip_dir / f"{s['id']}.mp4"
        if not clip.exists():
            fails.append(f"[{s['id']}] 没有渲染产物 {clip.name}")
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
        fails += [f"[{s['id']}] {b}" for b in bad]
    return fails


def measure_loudness(video: Path) -> float | None:
    if not shutil.which("ffmpeg"):
        return None
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-filter_complex",
                        "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    hits = re.findall(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS", r.stderr or "")
    return float(hits[-1]) if hits else None


def main() -> None:
    ap = argparse.ArgumentParser(description="成片体检：节奏 + 逐帧 + 响度")
    ap.add_argument("project", help="project.yaml")
    ap.add_argument("--style")
    ap.add_argument("--video", help="成片路径，默认 renders/<id>_<style>.mp4")
    ap.add_argument("--no-frames", action="store_true", help="跳过逐帧质检")
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
    loud = None
    if args.loudness:
        if not video.exists():
            fails.append(f"没有成片 {video}")
        else:
            loud = measure_loudness(video)
            print("响度")
            if loud is None:
                fails.append("测不到响度（ffmpeg ebur128 没输出）")
            else:
                ok = abs(loud - HARD["loudness_target"]) <= HARD["loudness_tol"]
                print(f"  整合响度 {loud:.1f} LUFS（目标 {HARD['loudness_target']}±{HARD['loudness_tol']}）"
                      + ("" if ok else "  ← 不在范围内"))
                if not ok:
                    fails.append(f"响度 {loud:.1f} LUFS，目标 {HARD['loudness_target']}±{HARD['loudness_tol']}")

    if video.exists():
        print(f"成片 {video.name}　{probe_duration(video):.2f}s")

    if args.json:
        Path(args.json).write_text(json.dumps({"shots": rows, "fails": fails, "loudness": loud},
                                              ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    if fails:
        print(f"[NG] {len(fails)} 项没过：")
        for f in fails:
            print("  - " + f)
        sys.exit(1)
    print("[OK] 硬指标全绿")


if __name__ == "__main__":
    main()
