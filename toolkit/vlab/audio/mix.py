"""混音：配音 + 配乐（说话时自动压低）+ 音效 → 统一响度 → 和画面合成。
规范和实测见 research/audio/02-mix-ducking/。

默认规范（MIX 字典，可以按项目覆盖）：
    配音        原样（vlab-tts 已标准化到 -16 LUFS）
    配乐        -12 dB；说话时稳定压低 8 dB（depth_db），停顿时 0.5 秒内回来。
                做法：sidechain 压缩用高比率一开口就压住，再只混回 40% 原信号（mix 参数），
                避让深度固定，不会被压到听不见、也不会忽高忽低（research/audio/02 实测对比）
    音效        -6 dB
    成片        立体声 -14 LUFS，真峰值不超过 -1.5 dBTP（短视频平台常见目标，具体以平台为准）；
                响度标准化分两遍（先测量、再线性调整），结果准确落在目标值

    from vlab.audio import mix
    mix.mux("silent.mp4", "build/x/narration.wav", "renders/x.mp4", music="music.wav", sfx="sfx.wav", duration=20.6)
"""

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

FF = shutil.which("ffmpeg") or "ffmpeg"
MIX = dict(music_db=-12.0, sfx_db=-6.0, duck=True, depth_db=8.0, threshold=0.005, ratio=20, attack=20, release=500,
           lufs=-14.0, tp=-1.5)


def _duck(opt):
    """sidechaincompress 参数串：mix = 1 - 10^(-深度/20)，说话时输出 ≈ 原信号的 10^(-深度/20)"""
    wet = 1 - 10 ** (-opt["depth_db"] / 20)
    return (f"sidechaincompress=threshold={opt['threshold']}:ratio={opt['ratio']}:attack={opt['attack']}:"
            f"release={opt['release']}:mix={wet:.3f}")


def _loudnorm(opt, measured=None):
    """响度标准化分两遍：第一遍只测量（print_format=json），第二遍用测量值线性调整，结果准确落在目标值"""
    base = f"loudnorm=I={opt['lufs']}:TP={opt['tp']}:LRA=11"
    if measured is None:
        return base + ":print_format=json"
    m = measured
    return (base + f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                   f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")


def _measure(cmd_inputs, graph):
    """跑第一遍，从 ffmpeg 输出里取 loudnorm 的测量结果"""
    r = subprocess.run([FF, "-hide_banner", "-nostats", *cmd_inputs, "-filter_complex", graph, "-map", "[a]", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    blob = r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1]
    return json.loads(blob)


def _graph(first_audio_idx, has_voice, has_music, has_sfx, opt, measured=None):
    """拼 ffmpeg 滤镜：输入顺序 = 配音（可无）、配乐（可无）、音效（可无）

    无人声时（纯音乐 + 字幕的片子）没有 sidechain 的 key，避让自动关掉，音乐走满电平。
    """
    i = first_audio_idx
    parts, labels = [], []
    if has_voice:
        if has_music and opt["duck"]:
            parts.append(f"[{i}:a]aresample=48000,asplit=2[voice][key]")
        else:
            parts.append(f"[{i}:a]aresample=48000[voice]")
        labels.append("[voice]")
        i += 1
    if has_music:
        parts.append(f"[{i}:a]aresample=48000,volume={opt['music_db']}dB[m0]")
        if has_voice and opt["duck"]:
            parts.append(f"[m0][key]{_duck(opt)}[mus]")
        else:
            parts.append("[m0]anull[mus]")
        labels.append("[mus]")
        i += 1
    if has_sfx:
        parts.append(f"[{i}:a]aresample=48000,volume={opt['sfx_db']}dB[fx]")
        labels.append("[fx]")
    if not labels:
        raise ValueError("没有任何音频输入：至少要给配音、配乐或音效")
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,"
                 f"pan=stereo|c0=c0|c1=c0,{_loudnorm(opt, measured)},"
                 # loudnorm 输出 192kHz 且不带声道布局，后面接 aresample 会报
                 # “Cannot select channel layout”而整条导出失败，这里用 aformat 把格式写死
                 f"aformat=sample_rates=48000:channel_layouts=stereo[a]")
    return ";".join(parts)


def mux(video, narration, out, music=None, sfx=None, duration=None, **override):
    """画面（无声）+ 配音（可省）+ 配乐 + 音效 → 成片 mp4"""
    opt = {**MIX, **override}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ins = ["-i", str(video)] + (["-i", str(narration)] if narration else []) \
        + (["-i", str(music)] if music else []) + (["-i", str(sfx)] if sfx else [])
    measured = _measure(ins, _graph(1, bool(narration), bool(music), bool(sfx), opt))
    cmd = [FF, "-y", "-v", "error", *ins, "-filter_complex", _graph(1, bool(narration), bool(music), bool(sfx), opt, measured),
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           *(["-t", f"{duration:.3f}"] if duration else []), "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def mix_audio(narration, out, music=None, sfx=None, duration=None, **override):
    """只混音频（试听、对比用），输出 .wav 或 .m4a；narration 传 None 就是纯音乐版"""
    opt = {**MIX, **override}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    ins = (["-i", str(narration)] if narration else []) + (["-i", str(music)] if music else []) \
        + (["-i", str(sfx)] if sfx else [])
    codec = ["-c:a", "aac", "-b:a", "192k"] if str(out).endswith(".m4a") else []
    measured = _measure(ins, _graph(0, bool(narration), bool(music), bool(sfx), opt))
    cmd = [FF, "-y", "-v", "error", *ins, "-filter_complex",
           _graph(0, bool(narration), bool(music), bool(sfx), opt, measured), "-map", "[a]",
           *codec, *(["-t", f"{duration:.3f}"] if duration else []), str(out)]
    subprocess.run(cmd, check=True)


def ducked_music(narration, music, out, **override):
    """只输出"被配音压低之后的配乐"（分析自动避让的效果用），单声道 wav"""
    opt = {**MIX, **override}
    g = (f"[0:a]aresample=48000[key];[1:a]aresample=48000,volume={opt['music_db']}dB[m0];"
         f"[m0][key]{_duck(opt)}[a]")
    subprocess.run([FF, "-y", "-v", "error", "-i", str(narration), "-i", str(music), "-filter_complex", g, "-map", "[a]",
                    "-ac", "1", str(out)], check=True)


def loudness(path):
    """整体响度（LUFS）和真峰值（dBTP），用 ffmpeg 的 ebur128 测"""
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return lufs, peak


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x.reshape(-1, ch).mean(1), sr


def rms_db(x, sr, t0, t1):
    seg = x[int(t0 * sr):int(t1 * sr)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else float("nan")
