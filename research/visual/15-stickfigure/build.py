"""火柴人样片的总装：算动作 → Remotion 卡 stickScene 出画面 → 按事件合成音效 → 混音成片。

    uv run python research/visual/15-stickfigure/build.py a            # 样片 A：火柴人 VS 物理
    uv run python research/visual/15-stickfigure/build.py b            # 样片 B：两个火柴人对打
    加 --sheet 只出骨架拼图（几秒，改关键帧时用），加 --frames 从成片抽帧拼图看效果

产物：build/<样片>.json（每帧关节数据）、build/<样片>_sfx.wav、media/<样片>_silent.mp4、renders/<样片>.mp4
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from vlab.stick.preview import sheet
from vlab.audio import mix, sfx
from vlab.render.remotion_bridge import render_shot

HERE = Path(__file__).resolve().parent
NAMES = {"a": "sample_a", "b": "sample_b"}


def frames_sheet(video, times, out, cols=4, w=640):
    """从成片抽几帧拼成一张图（看光效、粒子、倒影这些 Pillow 拼图里没有的东西）"""
    tiles = []
    for t in times:
        tmp = out.with_name(f"_f{t:.2f}.png")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={w}:-1", str(tmp)], check=True)
        tiles.append(Image.open(tmp).convert("RGB"))
        tmp.unlink()
    h = tiles[0].height
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * w, rows * h), "#000")
    for i, im in enumerate(tiles):
        img.paste(im, ((i % cols) * w, (i // cols) * h))
    img.save(out)
    return out


def main():
    args = sys.argv[1:]
    key = args[0] if args else "a"
    mod = importlib.import_module(NAMES[key])
    sc, info = mod.build()
    data, events = sc.export()
    for d in ("build", "media", "renders"):
        (HERE / d).mkdir(exist_ok=True)
    (HERE / "build" / f"{key}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    total = data["frames"] / data["fps"]
    print(f"样片 {key}：{data['frames']} 帧 / {total:.2f}s，事件 {len(events)} 个")
    print("  " + "  ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in info.items()))

    times = [float(x) for x in next((a.split("=", 1)[1] for a in args if a.startswith("--at=")), "").split(",") if x]
    if not times:
        times = [round(total * i / 11, 2) for i in range(12)]
    if "--sheet" in args:
        out = sheet(data, times, HERE / "media" / f"{key}_sheet.png", onion=2 if "--onion" in args else 0)
        print("骨架拼图：", out)
        return

    silent = HERE / "media" / f"{key}_silent.mp4"
    if "--frames" not in args or not silent.exists():
        render_shot("stickScene", silent, total, params={"data": data}, fps=data["fps"], frames=data["frames"],
                    width=1920, height=1080,
                    fx={"handheld": False, "stardust": False, "sweep": False, "flash": False,
                        "dipIn": 1.0, "dipOut": 0.0, "dipFrames": 10})
    wav = HERE / "build" / f"{key}_sfx.wav"
    sfx.write_wav(wav, sfx.render(events, total))
    final = HERE / "renders" / f"{key}.mp4"
    mix.mux(silent, None, final, sfx=wav, duration=total)
    print("成片：", final, "响度/峰值：", mix.loudness(final))
    out = frames_sheet(final, times, HERE / "media" / f"{key}_frames.png")
    print("抽帧拼图：", out)


if __name__ == "__main__":
    main()
