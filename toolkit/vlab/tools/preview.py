"""视频 → 抽帧拼图，给人或 AI 快速看画面（"渲染 → 看图 → 改"循环用）。

用法（任意目录）:
    uv run vlab-preview media/videos/scene/960p15/MobiusStrip.mp4 --timeline build/mobius-strip/timeline.json
        有时间轴：默认取每个分镜最后一帧（看每个分镜的最终画面），每格标上时间和分镜名
    uv run vlab-preview renders/xxx_final.mp4 --times 1.5,4.8,9
        指定时间点
    uv run vlab-preview renders/xxx_final.mp4 --every 2
        每隔 2 秒一帧（没有时间轴时的默认方式）

常用参数:
    --scenes end|mid|both   有时间轴时，取每个分镜的结尾、中点，或两者
    --cols 6                每行几格
    --width 270             每格宽度（像素）
    --out 路径               默认写在视频旁边：<视频名>_preview.png（已在 .gitignore 里忽略）
也可以在代码里用：python -m vlab.tools.preview ...
"""

import argparse
import io
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vlab import fonts

FONT_PATHS = [str(fonts.REGULAR), "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]   # 仓库字体优先


def probe_duration(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def grab(video: Path, t: float, width: int) -> Image.Image:
    # 跳到视频最末尾附近时 ffmpeg 偶尔取不到帧：往前退一点重试
    for back in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
        png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t - back):.3f}", "-i", str(video),
                              "-frames:v", "1", "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                             capture_output=True, check=True).stdout
        if png:
            return Image.open(io.BytesIO(png)).convert("RGB")
    raise RuntimeError(f"{t:.2f}s 取不到帧（超出视频长度？）")


def pick_times(args, duration: float) -> list[tuple[float, str]]:
    if args.times:
        return [(float(x), "") for x in args.times.split(",")]
    if args.timeline:
        scenes = json.loads(Path(args.timeline).read_text(encoding="utf-8"))["scenes"]
        out = []
        for s in scenes:
            if args.scenes in ("mid", "both"):
                out.append(((s["start"] + s["end"]) / 2, f"{s['id']} 中"))
            if args.scenes in ("end", "both"):
                # 分镜末尾按帧对齐后会比时间轴短几毫秒，再留 0.15s 余量，免得最后一镜永远取不到帧
                out.append((max(s["start"], min(s["end"] - 0.12, duration - 0.15)), s["id"]))
        return out
    n = int(duration // args.every) + 1
    return [(min(i * args.every + 0.05, duration - 0.1), "") for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description="视频抽帧拼图")
    ap.add_argument("video")
    ap.add_argument("--timeline")
    ap.add_argument("--times", help="逗号分隔的秒数，如 1.5,4.8,9")
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--scenes", choices=["end", "mid", "both"], default="end")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--width", type=int, default=270)
    ap.add_argument("--out")
    args = ap.parse_args()

    video = Path(args.video)
    duration = probe_duration(video)
    times = [(t, label) for t, label in pick_times(args, duration) if 0 <= t < duration]
    tiles = [grab(video, t, args.width) for t, _ in times]

    font_path = next((p for p in FONT_PATHS if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, max(12, args.width // 16)) if font_path else ImageFont.load_default()
    tw, th = tiles[0].size
    cols = min(args.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols - 1) * 4, rows * th + (rows - 1) * 4), (40, 40, 40))
    for i, ((t, label), tile) in enumerate(zip(times, tiles)):
        d = ImageDraw.Draw(tile)
        text = f"{t:.2f}s {label}".strip()
        box = d.textbbox((6, 4), text, font=font)
        d.rectangle([box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 3], fill=(0, 0, 0))
        d.text((6, 4), text, font=font, fill=(255, 230, 120))
        sheet.paste(tile, ((i % cols) * (tw + 4), (i // cols) * (th + 4)))

    out = Path(args.out) if args.out else video.with_name(f"{video.stem}_preview.png")
    sheet.save(out)
    print(f"{len(tiles)} 帧 → {out}")


if __name__ == "__main__":
    main()
