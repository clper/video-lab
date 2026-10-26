"""003《夕阳为什么是红的》总装：渲染各段 → 校验帧数 → 拼接 → 合配音和字幕。

多技术混剪，每个分镜用最合适的技术，各段帧数都按 timeline.json 精确计算：
    hook                          着色器：云海飞越雪山      shader/render_clips.py
    white, molecule, scatter, ratio  Manim：Physics          manim/scene.py
    noon                          着色器：大气散射（中午）  shader/render_clips.py
    path, lose_blue               Manim：SunsetPath          manim/scene.py
    sunset                        着色器：大气散射（日落）  shader/render_clips.py
    outro                         程序化风景（vlab.scenes） landscape/render_outro.py

用法（在 003-sunset-red 目录里）:
    uv run vlab-tts content/sunset.json                  # 改了稿子才需要重跑
    uv run python build.py                               # 缺哪段渲染哪段，然后拼接成片
    uv run python build.py --force                       # 全部重新渲染
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent
TL = json.loads((PROJ / "build" / "sunset-red" / "timeline.json").read_text(encoding="utf-8"))
SC = {s["id"]: s for s in TL["scenes"]}
FPS = 30
CLIPS = PROJ / "media" / "clips"
MANIM_OUT = PROJ / "media" / "videos" / "scene" / "1920p30"

# 拼接顺序：(片段文件, 覆盖的首尾分镜, 怎么渲染)
SEGMENTS = [
    (CLIPS / "hook.mp4", ("hook", "hook"), ["shader/render_clips.py", "--only", "hook"]),
    (MANIM_OUT / "Physics.mp4", ("white", "ratio"), ["-m", "manim", "render", "manim/scene.py", "Physics", "--format", "mp4"]),
    (CLIPS / "noon.mp4", ("noon", "noon"), ["shader/render_clips.py", "--only", "noon"]),
    (MANIM_OUT / "SunsetPath.mp4", ("path", "lose_blue"), ["-m", "manim", "render", "manim/scene.py", "SunsetPath", "--format", "mp4"]),
    (CLIPS / "sunset.mp4", ("sunset", "sunset"), ["shader/render_clips.py", "--only", "sunset"]),
    (CLIPS / "outro.mp4", ("outro", "outro"), ["landscape/render_outro.py"]),
]


def frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0",
                          "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return int(out.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="全部重新渲染")
    args = ap.parse_args()

    for clip, (a, b), cmd in SEGMENTS:
        if args.force or not clip.exists():
            print(f"渲染 {clip.name} …")
            subprocess.run([sys.executable, *cmd], cwd=PROJ, check=True)

    print("校验帧数：")
    ok = True
    for clip, (a, b), _ in SEGMENTS:
        want = round(SC[b]["end"] * FPS) - round(SC[a]["start"] * FPS)
        got = frames(clip)
        flag = "✓" if got == want else "✗"
        ok &= got == want
        print(f"  {flag} {clip.name:<16} {got} 帧（应为 {want}，分镜 {a}–{b}）")
    if not ok:
        sys.exit("帧数不对，先修正再拼接（否则画面会和配音错位）")

    lst = PROJ / "media" / "concat.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c, _, _ in SEGMENTS), encoding="utf-8")
    silent = PROJ / "media" / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    str(silent)], check=True)
    print(f"无声画面：{frames(silent)} 帧（配音 {TL['duration']}s ≈ {round(TL['duration'] * FPS)} 帧）")

    final = PROJ / "renders" / "sunset-red_final.mp4"
    subprocess.run([sys.executable, "-m", "vlab.pipeline.finalize", str(silent),
                    str(PROJ / "build" / "sunset-red"), str(final)], check=True)
    silent.unlink()                      # 无声中间文件只是合配音前的过渡，用完就删


if __name__ == "__main__":
    main()
