"""004《为什么没有绿色的恒星》总装：把各段画面按时间轴拼成成片，再混音。

画面来自三处：
    着色器   media/clips/*.mp4          星空 4 镜、太阳与大气 5 镜（各自一个文件）
    文字动效 media/clips/s13_*.mp4       1 镜
    Manim    media/videos/scene/1080p30/ 6 个片段，每个覆盖连续的若干镜头

Manim 片段是按"一段多镜"渲染的，这里不切开，直接按它覆盖的时间范围参与排序。
拼接用帧数而不是秒：n = round(end*fps) - round(start*fps)，避免累积误差。

用法（在 archive/004-green-star 目录里）:
    uv run python build.py            # 缺哪段提示哪段，全齐就拼成片
    uv run python build.py --check    # 只检查片段齐不齐、时长对不对
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build" / "green-star"
TL = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
FPS, W, H = TL["fps"], TL["width"], TL["height"]
SCENES = {s["id"]: s for s in TL["scenes"]}
FF = shutil.which("ffmpeg") or "ffmpeg"

# Manim 的每个场景类覆盖哪些镜头（和 manim/scene.py 里的 ids 一致）
MANIM = {
    "Intro":     ["s03_why"],
    "Temp":      ["s04_temp", "s05_iron", "s06_class", "s07_class2", "s08_gap"],
    "Reveal":    ["s09_wien", "s10_calc"],
    "Sun":       ["s12_peak"],
    "Principle": ["s14_wrong", "s15_curve", "s16_data", "s17_equal", "s18_mix"],
    "Closing":   ["s22_answer", "s23_never"],
}
MANIM_DIR = HERE / "media" / "videos" / "scene" / "1080p30"
CLIPS = HERE / "media" / "clips"


def n_frames(start, end):
    """这一段应有多少帧。用 round 而不是乘除，避免误差累积。"""
    return round(end * FPS) - round(start * FPS)


def pieces():
    """把成片切成有序的若干段：(起, 止, 源文件, 说明)"""
    out = []
    covered = set()
    for cls, ids in MANIM.items():
        start, end = SCENES[ids[0]]["start"], SCENES[ids[-1]]["end"]
        out.append((start, end, MANIM_DIR / f"{cls}.mp4", f"Manim {cls}（{len(ids)} 镜）"))
        covered.update(ids)
    for sid, sc in SCENES.items():
        if sid in covered:
            continue
        out.append((sc["start"], sc["end"], CLIPS / f"{sid}.mp4", f"片段 {sid}"))
    return sorted(out, key=lambda x: x[0])


def probe(path):
    """返回 (帧数, 宽, 高)；文件还在写或读不出来时返回 None，让调用方当成"没准备好"。"""
    r = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error",
                        "-select_streams", "v:0", "-count_frames",
                        "-show_entries", "stream=nb_read_frames,width,height",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)["streams"][0]
        return int(d["nb_read_frames"]), int(d["width"]), int(d["height"])
    except (json.JSONDecodeError, KeyError, IndexError, ValueError):
        return None


def check():
    ok = True
    total = 0
    print(f"成片目标 {TL['duration']:.2f}s / {n_frames(0, TL['duration'])} 帧 / {W}x{H}\n")
    for start, end, src, note in pieces():
        want = n_frames(start, end)
        total += want
        if not src.exists():
            print(f"  ✗ 缺 {note}  需要 {want} 帧  {src.name}")
            ok = False
            continue
        info = probe(src)
        if info is None:
            print(f"  ✗ 读不出 {note}（可能还在渲染）  {src.name}")
            ok = False
            continue
        got, w, h = info
        flag = "✓" if got == want and (w, h) == (W, H) else "✗"
        if flag == "✗":
            ok = False
        extra = "" if got == want else f"  ← 实际 {got} 帧"
        size = "" if (w, h) == (W, H) else f"  ← 实际 {w}x{h}"
        print(f"  {flag} {note:28s} {start:6.2f}–{end:6.2f}s  {want:4d} 帧{extra}{size}")
    print(f"\n合计 {total} 帧，目标 {n_frames(0, TL['duration'])} 帧")
    return ok


def main():
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    if not check():
        sys.exit("\n片段不齐或规格不对，先把上面标 ✗ 的补齐。")

    tmp = HERE / "media" / "_concat"
    tmp.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, (start, end, src, note) in enumerate(pieces()):
        # 统一重编码一遍，保证参数一致，拼接不出问题
        p = tmp / f"{i:02d}.mp4"
        subprocess.run([FF, "-y", "-v", "error", "-i", str(src),
                        "-frames:v", str(n_frames(start, end)),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-an", str(p)], check=True)
        parts.append(p)

    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    silent = HERE / "media" / "silent.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(silent)], check=True)

    renders = HERE / "renders"
    renders.mkdir(exist_ok=True)
    out = renders / "green-star.mp4"

    from vlab.audio import mix
    mix.mux(silent, BUILD / "narration.wav", out, duration=TL["duration"])
    silent.unlink()
    shutil.rmtree(tmp, ignore_errors=True)

    lufs, peak = mix.loudness(out)
    print(f"\n成片 → {out}")
    print(f"响度 {lufs} LUFS，真峰值 {peak} dBTP")


if __name__ == "__main__":
    main()
