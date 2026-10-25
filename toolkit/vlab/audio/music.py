"""程序化背景音乐（研究路线见 research/audio/README.md 的 03 程序化背景音乐）。

目前一种：ambient_pulse —— 小调四和弦循环（Am–F–C–G）的铺底 + 八分音符琶音 + 轻鼓，适合科普和文字动效做底。
自己生成的音乐没有版权问题；后续在 research/audio/03 里扩展情绪、节奏、乐器。

    from vlab.audio import music
    music.write_wav("music.wav", music.ambient_pulse(20.0, bpm=100))
"""

import numpy as np

from vlab.audio.sfx import SR, write_wav  # noqa: F401  （统一采样率，顺便导出 write_wav）

NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
CHORDS = [("A", "m"), ("F", ""), ("C", ""), ("G", "")]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord_midis(root, kind, octave=3):
    r = NOTE[root] + 12 * (octave + 1)
    third = 3 if kind == "m" else 4
    return [r, r + third, r + 7]


def _lowpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / cutoff) ** 4), len(x))


def ambient_pulse(duration, bpm=100, seed=0, chords=CHORDS):
    n = int(duration * SR)
    out = np.zeros(n + SR * 2)
    beat = 60 / bpm
    bar = 4 * beat
    rng = np.random.default_rng(seed)
    t_all = np.arange(len(out)) / SR
    # 铺底：每小节一个和弦，三个音各两路微失谐的锯齿波（叠 6 次谐波），慢起慢收
    pad = np.zeros(len(out))
    for b in range(int(duration / bar) + 2):
        root, kind = chords[b % len(chords)]
        a, e = int(b * bar * SR), int(min((b + 1) * bar + 0.4, duration + 2) * SR)
        seg_t = np.arange(e - a) / SR
        env = np.minimum(1, seg_t / 0.5) * np.minimum(1, (len(seg_t) / SR - seg_t) / 0.4)
        for m in chord_midis(root, kind, 3):
            for det in (0.9985, 1.0015):
                f = midi_hz(m) * det
                pad[a:e] += sum(np.sin(2 * np.pi * f * h * seg_t) / h for h in range(1, 7)) * env * 0.05
    out += _lowpass(pad, 1400)
    # 琶音：八分音符，在和弦音上高八度往返，三角波拨弦
    step = beat / 2
    k = 0
    t = 0.0
    while t < duration:
        root, kind = chords[int(t / bar) % len(chords)]
        tones = chord_midis(root, kind, 4) + [chord_midis(root, kind, 5)[0]]
        m = tones[[0, 1, 2, 3, 2, 1][k % 6]]
        d = 0.32
        st = np.arange(int(d * SR)) / SR
        ph = (st * midi_hz(m)) % 1
        tri = 4 * np.abs(ph - 0.5) - 1
        vel = 0.10 if k % 2 == 0 else 0.065
        i0 = int(t * SR)
        out[i0:i0 + len(st)] += tri * np.exp(-st * 9) * np.minimum(1, st / 0.003) * vel
        t += step
        k += 1
    # 轻鼓：每拍一下底鼓（1、3 拍重），反拍一个小镲
    t = 0.0
    k = 0
    while t < duration:
        st = np.arange(int(0.25 * SR)) / SR
        kick = np.sin(2 * np.pi * np.cumsum(55 * np.exp(-st * 18) + 42) / SR) * np.exp(-st * 14)
        i0 = int(t * SR)
        out[i0:i0 + len(st)] += kick * (0.22 if k % 2 == 0 else 0.12)
        hat_n = int(0.03 * SR)
        hat = rng.uniform(-1, 1, hat_n) * np.exp(-np.arange(hat_n) / SR * 120)
        hat = hat - _lowpass(hat, 6000)
        j0 = int((t + beat / 2) * SR)
        out[j0:j0 + hat_n] += hat * 0.05
        t += beat
        k += 1
    out = out[:n]
    fade_in, fade_out = int(1.0 * SR), int(1.5 * SR)
    out[:fade_in] *= np.linspace(0, 1, fade_in)
    out[-fade_out:] *= np.linspace(1, 0, fade_out)
    return out / (np.abs(out).max() + 1e-9) * 0.6


# ── 有段落的配乐 ────────────────────────────────────────────────────
# ambient_pulse 是一条从头到尾一个密度的铺底——两分钟后就听不出“在走路”。
# fold_score 不动和声与动机，只在同一条铺底上按段落改频带与电平：
# 闷（纸里）→ 全开（片名）→ 抽掉低频（墙：折不动的空）→ 闷（走廊）→
# 全停（一句留白）→ 只剩一点木头味的底（回场）。
# 边界用 0.4 秒交叉淡化，所以听不到开关声。
#
#   segs = [(起, 止, {lp/hp/gain}), ...]，单位秒。lp/hp 是 FFT 一阶拱形滤波的分频点。

def _band(x, lp=None, hp=None):
    y = x
    if hp:
        y = y - _lowpass(y, hp)      # 一阶高通：拿掉低频，保留 pad 与铃声
    if lp:
        y = _lowpass(y, lp)
    return y


DEFAULT_SEGS = [
    (0.0, 18.0, {"lp": 900, "gain": 0.92}),      # 钩子：闷在纸里
    (18.0, 23.4, {"gain": 1.0}),                  # 片名：全开
    (23.4, 45.0, {"gain": 0.96}),                 # 章一 · 手
    (45.0, 104.4, {"gain": 1.0}),                 # 章二 · 尺
    (104.4, 125.4, {"hp": 300, "gain": 0.95}),   # 章三 · 墙：拿走鼓
    (125.4, 140.4, {"lp": 2200, "gain": 0.95}),  # 走廊 / 八小时：闷
    (140.4, 164.6, {"gain": 1.0}),                # 章四 · 平
    (164.6, 167.2, {"gain": 0.0}),                # 全停
    (167.2, 1e9, {"lp": 1500, "gain": 0.78}),    # 回场：只剩底
]


def fold_score(duration, bpm=100, seed=0, segs=None, xf=0.4):
    """带段落的铺底：同一套和声，按段落换频带与电平（002/006 这类长片用）"""
    n = int(duration * SR)
    base = ambient_pulse(duration + 1.0, bpm=bpm, seed=seed)[:n]
    out = np.zeros(n)
    for t0, t1, kw in (segs or DEFAULT_SEGS):
        a = max(0, int((t0 - xf) * SR))
        b = min(n, int((t1 + xf) * SR))
        if b <= a:
            continue
        y = _band(base[a:b], kw.get("lp"), kw.get("hp")) * kw.get("gain", 1.0)
        env = np.ones(b - a)
        f = int(xf * SR)
        if a > 0:
            m = min(f, b - a)
            env[:m] = np.linspace(0, 1, m)
        if b < n:
            m = min(f, b - a)
            env[-m:] = np.minimum(env[-m:], np.linspace(1, 0, m))
        out[a:b] += y * env
    tail = int(min(3.5, duration * 0.2) * SR)
    out[-tail:] *= np.linspace(1, 0, tail) ** 0.8
    return out / (np.abs(out).max() + 1e-9) * 0.6
