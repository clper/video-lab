"""音频实验 09：事件驱动音效 —— 音效样板

vlab.audio.sfx 里 12 种代码合成的音效逐个播放：每种一张卡片，写名称、什么时候用，画出波形，播放时播放线扫过。
用来试听、挑选、调参；实际使用时由画面的"事件清单"自动触发（例子见 research/visual/12-kinetic-type）。

用法（任意目录）:
    uv run python research/audio/09-event-sfx/sfx_palette.py      # → renders/sfx_palette.mp4
"""

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vlab.audio import mix, sfx

HERE = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
CARD, LEAD = 1.6, 0.25                 # 每张卡片 1.6 秒，卡片出现 0.25 秒后发声
INTRO = 1.2
F_B, F_R = "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"
USE = {"pop": "字、图标出现", "boing": "问号、可爱元素摇摆", "whoosh": "滑入、转场", "whip": "快速甩出画面",
       "tick": "数字跳动、计时", "impact": "重要数字落定、大标题", "chime": "亮点、光、答案揭晓", "key": "打字机效果",
       "glitch": "故障风文字", "shimmer": "魔法、星光出现", "laser": "光线、能量传播", "riser": "转场前蓄势"}
KINDS = list(sfx.KINDS)
BG, INK, DIM, GOLD, CYAN = (16, 18, 32), (240, 240, 250), (140, 146, 170), (255, 200, 90), (76, 201, 240)


@lru_cache(maxsize=32)
def font(path, size):
    return ImageFont.truetype(path, size)


@lru_cache(maxsize=16)
def wave_pts(kind):
    s = sfx.KINDS[kind](seed=1)
    n = 400
    chunks = np.array_split(np.abs(s), n)
    amp = np.array([c.max() if len(c) else 0 for c in chunks])
    return amp / (amp.max() + 1e-9), len(s) / sfx.SR


def frame(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 180), "音效样板 · 全部由代码合成", font=font(F_B, 56), fill=INK, anchor="mm")
    d.text((W / 2, 260), "画面里每个动作，自动配上对应的声音", font=font(F_R, 38), fill=DIM, anchor="mm")
    if t < INTRO:
        return np.asarray(img)
    i = min(int((t - INTRO) / CARD), len(KINDS) - 1)
    k = KINDS[i]
    t_card = t - INTRO - i * CARD
    d.text((W / 2, 560), f"{i + 1:02d} / {len(KINDS)}", font=font(F_R, 40), fill=DIM, anchor="mm")
    d.text((W / 2, 720), sfx.LABELS[k], font=font(F_B, 180), fill=GOLD, anchor="mm")
    d.text((W / 2, 860), k, font=font(F_R, 54), fill=CYAN, anchor="mm")
    d.text((W / 2, 960), f"用在：{USE[k]}", font=font(F_R, 46), fill=INK, anchor="mm")
    amp, dur = wave_pts(k)                                           # 波形 + 播放线
    x0, x1, yc, hh = 120, 960, 1300, 180
    for j, a in enumerate(amp):
        x = x0 + (x1 - x0) * j / len(amp)
        d.line([(x, yc - a * hh), (x, yc + a * hh)], fill=(70, 80, 120), width=2)
    p = (t_card - LEAD) / dur
    if 0 <= p <= 1:
        px = x0 + (x1 - x0) * p
        for j, a in enumerate(amp[:int(p * len(amp))]):
            x = x0 + (x1 - x0) * j / len(amp)
            d.line([(x, yc - a * hh), (x, yc + a * hh)], fill=GOLD, width=2)
        d.line([(px, yc - hh - 30), (px, yc + hh + 30)], fill=INK, width=4)
    d.text((W / 2, yc + hh + 80), f"{dur:.2f} 秒", font=font(F_R, 36), fill=DIM, anchor="mm")
    return np.asarray(img)


def main():
    out_dir, media = HERE / "renders", HERE / "media"
    out_dir.mkdir(exist_ok=True)
    media.mkdir(exist_ok=True)
    dur = INTRO + CARD * len(KINDS) + 0.4
    events = [{"t": INTRO + i * CARD + LEAD, "kind": k, "gain": 0.9} for i, k in enumerate(KINDS)]
    fx = media / "sfx.wav"
    sfx.write_wav(fx, sfx.render(events, dur))
    silent = media / "silent.mp4"
    enc = subprocess.Popen([shutil.which("ffmpeg") or "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for n in range(round(dur * FPS)):
        enc.stdin.write(frame(n / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    # 这里没有配音，把音效轨放在"主音轨"位置，照样按成片规范统一响度
    mix.mux(silent, fx, out_dir / "sfx_palette.mp4", duration=dur)
    silent.unlink()
    print("音效样板 →", out_dir / "sfx_palette.mp4")


if __name__ == "__main__":
    main()
