"""无声画面 + 配音 (+ 字幕) → 成片（三种做法共用的最后一步）。

用法（任意目录）:
       uv run vlab-finalize <无声画面.mp4> <项目>/build/<id> <项目>/renders/<id>_final.mp4 [--no-subs]
       画面里已经自带字幕时（比如 HyperFrames 版），加 --no-subs 只合配音。
"""

import json
import subprocess
import sys
from pathlib import Path


def finalize(video: Path, build_dir: Path, out: Path, burn_subs: bool = True) -> None:
    duration = json.loads((build_dir / "timeline.json").read_text(encoding="utf-8"))["duration"]
    out.parent.mkdir(parents=True, exist_ok=True)
    # 在 build 目录里运行，字幕文件用相对路径，省掉 Windows 盘符在滤镜里的转义麻烦
    vf = ["-vf", "subtitles=subs.ass"] if burn_subs else []
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video.resolve()),
        "-i", "narration.wav",
        *vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-af", "pan=stereo|c0=c0|c1=c0",  # 单声道原样复制成左右声道（-ac 2 会乘 0.707），和 HyperFrames 的输出一致
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
