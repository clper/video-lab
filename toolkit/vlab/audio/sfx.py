"""代码合成的音效 + 事件驱动音效（研究记录见 research/audio/09-event-sfx/）。

代码生成的视频知道每个画面事件发生的精确时间（字弹出、转场、数字跳动……），
把这些事件交给 render()，就自动得到一条和画面严丝合缝的音效轨。

    from vlab.audio import sfx
    events = [{"t": 0.35, "kind": "pop", "gain": 0.5}, {"t": 2.6, "kind": "whoosh", "gain": 0.7}]
    sfx.write_wav("sfx.wav", sfx.render(events, duration=20.0))

音效种类见 KINDS。全部用 numpy 合成，没有素材文件，没有版权问题。
"""

import wave

import numpy as np

SR = 48000


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _env(n, attack=0.002, decay=0.08):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / decay)


def _noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def _sweep_filter(x, f_start, f_end, width=0.6, hop=256, nfft=1024):
    """随时间移动中心频率的带通（短时傅里叶），用来做"呼啸"这类有方向感的噪声"""
    win = np.hanning(nfft)
    out = np.zeros(len(x) + nfft)
    norm = np.zeros(len(x) + nfft)
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    n_frames = max(1, (len(x) - nfft) // hop + 1)
    for i in range(n_frames):
        a = i * hop
        seg = x[a:a + nfft]
        if len(seg) < nfft:
            seg = np.pad(seg, (0, nfft - len(seg)))
        f = i / max(n_frames - 1, 1)
        fc = f_start * (f_end / f_start) ** f
        g = np.exp(-0.5 * (np.log(np.maximum(freqs, 1) / fc) / width) ** 2)
        y = np.fft.irfft(np.fft.rfft(seg * win) * g, nfft)
        out[a:a + nfft] += y * win
        norm[a:a + nfft] += win ** 2
    return (out / np.maximum(norm, 1e-6))[:len(x)]


def _fm_sine(f, dur):
    """频率随时间变化的正弦（f 是长度为采样数的频率数组）"""
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def pop(seed=0):
    t = _t(0.09)
    f0 = 700 * 2 ** (np.random.default_rng(seed).uniform(-0.3, 0.3))
    s = _fm_sine(f0 * np.exp(-t * 28) + 180, 0.09) * _env(len(t), 0.001, 0.035)
    s[:30] += np.linspace(0.6, 0, 30)                                     # 起音的小咔嗒
    return s


def boing(seed=0):
    t = _t(0.45)
    f = 260 + 420 * (1 - np.exp(-t * 9)) + 35 * np.sin(2 * np.pi * 9 * t)
    return _fm_sine(f, 0.45) * _env(len(t), 0.004, 0.16)


def whoosh(seed=0, dur=0.38, f0=300, f1=2600):
    n = int(dur * SR)
    x = _sweep_filter(_noise(n, seed), f0, f1)
    s = x * np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return s / (np.abs(s).max() + 1e-9) * 0.9


def whip(seed=0):
    s = whoosh(seed, 0.22, 900, 6000)
    return s * np.linspace(0.6, 1.0, len(s)) ** 2


def tick(seed=0):
    t = _t(0.012)
    return np.sin(2 * np.pi * 3200 * t) * _env(len(t), 0.0003, 0.0025)


def impact(seed=0):
    t = _t(0.6)
    body = _fm_sine(110 * np.exp(-t * 6) + 42, 0.6) * _env(len(t), 0.002, 0.22)
    n = int(0.12 * SR)
    burst = np.zeros(len(t))
    burst[:n] = _sweep_filter(_noise(n, seed), 1200, 200) * _env(n, 0.001, 0.04)
    return np.tanh((body * 1.2 + burst * 0.8) * 1.5)


def chime(seed=0, base=1046.5):
    t = _t(1.6)
    s = np.zeros(len(t))
    for k, (ratio, amp, dec) in enumerate(((1, 1, 0.7), (2.0, 0.5, 0.45), (3.01, 0.35, 0.3), (4.2, 0.2, 0.2), (5.4, 0.12, 0.15))):
        s += amp * np.sin(2 * np.pi * base * ratio * t + k) * np.exp(-t / dec)
    return s * np.minimum(1, t / 0.002) / 2.2


def key(seed=0):
    n = int(0.03 * SR)
    click = _sweep_filter(_noise(n, seed), 3000, 2500, 0.8) * _env(n, 0.0005, 0.008)
    thump = np.sin(2 * np.pi * 140 * _t(0.03)) * _env(n, 0.001, 0.012)
    s = click / (np.abs(click).max() + 1e-9) * 0.8 + thump * 0.5
    return s / (np.abs(s).max() + 1e-9) * 0.9


def glitch(seed=0):
    rng = np.random.default_rng(seed + 99)
    parts = []
    for _ in range(7):
        d = rng.uniform(0.012, 0.032)
        t = _t(d)
        f = rng.uniform(180, 2200)
        sq = np.sign(np.sin(2 * np.pi * f * t))
        crushed = np.round(_noise(len(t), int(rng.integers(1e6))) * 3) / 3
        parts.append((sq * 0.6 + crushed * 0.4) * rng.uniform(0.4, 1.0))
    return np.concatenate(parts) * 0.8


def shimmer(seed=0):
    t = _t(0.7)
    s = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate((2093, 2637, 3136, 4186, 5274)))
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 14 * t)
    s = s * trem * np.sin(np.linspace(0, np.pi, len(t))) ** 2
    return s / (np.abs(s).max() + 1e-9) * 0.8


def laser(seed=0, dur=1.4):
    t = _t(dur)
    f = 300 * (1500 / 300) ** (t / dur)
    s = _fm_sine(f, dur) * 0.6 + _fm_sine(f * 2, dur) * 0.2
    return s * np.sin(np.linspace(0, np.pi, len(t))) ** 0.8 * 0.6


def riser(seed=0, dur=0.8):
    n = int(dur * SR)
    x = _sweep_filter(_noise(n, seed), 300, 5000) * np.linspace(0, 1, n) ** 2
    return x / (np.abs(x).max() + 1e-9)


KINDS = {"pop": pop, "boing": boing, "whoosh": whoosh, "whip": whip, "tick": tick, "impact": impact, "chime": chime,
         "key": key, "glitch": glitch, "shimmer": shimmer, "laser": laser, "riser": riser}
LABELS = {"pop": "弹出", "boing": "回弹", "whoosh": "呼啸", "whip": "甩镜", "tick": "咔嗒", "impact": "冲击", "chime": "铃音",
          "key": "打字", "glitch": "故障", "shimmer": "闪烁", "laser": "激光", "riser": "上扬"}


def render(events, duration):
    """事件清单 → 一条单声道音效轨（float，-1..1）。同一种音效每次略有变化，听起来不机械"""
    out = np.zeros(int(duration * SR) + SR)
    for i, e in enumerate(events):
        s = KINDS[e["kind"]](seed=i) * e.get("gain", 1.0)
        k = int(e["t"] * SR)
        if k >= len(out):
            continue
        out[k:k + len(s)] += s[:len(out) - k]
    out = out[:int(duration * SR)]
    peak = np.abs(out).max()
    return out / peak * 0.9 if peak > 0.9 else out


def write_wav(path, x, sr=SR):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
