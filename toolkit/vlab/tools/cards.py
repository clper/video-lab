"""镜头卡一览：把卡库里的每张卡按默认参数渲一小段，抽一帧拼成对照表。

用法（任意目录）:
    uv run vlab-cards --out archive/005-emergence/media/cards.png
    uv run vlab-cards --out /tmp/cards.png --only polaroid,maskWipe --seconds 2.5

为什么需要它：卡库是公共资产，但一条片只会用到其中几张（005 用了 11 张）。
剩下的卡坏了不会有人发现，直到下一次要用它。跑一遍就能看到"每张卡长什么样、还在不在"。
"""

import argparse
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vlab.render import remotion_bridge
from vlab.tools.preview import grab

# 有必填参数的卡：给一份示例内容，不然渲出来是空的
SAMPLE = {
    "particleText": {"text": "涌现", "kicker": "EMERGENCE", "sub": "整体有了，个体却没有"},
    "kineticSubtitle": {"text": "你无法从一只鸟，读出整个鸟群。", "highlight": "鸟群"},
}

COLS = 5
CELL_W = 300
PAD = 8
LABEL_H = 26
GRAB_AT = 0.7          # 抽后段：动画基本落位，能看出卡片的稳态样子


def _font():
    try:
        return ImageFont.load_default(size=16)
    except TypeError:                       # 老 Pillow 没有 size 参数
        return ImageFont.load_default()


def _cell(name: str, img: Image.Image, font) -> Image.Image:
    box = Image.new("RGB", (img.width, LABEL_H + img.height), (10, 10, 12))
    draw = ImageDraw.Draw(box)
    draw.text((6, 4), name, fill=(232, 214, 160), font=font)
    box.paste(img, (0, LABEL_H))
    return box


def build(out: Path, seconds: float, only: list[str] | None, width: int = 1080) -> Path:
    names = remotion_bridge.card_names()
    if not names:
        raise SystemExit("卡名解析失败：检查 src/cards/registry.ts")
    if only:
        unknown = [n for n in only if n not in names]
        if unknown:
            raise SystemExit(f"没有这些卡：{', '.join(unknown)}；可选：{', '.join(names)}")
        names = only
    ready, detail = remotion_bridge.node_ready()
    if not ready:
        raise SystemExit(f"Remotion 环境没准备好：{detail}")

    tmp = Path(tempfile.mkdtemp(prefix="vlab_cards_"))
    cells: list[Image.Image] = []
    try:
        for i, name in enumerate(names, 1):
            clip = tmp / f"{name}.mp4"
            print(f"[{i}/{len(names)}] {name}")
            remotion_bridge.render_shot(name, clip, seconds, params=SAMPLE.get(name, {}))
            cells.append(_cell(name, grab(clip, seconds * GRAB_AT, CELL_W), _font()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    rows = (len(cells) + COLS - 1) // COLS
    cell_h = cells[0].height
    sheet = Image.new("RGB", (COLS * (CELL_W + PAD) + PAD, rows * (cell_h + PAD) + PAD), (8, 8, 10))
    for i, cell in enumerate(cells):
        x = PAD + (i % COLS) * (CELL_W + PAD)
        y = PAD + (i // COLS) * (cell_h + PAD)
        sheet.paste(cell, (x, y))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="卡库一览：每张卡渲一段并抽帧拼图")
    ap.add_argument("--out", required=True, help="输出 png")
    ap.add_argument("--seconds", type=float, default=3.2, help="每张卡渲多长（默认 3.2s）")
    ap.add_argument("--only", help="只渲这几张，逗号分隔")
    a = ap.parse_args()
    out = build(Path(a.out), a.seconds, [s.strip() for s in a.only.split(",")] if a.only else None)
    print(f"卡库一览 → {out}")


if __name__ == "__main__":
    main()
