"""A/B 对比：几条成片按同一组时间点抽帧，拼成一张对照图，横着看差距。

用法（任意目录）:
    uv run vlab-ab videos/002-mobius-strip/renders/mobius-strip_final.mp4 \
        videos/003-sunset-red/renders/sunset-red_final.mp4 \
        videos/005-emergence/renders/005-emergence_emergent.mp4 \
        --out videos/005-emergence/media/ab_002_003_005.png

为什么按"片长百分比"而不是绝对秒数：几条片子时长不一样，用绝对秒数会各看各的；
用 15%/50%/85% 取的是每条片的开/中/收，才是同一个叙事位置之间的比较。

每条片一行，同列是同一叙事位置。看图时问三个问题：暗部有没有层次、元素密度差多少、
信息量（字/图/读数）是不是同一档。数值上的差距仍然交给 vlab-review。
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vlab.tools.preview import grab, probe_duration

CELL_W = 360                      # 单帧宽度（高度按 9:16 自动算）
PAD = 8
LABEL_H = 30
DEFAULT_FRACS = "0.15,0.5,0.85"
STEADY_STEPS = (-0.18, 0.0, 0.18)   # 抽帧容位：避开切点那一两帧白闪


def _steady(video: Path, t: float, width: int) -> Image.Image:
    """在目标时刻附近取三帧，挑亮度居中的那帧。

    每个镜头开头都有两帧快门闪，正好抽在切点上会得到一整帧灰白 —— 那不是画面本身，
    拿它去对比会让人以为渲染坏了。取三帧的中位数是不靠猜测的避让方式。
    """
    frames = [grab(video, max(0.0, t + dt), width) for dt in STEADY_STEPS]
    means = [float(np.asarray(f.convert("L")).mean()) for f in frames]
    return frames[int(np.argsort(means)[len(means) // 2])]


def _label(text: str, width: int) -> Image.Image:
    bar = Image.new("RGB", (width, LABEL_H), (12, 12, 16))
    draw = ImageDraw.Draw(bar)
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:                      # 老 Pillow 没有 size 参数
        font = ImageFont.load_default()
    draw.text((8, 6), text, fill=(232, 214, 160), font=font)
    return bar


def build(videos: list[Path], out: Path, fracs: list[float], cell_w: int = CELL_W) -> Path:
    rows: list[list[Image.Image]] = []
    labels: list[str] = []
    for video in videos:
        dur = probe_duration(video)
        if dur <= 0:
            raise SystemExit(f"读不到时长：{video}")
        rows.append([_steady(video, dur * f, cell_w) for f in fracs])
        labels.append(f"{video.parent.parent.name}/{video.name}  {dur:.1f}s")

    cell_h = rows[0][0].height
    cols = len(fracs)
    width = PAD + cols * (cell_w + PAD)
    height = PAD + len(rows) * (LABEL_H + cell_h + PAD)
    sheet = Image.new("RGB", (width, height), (8, 8, 10))
    y = PAD
    for label, row in zip(labels, rows):
        sheet.paste(_label(label, width - 2 * PAD), (PAD, y))
        y += LABEL_H
        x = PAD
        for img in row:
            sheet.paste(img, (x, y))
            x += cell_w + PAD
        y += cell_h + PAD
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="几条成片并排 A/B 对比")
    ap.add_argument("videos", nargs="+", help="成片路径，一行一条")
    ap.add_argument("--out", required=True, help="输出 png")
    ap.add_argument("--fracs", default=DEFAULT_FRACS, help="抽帧位置，按片长百分比，如 0.15,0.5,0.85")
    ap.add_argument("--width", type=int, default=CELL_W, help="单帧像素宽度")
    a = ap.parse_args()
    fracs = [float(x) for x in a.fracs.split(",")]
    out = build([Path(v) for v in a.videos], Path(a.out), fracs, a.width)
    print(f"对照图 → {out}")


if __name__ == "__main__":
    main()
