"""稿子 → 配音 + 时间轴 + 字幕（三种做法共用）。

先配音、后做画面：每个分镜单独合成一段语音，拿到真实时长和每个词的时间点，
画面再按这个时间轴去对齐。

用法（任意目录）:
       uv run vlab-tts archive/001-float-precision/content/float.json
稿子里可以写 "aspect": "landscape" 出横屏（1920x1080），不写就是竖屏（1080x1920）。
分镜里写 "no_sub": true，这一句照常配音、进时间轴，但不出字幕（画面上用大字代替，同一句不出现两遍）。
产物写到稿子所在项目的 build 目录（稿子在 <项目>/content/ 下）:
       <项目>/build/<id>/narration.wav   整条配音
       <项目>/build/<id>/timeline.json   分镜起止时间、每个词的时间点、字幕条
       <项目>/build/<id>/subs.ass / subs.srt
"""

import asyncio
import json
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts

from vlab import fonts

SAMPLE_RATE = 24000
LEAD = 0.25  # 画面切进来后，停多久再开口
TRAIL = 0.35  # 这段说完后，留多久再切下一个画面
END_HOLD = 1.6  # 片尾多停一会儿
# 画幅：竖屏给手机，横屏给 B 站这类以横屏为主的平台。字幕字号、边距、每行字数都跟着画幅走。
ASPECTS = {
    "portrait": dict(width=1080, height=1920, font=64, margin_v=420, margin_h=70, max_line=13),
    "landscape": dict(width=1920, height=1080, font=56, margin_v=70, margin_h=200, max_line=22),
}
DEFAULT_ASPECT = "portrait"
BREAK_PUNCT = "，。：；？！,.:;?!"  # 遇到这些标点就断开字幕
STRIP_PUNCT = "，。：；、,.:;"  # 字幕里去掉的标点（问号、感叹号保留）


async def synth(text: str, voice: str, rate: str) -> tuple[bytes, list[dict]]:
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio = bytearray()
    words = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 1e7
            words.append({"text": chunk["text"], "start": start, "end": start + chunk["duration"] / 1e7})
    return bytes(audio), words


def mp3_to_pcm(mp3_path: Path) -> bytes:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(mp3_path), "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"],
        check=True,
        capture_output=True,
    )
    return result.stdout


def normalize(src: Path, dst: Path) -> None:
    """响度拉到 -16 LUFS（Edge TTS 原声约 -23，放到短视频平台上偏小），时长不变。"""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True,
    )


def silence(seconds: float) -> bytes:
    return b"\x00\x00" * round(seconds * SAMPLE_RATE)


def align_words(text: str, words: list[dict]) -> list[dict]:
    """把 WordBoundary 的词对回原文，补上词之间被跳过的字符和词后面的标点。"""
    cursor = 0
    aligned = []
    for w in words:
        pos = text.find(w["text"], cursor)
        end = pos + len(w["text"]) if pos >= 0 else cursor
        shown = text[cursor:end]
        cursor = end
        trailing = ""
        while cursor < len(text) and text[cursor] in BREAK_PUNCT + "、":
            trailing += text[cursor]
            cursor += 1
        aligned.append({**w, "shown": shown, "trailing": trailing})
    if aligned and cursor < len(text):
        aligned[-1]["trailing"] += text[cursor:]
    return aligned


def make_cues(aligned: list[dict], max_line: int) -> list[dict]:
    cues = []
    line: list[dict] = []
    for i, w in enumerate(aligned):
        line.append(w)
        length = sum(len(x["shown"]) for x in line)
        nxt = len(aligned[i + 1]["shown"]) if i + 1 < len(aligned) else 0
        breaks = any(p in w["trailing"] for p in BREAK_PUNCT)
        if breaks or length + nxt > max_line or i == len(aligned) - 1:
            text = "".join(x["shown"] + x["trailing"] for x in line).strip(STRIP_PUNCT + " ")
            text = text.lstrip(BREAK_PUNCT + "、")
            if text:
                cues.append({"start": line[0]["start"], "end": line[-1]["end"], "text": text})
            line = []
    return cues


def ass_time(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def build_grid(content: dict, content_path: Path) -> None:
    """拍格时间轴：没有旁白，时长由 BPM 的拍子定。

    用于「纯音乐 + 字幕」这类片子：句子不靠配音量时长，而是每镜占固定几拍（hold），
    全片总长 = 总拍数 × 每拍秒数。产物只有 timeline.json / subs.ass / subs.srt，不出音频。
    """
    aspect_name = content.get("aspect", "landscape")
    if aspect_name not in ASPECTS:
        sys.exit(f"aspect 只能是 {' 或 '.join(ASPECTS)}，稿子里写的是 {aspect_name!r}")
    aspect = ASPECTS[aspect_name]
    beat = float(content["grid"]["beat"])
    fps = int(content.get("fps", 30))
    project = content_path.resolve().parent.parent
    out_dir = project / "build" / content["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    # 同一个工程从「有旁白」改成「拍格」时，旧配音会残留在 build 里，混音会把旧人声又合进去
    (out_dir / "narration.wav").unlink(missing_ok=True)

    t = 0.0
    scenes, cues = [], []
    for scene in content["scenes"]:
        hold = float(scene["hold"])
        start, end = t, t + hold * beat
        text = (scene.get("text") or "").strip()
        if text and not scene.get("no_sub"):
            cin = float(scene.get("sub_in") if scene.get("sub_in") is not None else 0.15)
            cout = float(scene.get("sub_out") if scene.get("sub_out") is not None else 0.20)
            c0, c1 = start + cin, max(start + cin + 0.6, end - cout)
            cues.append({"start": round(c0, 3), "end": round(c1, 3), "text": text})
        scenes.append({**scene, "start": round(start, 3), "end": round(end, 3),
                       "width": aspect["width"], "height": aspect["height"],
                       "voice_start": None, "voice_end": None, "words": []})
        print(f"  {scene['id']:<10} {start:6.2f}s → {end:6.2f}s   {hold:g} 拍   {text or '（无字幕）'}")
        t = end

    timeline = {
        "id": content["id"],
        "title": content["title"],
        "mode": "grid",
        "aspect": aspect_name,
        "width": aspect["width"],
        "height": aspect["height"],
        "fps": fps,
        "bpm": content["grid"]["bpm"],
        "beat": beat,
        "duration": round(t, 3),
        "scenes": scenes,
        "cues": cues,
    }
    (out_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    # 字幕自己也淡入淡出 0.15s。dip 只压得住画面，压不住后烧的字幕：
    # 006 开片实测过——画面才 25% 亮度，字幕已经全亮地悬在黑暗里。
    FADE = r"{\fad(150,150)}"
    ass = ass_header(aspect) + "".join(
        f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{FADE}{c['text']}\n" for c in cues
    )
    (out_dir / "subs.ass").write_text(ass, encoding="utf-8-sig")
    srt = "".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n" for i, c in enumerate(cues, 1))
    (out_dir / "subs.srt").write_text(srt, encoding="utf-8")
    print(f"总时长 {t:.2f}s（{round(t / beat):g} 拍），{len(cues)} 条字幕 → {out_dir}")


def ass_header(a: dict) -> str:
    """字幕样式。字号和边距按画幅给，横屏字幕贴底，竖屏抬高到安全区以上。"""
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {a["width"]}
PlayResY: {a["height"]}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{fonts.FAMILY},{a["font"]},&H00FFFFFF,&H00FFFFFF,&H00101114,&H64000000,-1,0,0,0,100,100,2,0,1,5,2,2,{a["margin_h"]},{a["margin_h"]},{a["margin_v"]},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


async def main(content_path: Path) -> None:
    # 剧本闸门：videos/ 下的正式视频，剧本没被项目负责人确认之前不许配音（process/SCRIPT-REVIEW.md）
    from vlab.tools import script_gate
    script_gate.require_confirmed(content_path, "配音或生成时间轴")
    content = json.loads(content_path.read_text(encoding="utf-8"))
    if content.get("mode") == "grid":
        build_grid(content, content_path)
        return
    aspect_name = content.get("aspect", DEFAULT_ASPECT)
    if aspect_name not in ASPECTS:
        sys.exit(f"aspect 只能是 {' 或 '.join(ASPECTS)}，稿子里写的是 {aspect_name!r}")
    aspect = ASPECTS[aspect_name]
    end_hold = float(content.get("end_hold", END_HOLD))   # 片尾多停多久，可以在稿子里覆盖
    # 每镜开口前 / 说完后留多久：镜头多的快切片要收紧（52 镜 × 0.6s 就是半分钟空白），稿子里写 lead / trail 覆盖
    lead = float(content.get("lead", LEAD))
    trail = float(content.get("trail", TRAIL))
    project = content_path.resolve().parent.parent      # <项目>/content/xxx.json → <项目>
    out_dir = project / "build" / content["id"]
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    pcm = bytearray()
    t = 0.0
    scenes, cues = [], []
    cue_limits = []        # 每条字幕最多能挂到哪一秒 = 它自己那一镜的结尾
    for i, scene in enumerate(content["scenes"]):
        text = (scene.get("narration") or "").strip()
        if text:
            audio, words = await synth(text, content["voice"], content["rate"])
            mp3 = seg_dir / f"{i:02d}_{scene['id']}.mp3"
            mp3.write_bytes(audio)
            seg = mp3_to_pcm(mp3)
            seg_len = len(seg) / 2 / SAMPLE_RATE
            if not words:
                sys.exit(f"分镜 {scene['id']} 没有拿到词时间点，检查网络或 edge-tts 版本")
        else:
            # 呼吸镜：没有旁白，画面自己演。以前这里会因为拿不到词而直接退出，
            # 所以有旁白的片子里插不进空镜——007《回归》需要 6 个呼吸镜，才加的这条路。
            words, seg, seg_len = [], b"", 0.0

        voice_start = t + lead
        tail = trail + (end_hold if i == len(content["scenes"]) - 1 else 0)
        # 镜头最短时长 min_hold（秒）：呼吸镜至少要停够（不然 0.6 秒一闪而过），
        # 有旁白的镜头也能靠它把节奏压整齐。不写 = 0，行为和以前完全一样。
        pad = max(0.0, float(scene.get("min_hold") or 0) - (lead + seg_len + tail))
        pcm += silence(lead) + seg + silence(tail + pad)
        end = voice_start + seg_len + tail + pad

        aligned = align_words(text, words)
        for w in aligned:
            w["start"] += voice_start
            w["end"] += voice_start
        scene_cues = make_cues(aligned, aspect["max_line"])
        if i == len(content["scenes"]) - 1 and len(scene_cues) > 1:
            # 收尾镜头不按标点切：金句要整句停在画面上（切碎了只剩半句，看不出是收尾）
            whole = "".join(w["shown"] + w["trailing"] for w in aligned).strip()
            whole = whole.rstrip(STRIP_PUNCT + " ")
            scene_cues = [{"start": scene_cues[0]["start"], "end": scene_cues[-1]["end"], "text": whole}]
        if scene.get("no_sub"):
            scene_cues = []        # 这一句画面上用大字给，不烧字幕（008 的开场问句和落点）
        cues += scene_cues
        cue_limits += [round(end, 3)] * len(scene_cues)

        scenes.append(
            {
                **scene,
                "start": round(t, 3),
                "end": round(end, 3),
                "width": aspect["width"],
                "height": aspect["height"],
                "voice_start": round(voice_start, 3),
                "voice_end": round(voice_start + seg_len, 3),
                "words": [{"text": w["shown"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in aligned],
            }
        )
        print(f"  {scene['id']:<10} {t:6.2f}s → {end:6.2f}s   {len(words)} 个词, {len(scene_cues)} 条字幕")
        t = end

    # 字幕之间的小空隙补齐（避免一闪一闪），其余的多停 0.3 秒但不压到下一条
    for i, c in enumerate(cues):
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else None
        if nxt is not None and nxt - c["end"] < 0.6:
            c["end"] = nxt
        else:
            c["end"] = min(c["end"] + 0.3, nxt) if nxt is not None else c["end"] + 0.3
        c["start"], c["end"] = round(c["start"], 3), round(c["end"], 3)

    # 最后一句停到片尾：收尾金句得留在屏幕上，不能说完就消失（空镜白留着）
    # 但只能停到它自己那一镜的结尾：008 片尾三镜是 no_sub 的大字 + 片尾卡，
    # 一路拖到片尾会让「都是一个新的世界」压在大字和片名上 13 秒
    if cues and cues[-1]["end"] < t - 0.1:
        limit = min(t - 0.1, cue_limits[-1] - 0.2) if cue_limits else t - 0.1
        cues[-1]["end"] = round(max(cues[-1]["end"], limit), 3)

    raw = seg_dir / "narration_raw.wav"
    with wave.open(str(raw), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(bytes(pcm))
    normalize(raw, out_dir / "narration.wav")

    timeline = {
        "id": content["id"],
        "title": content["title"],
        "aspect": aspect_name,
        "width": aspect["width"],
        "height": aspect["height"],
        "fps": 30,
        "duration": round(t, 3),
        "scenes": scenes,
        "cues": cues,
    }
    (out_dir / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    # 字幕自己也淡入淡出 0.15s。dip 只压得住画面，压不住后烧的字幕：
    # 006 开片实测过——画面才 25% 亮度，字幕已经全亮地悬在黑暗里。
    FADE = r"{\fad(150,150)}"
    ass = ass_header(aspect) + "".join(
        f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{FADE}{c['text']}\n" for c in cues
    )
    (out_dir / "subs.ass").write_text(ass, encoding="utf-8-sig")
    srt = "".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n" for i, c in enumerate(cues, 1))
    (out_dir / "subs.srt").write_text(srt, encoding="utf-8")

    print(f"总时长 {t:.2f}s，{len(cues)} 条字幕 → {out_dir}")


def cli() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法：vlab-tts <项目>/content/<稿子>.json")
    asyncio.run(main(Path(sys.argv[1])))


if __name__ == "__main__":
    cli()
