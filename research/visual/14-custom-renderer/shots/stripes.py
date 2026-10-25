"""示例：renderer: custom 的镜头脚本。

约定（由 vlab-build 在渲染该镜头时调用）：
    python shots/stripes.py --scene <临时 json> [额外 args…]

`--scene` 里的字段：
    out     要写出的 mp4（绝对路径），必须写出这个文件
    frames  帧数（和帧数校验用同一套算法算出来的，别自己再按秒数取整）
    fps     帧率
    width / height   画布尺寸
    seconds / start / end   在整片时间轴上的位置
    params  project.yaml 里该镜头的 params
    words   这一镜的配音词表 [{text, start, end}…]，可用来对齐画面

一镜一个脚本，写得像"一次性镜头"就对了；一旦它开始被反复复制，说明该抽成
toolkit/vlab 里的镜头卡或 manim 模板。
"""

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (8, 10, 20)
GOLD = (212, 175, 120)
CYAN = (96, 200, 210)
INK = (240, 240, 245)


def _font(size: int):
    for name in ("SourceHanSansCN-Bold.otf", "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def frame_image(i: int, total: int, w: int, h: int, text: str) -> Image.Image:
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    # 斜向条带：位置随帧推进，颜色在两色之间摆动
    for k in range(-h, w + h, 90):
        x = k + (i / max(1, total)) * 180
        shade = 0.5 + 0.5 * math.sin((i * 0.06) + k * 0.01)
        col = tuple(int(BG[c] + (GOLD[c] - BG[c]) * 0.35 * shade) for c in range(3))
        draw.polygon([(x, 0), (x + 46, 0), (x + 46 - h * 0.4, h), (x - h * 0.4, h)], fill=col)
    # 中心标题 + 帧号：自定义镜头也要有可核对的信息，不然只是花纹
    f_title = _font(96)
    f_meta = _font(34)
    tw = draw.textlength(text, font=f_title)
    draw.text(((w - tw) / 2, h * 0.42), text, font=f_title, fill=INK)
    meta = f"frame {i:03d}/{total - 1:03d}"
    mw = draw.textlength(meta, font=f_meta)
    draw.text(((w - mw) / 2, h * 0.42 + 140), meta, font=f_meta, fill=CYAN)
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, help="vlab-build 传进来的场景 JSON")
    args, _ = ap.parse_known_args()

    spec = json.loads(Path(args.scene).read_text(encoding="utf-8"))
    out = Path(spec["out"])
    frames, fps = int(spec["frames"]), int(spec["fps"])
    w, h = int(spec["width"]), int(spec["height"])
    text = (spec.get("params") or {}).get("text", "CUSTOM")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="custom_shot_") as tmp:
        for i in range(frames):
            frame_image(i, frames, w, h, text).save(Path(tmp) / f"{i:05d}.png")
        # 帧序号连续，用 -framerate 精确控制时长；像素格式和拼接环节一致
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(Path(tmp) / "%05d.png"),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-r", str(fps), str(out)], check=True)
    print(f"custom 镜头写好了：{out.name}（{frames} 帧）")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                      # noqa: BLE001 - 脚本失败要让 build 看到非 0 退出码
        print(f"custom 镜头渲染失败：{e}", file=sys.stderr)
        sys.exit(1)
