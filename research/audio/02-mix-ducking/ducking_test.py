"""音频实验 02：混音规范与自动避让（说话时音乐自动压低）

做什么：同一段配音 + 同一段程序化配乐，混两版——
    A：配乐固定音量（不避让）
    B：说话时配乐自动压低（sidechain 压缩，vlab.audio.mix 的默认规范）
然后实测：
    配乐在"说话时"和"停顿时"各有多响（把被压低后的配乐单独导出来测）
    两版成片的整体响度（LUFS）和真峰值（dBTP）
并画一张电平曲线图：蓝色是说话的时段，灰线是原配乐，金线是自动避让后的配乐。

用法（任意目录）:
    uv run vlab-tts research/audio/02-mix-ducking/content/duck-test.json   # 配音（已生成）
    uv run python research/audio/02-mix-ducking/ducking_test.py
产出 renders/：A_no_duck.m4a、B_duck.m4a（试听）、ducking_plot.png（曲线图）、report.json（数字）
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vlab.audio import mix, music

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build" / "duck-test"
OUT, MEDIA = HERE / "renders", HERE / "media"
FONT = "C:/Windows/Fonts/msyh.ttc"


def windows(tl):
    """说话的时段（每段从第一个词开始到最后一个词结束；配音片段末尾自带的静音不算说话），以及停顿时段（含片头片尾）"""
    speech = [(s["words"][0]["start"], s["words"][-1]["end"]) for s in tl["scenes"]]
    gaps, prev = [], 0.0
    for a, b in speech:
        if a - prev > 0.15:
            gaps.append((prev + 0.05, a - 0.05))
        prev = b
    gaps.append((prev + 0.05, tl["duration"] - 0.05))
    return speech, gaps


def level_curve(x, sr, hop=0.05):
    n = int(hop * sr)
    frames = len(x) // n
    seg = x[:frames * n].reshape(frames, n)
    return 20 * np.log10(np.sqrt((seg ** 2).mean(1)) + 1e-9)


def plot(plain, ducked, speech, dur, path, hop=0.05):
    Wd, Hd, L, R, T, B = 1600, 620, 90, 30, 70, 70
    img = Image.new("RGB", (Wd, Hd), (18, 20, 34))
    d = ImageDraw.Draw(img)
    f, fs = ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT, 20)
    X = lambda t: L + (Wd - L - R) * t / dur                          # noqa: E731
    lo, hi = -60, -10
    Y = lambda db: T + (Hd - T - B) * (hi - np.clip(db, lo, hi)) / (hi - lo)   # noqa: E731
    for a, b in speech:
        d.rectangle([X(a), T, X(b), Hd - B], fill=(34, 52, 92))
    for db in range(lo, hi + 1, 10):
        d.line([(L, Y(db)), (Wd - R, Y(db))], fill=(50, 54, 74))
        d.text((L - 70, Y(db) - 12), f"{db} dB", font=fs, fill=(150, 156, 180))
    for s in range(0, int(dur) + 1, 2):
        d.text((X(s) - 10, Hd - B + 12), f"{s}s", font=fs, fill=(150, 156, 180))
    for curve, col, w in ((plain, (140, 144, 160), 2), (ducked, (255, 200, 90), 3)):
        pts = [(X(i * hop), Y(v)) for i, v in enumerate(curve)]
        d.line(pts, fill=col, width=w)
    d.text((L, 20), "配乐电平：灰线 = 原配乐（不避让）  金线 = 自动避让后  蓝底 = 正在说话", font=f, fill=(235, 236, 245))
    img.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    MEDIA.mkdir(exist_ok=True)
    tl = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))
    dur = tl["duration"]
    narration = BUILD / "narration.wav"
    music_wav = MEDIA / "music.wav"
    music.write_wav(music_wav, music.ambient_pulse(dur, bpm=96, seed=1))

    mix.mix_audio(narration, OUT / "A_no_duck.m4a", music=music_wav, duration=dur, duck=False)
    mix.mix_audio(narration, OUT / "B_duck.m4a", music=music_wav, duration=dur, duck=True)

    # 把"压低后的配乐"单独导出来测；对照组是同样音量但不压低的配乐
    ducked_wav = MEDIA / "music_ducked.wav"
    mix.ducked_music(narration, music_wav, ducked_wav)
    m, sr = mix.read_wav(music_wav)
    plain = m * 10 ** (mix.MIX["music_db"] / 20)
    duck, sr2 = mix.read_wav(ducked_wav)
    speech, gaps = windows(tl)
    avg = lambda x, s, ws: float(np.mean([mix.rms_db(x, s, a, b) for a, b in ws]))   # noqa: E731
    res = {
        "配乐_说话时_不避让_dB": round(avg(plain, sr, speech), 1),
        "配乐_说话时_避让后_dB": round(avg(duck, sr2, speech), 1),
        "配乐_停顿时_不避让_dB": round(avg(plain, sr, gaps), 1),
        "配乐_停顿时_避让后_dB": round(avg(duck, sr2, gaps), 1),
    }
    res["说话时压低了_dB"] = round(res["配乐_说话时_不避让_dB"] - res["配乐_说话时_避让后_dB"], 1)
    res["停顿时压低了_dB"] = round(res["配乐_停顿时_不避让_dB"] - res["配乐_停顿时_避让后_dB"], 1)
    for name in ("A_no_duck", "B_duck"):
        lufs, peak = mix.loudness(OUT / f"{name}.m4a")
        res[f"{name}_整体响度_LUFS"], res[f"{name}_真峰值_dBTP"] = lufs, peak
    res["规范"] = {k: v for k, v in mix.MIX.items()}
    (OUT / "report.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    plot(level_curve(plain, sr), level_curve(duck, sr2), speech, dur, OUT / "ducking_plot.png")
    for k, v in res.items():
        if k != "规范":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
