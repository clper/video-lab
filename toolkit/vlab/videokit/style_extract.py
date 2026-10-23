"""风格参考：分析一段参考视频，产出 ①指标报告 ②总览拼图 ③色板图 ④草稿风格文件。

只提取抽象风格（配色、明暗、节奏、动感），不复制参考视频的任何内容。
草稿是"机器第一稿"：拿 sheet.png、palette.png、report.json 给 AI（或人）看，修正后存成正式 style.yaml。

用法:
    uv run vlab-style <参考视频.mp4> <输出目录> [--name 风格名]
输出:
    <输出目录>/sheet.png          均匀抽帧 + 镜头切换点抽帧拼成的总览图
    <输出目录>/palette.png        主色板（按占比排列，标出亮度和饱和度）
    <输出目录>/report.json        指标：镜头数、平均镜头时长、色板、亮度、对比度、饱和度、运动量
    <输出目录>/style.draft.yaml   草稿风格文件
"""

import argparse
import colorsys
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

from vlab import fonts

FONT = str(fonts.REGULAR)   # 仓库自带的思源黑体


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height",
                          "-select_streams", "v:0", "-of", "json", str(video)], capture_output=True, text=True, check=True)
    j = json.loads(out.stdout)
    return float(j["format"]["duration"]), j["streams"][0]["width"], j["streams"][0]["height"]


def scene_cuts(video, thresh=0.3):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", f"select='gt(scene,{thresh})',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def grab(video, t, width):
    for back in (0.0, 0.1, 0.25):
        png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t - back):.3f}", "-i", str(video), "-frames:v", "1",
                              "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                             capture_output=True, check=True).stdout
        if png:
            return Image.open(io.BytesIO(png)).convert("RGB")
    return None


def kmeans(px, k=8, iters=12, seed=0):
    rng = np.random.default_rng(seed)
    cent = px[rng.choice(len(px), k, replace=False)]
    for _ in range(iters):
        lab = np.argmin(((px[:, None, :] - cent[None]) ** 2).sum(-1), axis=1)
        for j in range(k):
            if (lab == j).any():
                cent[j] = px[lab == j].mean(0)
    lab = np.argmin(((px[:, None, :] - cent[None]) ** 2).sum(-1), axis=1)
    share = np.bincount(lab, minlength=k) / len(px)
    return cent, share


def hexc(rgb):
    return "#{:02x}{:02x}{:02x}".format(*[int(round(min(max(c, 0), 1) * 255)) for c in rgb])


def lum(rgb):
    return float(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])


def sat(rgb):
    return colorsys.rgb_to_hsv(*[float(c) for c in rgb])[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--name")
    args = ap.parse_args()
    video, out = Path(args.video), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = args.name or video.stem

    dur, w, h = probe(video)
    cuts = scene_cuts(video)
    bounds = [0.0] + cuts + [dur]
    shots = [b - a for a, b in zip(bounds, bounds[1:]) if b - a > 0.05]
    uniform = list(np.linspace(0.2, dur - 0.2, 12))
    times = sorted(set([round(t, 2) for t in uniform] + [round(c + 0.2, 2) for c in cuts[:8]]))
    frames = [(t, grab(video, t, 216)) for t in times]
    frames = [(t, f) for t, f in frames if f is not None]

    # 色板：所有抽帧的像素一起聚类
    px = np.concatenate([np.asarray(f.resize((72, int(72 * f.height / f.width))), np.float32).reshape(-1, 3) / 255
                         for _, f in frames])
    cent, share = kmeans(px, k=8)
    order = np.argsort(-share)
    palette = [{"hex": hexc(cent[i]), "share": round(float(share[i]), 3), "lum": round(lum(cent[i]), 3),
                "sat": round(sat(cent[i]), 3)} for i in order]
    L = 0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2]
    S = np.array([sat(p) for p in px[:: max(1, len(px) // 4000)]])

    # 运动量：每个采样点和 0.2 秒后的帧比较
    motion = []
    for t in uniform[:-1]:
        a, b = grab(video, t, 120), grab(video, t + 0.2, 120)
        if a is not None and b is not None and a.size == b.size:
            motion.append(float(np.abs(np.asarray(a, np.float32) - np.asarray(b, np.float32)).mean() / 255))
    mot = float(np.mean(motion)) if motion else 0.0

    report = {"video": str(video), "duration": round(dur, 2), "size": [w, h], "shots": len(shots),
              "avg_shot_sec": round(float(np.mean(shots)), 2) if shots else round(dur, 2),
              "brightness": round(float(L.mean()), 3), "contrast": round(float(L.std()), 3),
              "saturation": round(float(S.mean()), 3), "motion": round(mot, 4), "palette": palette}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 总览拼图
    tw, th = frames[0][1].size
    cols = 6
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols - 1) * 4, rows * th + (rows - 1) * 4), (40, 40, 40))
    font = ImageFont.truetype(FONT, 14)
    for i, (t, f) in enumerate(frames):
        ImageDraw.Draw(f).text((5, 4), f"{t:.1f}s", font=font, fill=(255, 230, 120))
        sheet.paste(f, ((i % cols) * (tw + 4), (i // cols) * (th + 4)))
    sheet.save(out / "sheet.png")

    # 色板图
    pw = 900
    pal_img = Image.new("RGB", (pw, 140), (20, 20, 20))
    d = ImageDraw.Draw(pal_img)
    x = 0
    for p in palette:
        ww = max(60, int(pw * p["share"]))
        d.rectangle([x, 0, x + ww, 100], fill=p["hex"])
        d.text((x + 4, 104), f"{p['hex']} {p['share'] * 100:.0f}%\n亮{p['lum']:.2f} 饱{p['sat']:.2f}",
               font=ImageFont.truetype(FONT, 12), fill=(230, 230, 230))
        x += ww
    pal_img.crop((0, 0, min(pw, x), 140)).save(out / "palette.png")

    # 草稿：最暗的大色块当背景，最亮的当文字，饱和度最高的几个当强调色；节奏快的动画就短
    big = [p for p in palette if p["share"] > 0.04] or palette
    bg = min(big, key=lambda p: p["lum"])
    ink = max(palette, key=lambda p: p["lum"])
    rest = [p for p in palette if p not in (bg, ink)]
    accents = sorted(rest, key=lambda p: -p["sat"] * (0.3 + p["share"]))[:3]
    dim = min(rest, key=lambda p: abs(p["lum"] - 0.55) + p["sat"]) if rest else ink
    bg2 = sorted(big, key=lambda p: p["lum"])[1] if len(big) > 1 else bg
    fast = report["avg_shot_sec"] < 2.5 or mot > 0.05
    draft = {
        "name": name,
        "source": str(video),
        "note": "style_extract.py 自动生成的草稿：请看 sheet.png / palette.png 修正后另存为正式风格文件",
        "palette": {"bg": bg["hex"], "bg2": bg2["hex"], "ink": ink["hex"], "dim": dim["hex"],
                    **{f"accent{i + 1}": a["hex"] for i, a in enumerate(accents)}},
        "motion": {"enter": "pop" if fast else "fade_up", "duration": 0.35 if fast else 0.6,
                   "stagger": 0.08 if fast else 0.15, "easing": "snappy" if fast else "smooth"},
        "texture": {"vignette": 0.3 if report["contrast"] > 0.2 else 0.15, "grain": 6 if report["saturation"] < 0.35 else 0},
    }
    (out / "style.draft.yaml").write_text(yaml.safe_dump(draft, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{video.name}: {dur:.1f}s，{len(shots)} 个镜头（平均 {report['avg_shot_sec']}s），"
          f"亮度 {report['brightness']}，饱和度 {report['saturation']}，运动量 {report['motion']}")
    print("色板：", " ".join(f"{p['hex']}({p['share'] * 100:.0f}%)" for p in palette))
    print("→", out)


if __name__ == "__main__":
    main()
