"""003 里用着色器渲染的三段：hook（云海飞越）、noon（中午蓝天）、sunset（太阳下沉、晚霞变红）。

每段的帧数按 timeline.json 精确计算（和其他段拼起来正好等于配音长度）。
画面上方叠标题（和 Manim 段同样的位置和字号风格），大气段再叠"太阳高度"读数。

用法（在 003-sunset-red 目录里）:
    uv run python shader/render_clips.py                  # 三段都渲染 → media/clips/*.mp4
    uv run python shader/render_clips.py --only noon      # 只渲染一段
    uv run python shader/render_clips.py --still sunset:3 # 只出某段第 3 秒的一帧 PNG，调画面用
"""

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vlab.render.glsl import ShaderRenderer, render_clip
from vlab.scenes import SHADERS

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent

FPS = 30
TL = json.loads((PROJ / "build" / "sunset-red" / "timeline.json").read_text(encoding="utf-8"))
SCENES = {s["id"]: s for s in TL["scenes"]}
CLIP_DIR = PROJ / "media" / "clips"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT = "C:/Windows/Fonts/msyh.ttc"


def frame_range(sid):
    s = SCENES[sid]
    return round(s["start"] * FPS), round(s["end"] * FPS)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def text_overlay(title, sub=None, title_color=(248, 250, 252), sub_color=(253, 186, 116)):
    ft = ImageFont.truetype(FONT_B, 80)
    fs = ImageFont.truetype(FONT, 50)

    def draw(t, img):
        d = ImageDraw.Draw(img)
        for text, font, y, col in ((title, ft, 288, title_color), (sub(t) if sub else None, fs, 400, sub_color)):
            if not text:
                continue
            w = d.textlength(text, font=font)
            x = (img.width - w) / 2
            d.text((x + 2, y - font.size / 2 + 3), text, font=font, fill=(0, 0, 0))     # 阴影，保证亮天空上也看得清
            d.text((x, y - font.size / 2), text, font=font, fill=col)
        return img
    return draw


def sun_label(elev_fn):
    return lambda t: f"太阳高度 {math.degrees(elev_fn(t)):.1f}°"


# 每段：着色器、超采样、起始时间、每帧 uniform、文字
def clip_specs():
    n_sunset = frame_range("sunset")[1] - frame_range("sunset")[0]
    dur_sunset = n_sunset / FPS
    sunset_elev = lambda t: math.radians(6.0 - 7.3 * ease(t / dur_sunset))        # 6° 降到 -1.3°：地面进入阴影，高空的云还被照红
    noon_elev = lambda t: math.radians(62.0)
    return {
        "hook": dict(frag="cloudsea.frag", ss=2, t0=2.0, uniforms=None,
                     overlay=text_overlay("天为什么是蓝的？", lambda t: "夕阳为什么是红的？" if t >= 2.0 + 2.2 else None,
                                          sub_color=(253, 186, 116))),
        "noon": dict(frag="atmosphere.frag", ss=1, t0=0.0,
                     uniforms=lambda t: dict(uSunElev=noon_elev(t), uSunAzim=math.radians(150.0),
                                             uPitch=math.radians(14.0 + 1.2 * t), uExposure=1.1, uCloudCover=0.42),
                     overlay=text_overlay("中午：天是蓝的", sun_label(noon_elev), sub_color=(147, 197, 253))),
        "sunset": dict(frag="atmosphere.frag", ss=1, t0=0.0,
                       uniforms=lambda t: dict(uSunElev=sunset_elev(t), uSunAzim=math.radians(8.0),
                                               uPitch=math.radians(9.0), uExposure=1.0 + 5.0 * ease(t / dur_sunset) ** 2,
                                               uCloudCover=0.50),
                       overlay=text_overlay("傍晚：夕阳和晚霞", sun_label(sunset_elev))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="逗号分隔：hook,noon,sunset")
    ap.add_argument("--still", help="段名:秒，如 sunset:3")
    args = ap.parse_args()
    specs = clip_specs()

    if args.still:
        sid, t = args.still.split(":")
        sp = specs[sid]
        r = ShaderRenderer(SHADERS / sp["frag"], ss=sp["ss"])
        tt = sp["t0"] + float(t)
        img = Image.fromarray(r.frame(tt, **(sp["uniforms"](tt) if sp["uniforms"] else {})))
        img = sp["overlay"](tt, img) if sp["overlay"] else img
        out = CLIP_DIR / f"{sid}_still_{float(t):.1f}s.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        print("静帧 →", out)
        return

    for sid in (args.only.split(",") if args.only else specs):
        sp = specs[sid]
        f0, f1 = frame_range(sid)
        print(f"  {sid}: {f1 - f0} 帧（{(f1 - f0) / FPS:.2f}s）")
        r = ShaderRenderer(SHADERS / sp["frag"], ss=sp["ss"])
        render_clip(r, CLIP_DIR / f"{sid}.mp4", f1 - f0, t0=sp["t0"], fps=FPS,
                    uniforms=sp["uniforms"], overlay=sp["overlay"])


if __name__ == "__main__":
    main()
