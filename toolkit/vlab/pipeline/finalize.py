"""无声画面 + 配音 (+ 字幕) → 成片（三种做法共用的最后一步）。

用法（任意目录）:
       uv run vlab-finalize <无声画面.mp4> <项目>/build/<id> <项目>/renders/<id>_final.mp4 [--no-subs]
       画面里已经自带字幕时（比如 HyperFrames 版），加 --no-subs 只合配音。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from vlab import fonts


def finalize(video: Path, build_dir: Path, out: Path, burn_subs: bool = True) -> None:
    duration = json.loads((build_dir / "timeline.json").read_text(encoding="utf-8"))["duration"]
    out.parent.mkdir(parents=True, exist_ok=True)
    # 拍格模式（纯音乐 + 字幕）没有配音：这里只烧字幕、不带音轨，音频交给 mix 那一步
    has_voice = (build_dir / "narration.wav").exists()
    # 在 build 目录里运行，字幕文件和字体目录都用相对路径，省掉 Windows 盘符在滤镜里的转义麻烦。
    # fontsdir 指向仓库自带的思源黑体，libass 不再依赖系统装没装字体。
    vf = []
    if burn_subs:
        try:
            fdir = os.path.relpath(fonts.DIR, build_dir).replace("\\", "/")
            vf = ["-vf", f"subtitles=subs.ass:fontsdir={fdir}"]
        except ValueError:          # 不在同一个盘：退回系统字体
            print("提示：build 目录和仓库不在同一个盘，字幕改用系统字体")
            vf = ["-vf", "subtitles=subs.ass"]
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video.resolve()),
        *(["-i", "narration.wav"] if has_voice else []),
        *vf,
        "-map", "0:v:0",
        *(["-map", "1:a:0", "-c:a", "aac", "-b:a", "160k",
           "-af", "pan=stereo|c0=c0|c1=c0"] if has_voice else ["-an"]),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        "-movflags", "+faststart",
        str(out.resolve()),
    ]
    subprocess.run(cmd, check=True, cwd=build_dir)
    print(f"成片 → {out}")


def cli() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 3:
        sys.exit("用法：vlab-finalize <无声画面.mp4> <项目>/build/<id> <输出.mp4> [--no-subs]")
    finalize(Path(args[0]), Path(args[1]), Path(args[2]), burn_subs="--no-subs" not in sys.argv)


if __name__ == "__main__":
    cli()
