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
