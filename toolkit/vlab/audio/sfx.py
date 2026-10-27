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


# —— 动作片用的击打声（research/visual/15-stickfigure）：短、低频有"肉"，起音带一点噪声的"啪" ——

def _lowpass(x, fc, order=2):
    """频域低通（幅度 1/sqrt(1+(f/fc)^2n)），给短噪声去掉刺耳的高频"""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(np.fft.rfft(x) / np.sqrt(1 + (f / fc) ** (2 * order)), len(x))


def _norm(s, peak=0.95):
    return s / (np.abs(s).max() + 1e-9) * peak


def punch(seed=0):
    t = _t(0.22)
    body = _fm_sine(170 * np.exp(-t * 32) + 52, 0.22) * _env(len(t), 0.001, 0.07)      # 下坠的低频"咚"
    n = int(0.05 * SR)
    slap = np.zeros(len(t))
    slap[:n] = _norm(_lowpass(_noise(n, seed), 2600)) * _env(n, 0.0005, 0.012)         # 起音的"啪"
    return _norm(np.tanh((body * 1.4 + slap * 1.1) * 1.8))


def kick(seed=0):
    t = _t(0.16)
    body = _fm_sine(250 * np.exp(-t * 40) + 95, 0.16) * _env(len(t), 0.0008, 0.045)
    n = int(0.03 * SR)
    click = np.zeros(len(t))
    click[:n] = _norm(_lowpass(_noise(n, seed + 3), 4200)) * _env(n, 0.0003, 0.006)
    return _norm(np.tanh((body + click * 0.8) * 1.6))


def block(seed=0):
    t = _t(0.2)
    body = _fm_sine(330 * np.exp(-t * 36) + 120, 0.2) * _env(len(t), 0.0005, 0.05)
    n = int(0.012 * SR)
    click = np.zeros(len(t))
    click[:n] = _sweep_filter(_noise(n, seed + 5), 5200, 3000, 0.7) * _env(n, 0.0002, 0.004)
    return _norm(np.tanh((body + _norm(click) * 0.7) * 2.2))


def step(seed=0):
    n = int(0.09 * SR)
    t = _t(0.09)
    scuff = _norm(_lowpass(_noise(n, seed + 7), 900)) * _env(n, 0.002, 0.022)
    thump = np.sin(2 * np.pi * 85 * t) * _env(n, 0.003, 0.03)
    return _norm(scuff * 0.7 + thump * 0.6, 0.8)


def thud(seed=0):
    t = _t(0.5)
    body = _fm_sine(92 * np.exp(-t * 10) + 38, 0.5) * _env(len(t), 0.002, 0.14)
    rumble = _norm(_lowpass(_noise(len(t), seed + 11), 300)) * _env(len(t), 0.003, 0.12)
    s = body * 1.3 + rumble
    k = int(0.07 * SR)                                   # 四肢跟着落地的第二下
    s[k:] += 0.45 * s[:-k]
    return _norm(np.tanh(s * 1.5))


def knock(seed=0):
    t = _t(0.25)
    s = (np.sin(2 * np.pi * 380 * t) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * 1050 * t) * np.exp(-t / 0.02)
         + 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.08))
    n = int(0.003 * SR)
    s[:n] += _noise(n, seed + 13) * np.linspace(0.5, 0, n)
    return _norm(s, 0.9)


def bounce(seed=0):
    t = _t(0.18)
    s = _fm_sine(185 * np.exp(-t * 18) + 70, 0.18) * _env(len(t), 0.001, 0.05)
    n = int(0.01 * SR)
    s[:n] += _norm(_lowpass(_noise(n, seed + 17), 1800)) * np.linspace(0.4, 0, n)
    return _norm(s, 0.9)


def stomp(seed=0):
    """大块头的重脚步：很低的"咚" + 地面的闷震 + 一点碎屑"""
    t = _t(0.55)
    sub = _fm_sine(70 * np.exp(-t * 9) + 32, 0.55) * _env(len(t), 0.003, 0.16)
    rumble = _norm(_lowpass(_noise(len(t), seed + 19), 160)) * _env(len(t), 0.004, 0.2)
    n = int(0.04 * SR)
    grit = np.zeros(len(t))
    grit[:n] = _norm(_lowpass(_noise(n, seed + 23), 2400)) * _env(n, 0.001, 0.01)
    return _norm(np.tanh((sub * 1.5 + rumble * 0.8 + grit * 0.35) * 1.6))


def crash(seed=0):
    """整个人砸在地上：超低频的下坠 + 宽频的爆裂 + 碎屑和余震拖尾"""
    t = _t(1.6)
    sub = _fm_sine(60 * np.exp(-t * 4) + 26, 1.6) * _env(len(t), 0.003, 0.45)
    n = int(0.25 * SR)
    burst = np.zeros(len(t))
    burst[:n] = _sweep_filter(_noise(n, seed + 29), 2600, 160) * _env(n, 0.001, 0.07)
    tail = _norm(_lowpass(_noise(len(t), seed + 31), 500)) * _env(len(t), 0.02, 0.5) * 0.5
    s = sub * 1.6 + _norm(burst) * 0.9 + tail
    k = int(0.09 * SR)                                    # 身体弹一下的第二声
    s[k:] += 0.35 * s[:-k]
    return _norm(np.tanh(s * 1.4))


def slap(seed=0):
    """抓住手腕、轻轻一拨：短促的"啪\""""
    n = int(0.07 * SR)
    t = _t(0.07)
    s = _norm(_sweep_filter(_noise(n, seed + 37), 2400, 1200, 0.8)) * _env(n, 0.0004, 0.014)
    s += np.sin(2 * np.pi * 220 * t) * _env(n, 0.001, 0.02) * 0.4
    return _norm(s, 0.85)


def scrape(seed=0, dur=0.6):
    """在地上滑出去：带通噪声，越滑越轻"""
    n = int(dur * SR)
    x = _sweep_filter(_noise(n, seed + 41), 900, 500, 0.9)
    env = np.minimum(1, np.arange(n) / (0.02 * SR)) * np.linspace(1, 0, n) ** 1.5
    return _norm(x * env, 0.8)


def hum(seed=0, dur=2.0, f=110.0):
    """定格时的嗡鸣：几层正弦慢慢起、慢慢落"""
    t = _t(dur)
    s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.01 * t) + 0.25 * np.sin(2 * np.pi * f * 3.0 * t)
         + 0.2 * np.sin(2 * np.pi * f * 0.5 * t))
    env = np.minimum(1, t / 0.25) * np.minimum(1, (dur - t) / 0.4)
    return _norm(s * env * (0.85 + 0.15 * np.sin(2 * np.pi * 3 * t)), 0.6)


def rumble(seed=0, dur=1.6):
    """憋着火的低吼：低频噪声慢慢涨起来再落下"""
    n = int(dur * SR)
    x = _norm(_lowpass(_noise(n, seed + 43), 120, 3))
    env = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return _norm(np.tanh(x * env * 2.0), 0.8)


def wind(seed=0, dur=1.2, f0=500, f1=900):
    """风、气流：慢慢扫过的带通噪声"""
    n = int(dur * SR)
    x = _sweep_filter(_noise(n, seed + 47), f0, f1, 0.7)
    return _norm(x * np.sin(np.linspace(0, np.pi, n)) ** 2, 0.7)


def pulse(seed=0):
    """躺在地上的喘息：两下很低的闷跳"""
    t = _t(0.7)
    beat = np.sin(2 * np.pi * 50 * t) * _env(len(t), 0.01, 0.07)
    s = beat.copy()
    k = int(0.22 * SR)
    s[k:] += 0.7 * beat[:-k]
    return _norm(s, 0.8)


KINDS = {"pop": pop, "boing": boing, "whoosh": whoosh, "whip": whip, "tick": tick, "impact": impact, "chime": chime,
         "key": key, "glitch": glitch, "shimmer": shimmer, "laser": laser, "riser": riser,
         "punch": punch, "kick": kick, "block": block, "step": step, "thud": thud, "knock": knock, "bounce": bounce,
         "stomp": stomp, "crash": crash, "slap": slap, "scrape": scrape, "hum": hum, "rumble": rumble, "wind": wind,
         "pulse": pulse}
LABELS = {"pop": "弹出", "boing": "回弹", "whoosh": "呼啸", "whip": "甩镜", "tick": "咔嗒", "impact": "冲击", "chime": "铃音",
          "key": "打字", "glitch": "故障", "shimmer": "闪烁", "laser": "激光", "riser": "上扬",
          "punch": "出拳打中", "kick": "踢球", "block": "格挡", "step": "脚步", "thud": "倒地", "knock": "撞墙",
          "bounce": "落地弹起", "stomp": "重脚步", "crash": "重摔", "slap": "拍、抓", "scrape": "滑行",
          "hum": "定格嗡鸣", "rumble": "低吼", "wind": "风", "pulse": "喘息"}


def render(events, duration):
    """事件清单 → 一条单声道音效轨（float，-1..1）。同一种音效每次略有变化，听起来不机械。
    事件可以带 args（如 {"dur": 0.8, "f0": 150}），原样传给对应的合成函数"""
    out = np.zeros(int(duration * SR) + SR)
    for i, e in enumerate(events):
        s = KINDS[e["kind"]](seed=i, **(e.get("args") or {})) * e.get("gain", 1.0)
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
