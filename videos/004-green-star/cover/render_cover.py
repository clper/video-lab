"""004《为什么没有绿色的恒星》封面：16:9 和 4:3 两个比例。

构图：星空打底（starfield.frag），左边一颗带绿色光环的白太阳（sun.frag，正是全片的反转点：
峰值在绿色，看起来却是白的），右边大字标题，"绿色"两个字染成绿色。
字体是仓库自带的思源黑体（vlab.fonts）。缩略图很小，所以字要大、最多三行。

用法:
    uv run python videos/004-green-star/cover/render_cover.py
产物：renders/cover-16x9.png（1920x1080）、renders/cover-4x3.png（1440x1080）
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from vlab import fonts
from vlab.render.glsl import ShaderRenderer
from vlab.scenes import SHADERS

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "renders"

INK = (244, 246, 252)
DIM = (160, 168, 194)
GREEN = (110, 236, 150)
GOLD = (255, 208, 105)


def background(w, h, sun_x, sun_r):
    """星空和太阳各渲一帧，按"取亮"叠在一起：太阳着色器的底色接近黑，取亮不会盖住星星。"""
    stars = ShaderRenderer(SHADERS / "starfield.frag", ss=2, size=(w, h))
    sun = ShaderRenderer(SHADERS / "sun.frag", ss=2, size=(w, h))
    a = stars.frame(2.0, uDrift=0.0, uZoom=1.0, uDim=0.25, uGreenTry=0.0, uTwinkle=0.0)
    b = sun.frame(4.0, uTemp=5772.0, uRadius=sun_r, uGround=0.0, uGlow=0.55, uBright=1.0,
                  uGreenRing=0.95, uCenter=(sun_x, 0.0))
    return Image.fromarray(np.maximum(a, b))


def text_with_shadow(img, xy, parts, size, bold=True):
    """一行多色文字：parts = [(文字, 颜色), ...]，左对齐从 xy 开始。下面垫一层模糊阴影保证缩略图上也清楚。"""
    f = fonts.pil(size, bold)
    shadow = Image.new("L", img.size, 0)
    sd = ImageDraw.Draw(shadow)
    x, y = xy
    for s, _ in parts:
        sd.text((x + 4, y + 6), s, font=f, fill=255)
        x += f.getlength(s)
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.12))
    img.paste((0, 0, 0), (0, 0), shadow.point(lambda v: int(v * 0.8)))
    d = ImageDraw.Draw(img)
    x, y = xy
    for s, col in parts:
        d.text((x, y), s, font=f, fill=col)
        x += f.getlength(s)
    return x


def cover(w, h, out):
    aspect = w / h
    # 太阳放左边：uCenter 的单位是"画面高度 = 1"，横向范围是 ±aspect/2
    sun_x = -aspect / 2 + 0.36 * (aspect / (16 / 9)) ** 0.6
    sun_r = 0.20 if aspect > 1.5 else 0.17
    img = background(w, h, sun_x, sun_r)

    # 文字块：从画面 48% 处开始，宽度占右侧，字号按最长一行"绿色的恒星？"（6 个字）放得下来算
    x0 = int(w * (0.47 if aspect > 1.5 else 0.45))
    block_w = w - x0 - int(w * 0.05)
    big = int(min(h * 0.145, block_w / 6.25))
    mid = int(big * 0.42)
    tag = int(big * 0.27)

    y = int(h * 0.20)
    text_with_shadow(img, (x0, y), [("「为什么」日常科学", DIM)], tag, bold=False)
    y += int(tag * 1.9)
    text_with_shadow(img, (x0, y), [("为什么没有", INK)], big)
    y += int(big * 1.18)
    text_with_shadow(img, (x0, y), [("绿色", GREEN), ("的恒星？", INK)], big)
    y += int(big * 1.45)
    text_with_shadow(img, (x0, y), [("太阳其实就是一颗", GOLD)], mid)

    OUT.mkdir(exist_ok=True)
    img.save(out)
    print(f"封面 {w}x{h} → {out}")


def main():
    cover(1920, 1080, OUT / "cover-16x9.png")
    cover(1440, 1080, OUT / "cover-4x3.png")


if __name__ == "__main__":
    main()
