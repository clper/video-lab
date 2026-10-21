"""003 结尾：复用 toolkit/vlab/scenes/landscape 的程序化日落湖景（和 research/visual/06 同一份代码），截取一段（有鹿抬头、鱼跃），叠标题。

帧数按 timeline.json 里 outro 分镜精确计算。标题在旁白说到"其实"时淡入。

用法（在 003-sunset-red 目录里）:
    uv run python landscape/render_outro.py              # → media/clips/outro.mp4
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vlab.render.glsl import open_encoder
from vlab.scenes import landscape as ls

PROJ = Path(__file__).resolve().parent.parent

FPS = 30
LANDSCAPE_T0 = 2.6        # 从风景动画的第 2.6 秒开始截：鹿正抬头，随后鱼跃


def main():
    tl = json.loads((PROJ / "build" / "sunset-red" / "timeline.json").read_text(encoding="utf-8"))
    sc = next(s for s in tl["scenes"] if s["id"] == "outro")
    n = round(sc["end"] * FPS) - round(sc["start"] * FPS)
    t_title = next(w["start"] for w in sc["words"] if w["text"].strip() == "其实") - sc["start"]
    print(f"  outro: {n} 帧（{n / FPS:.2f}s），标题在第 {t_title:.2f}s 淡入")

    scene = ls.build_scene()
    font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 60)
    out = PROJ / "media" / "clips" / "outro.mp4"
    enc = open_encoder(out, FPS)
    for i in range(n):
        t = i / FPS
        img = Image.fromarray((ls.render_frame(scene, LANDSCAPE_T0 + t) * 255).astype(np.uint8)).convert("RGBA")
        alpha = min(max((t - t_title) / 0.5, 0.0), 1.0)
        if alpha > 0:
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            text = "同一个原因：瑞利散射"
            x = (img.width - d.textlength(text, font=font)) / 2
            d.text((x + 2, 288 - 30 + 3), text, font=font, fill=(0, 0, 0, int(200 * alpha)))
            d.text((x, 288 - 30), text, font=font, fill=(255, 236, 210, int(255 * alpha)))
            img = Image.alpha_composite(img, layer)
        enc.stdin.write(np.asarray(img.convert("RGB")).tobytes())
        if i % 60 == 0:
            print(f"    outro.mp4: 帧 {i}/{n}")
    enc.stdin.close()
    enc.wait()
    print("  →", out)


if __name__ == "__main__":
    main()
