"""为 001-float-precision 生成配音 + 时间轴

用法：
    python tts.py

输出：
    build/float/narration.wav   - 整条配音
    build/float/timeline.json   - 时间轴（每个分镜 + 每个词的时间点）
"""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

import edge_tts

# ---------- 配置 ----------
CONTENT = Path(__file__).parent / "content" / "float.json"
BUILD = Path(__file__).parent / "build" / "float"
VOICE = "zh-CN-YunxiNeural"  # 男声，清晰
RATE = "+10%"

# ---------- 读稿子 ----------
script = json.loads(CONTENT.read_text(encoding="utf-8"))
scenes = script["scenes"]

# ---------- 生成每个分镜的配音 ----------
async def gen_scene_audio(scene, out_path):
    communicate = edge_tts.Communicate(scene["narration"], VOICE, rate=RATE)
    await communicate.save(str(out_path))

async def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp())
    
    print(f"生成 {len(scenes)} 个分镜的配音...")
    for i, scene in enumerate(scenes):
        out = temp_dir / f"{scene['id']}.mp3"
        await gen_scene_audio(scene, out)
        print(f"  {scene['id']}: {scene['narration'][:30]}...")
    
    # 拼接所有配音
    concat_list = BUILD / "concat.txt"
    concat_list.write_text("\n".join(f"file '{temp_dir / s['id']}.mp3'" for s in scenes), encoding="utf-8")
    
    narration = BUILD / "narration.wav"
    subprocess.run([
        "d:\\Projects\\personal_ip\\AI-Vedio\\tools\\bin\\ffmpeg.exe",
        "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
        str(narration)
    ], check=True)
    print(f"配音已保存：{narration}")
    
    # 生成 timeline.json（词的时间点按均匀分布估算）
    # 注：这是简化版，实际应该用语音识别对齐
    timeline = {"id": script["id"], "scenes": []}
    current_time = 0.0
    
    for scene in scenes:
        # 估算每个分镜的时长（按字数 × 0.3 秒/字）
        duration = len(scene["narration"]) * 0.3
        words = []
        # 把 narration 按字拆分，均匀分配到这段时间
        chars = list(scene["narration"])
        for j, char in enumerate(chars):
            if char.strip():  # 跳过空格
                words.append({
                    "text": char,
                    "start": current_time + (j / len(chars)) * duration,
                    "end": current_time + ((j + 1) / len(chars)) * duration
                })
        
        timeline["scenes"].append({
            "id": scene["id"],
            "headline": scene["headline"],
            "start": current_time,
            "end": current_time + duration,
            "words": words
        })
        current_time += duration
    
    timeline["duration"] = current_time
    timeline_path = BUILD / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"时间轴已保存：{timeline_path}")
    print(f"总时长：{current_time:.1f} 秒")

if __name__ == "__main__":
    asyncio.run(main())
