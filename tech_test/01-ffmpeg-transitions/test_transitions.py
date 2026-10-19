"""FFmpeg 转场效果测试

测试各种转场效果，生成对比视频。

用法：
    python test_transitions.py

输出：
    renders/transitions_demo.mp4
"""

import subprocess
from pathlib import Path

FFMPEG = r"d:\Projects\personal_ip\AI-Vedio\tools\bin\ffmpeg.exe"
OUT_DIR = Path(__file__).parent / "renders"
OUT_DIR.mkdir(exist_ok=True)

# 生成测试素材（彩色条）
def generate_test_clips():
    """生成 3 个 5 秒的彩色条视频"""
    clips = []
    colors = ["red", "green", "blue"]
    for i, color in enumerate(colors):
        out = OUT_DIR / f"clip_{i}.mp4"
        cmd = [
            FFMPEG, "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d=5",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration=5",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            str(out)
        ]
        subprocess.run(cmd, check=True)
        clips.append(out)
    return clips

# 转场效果列表
TRANSITIONS = [
    ("fade", "淡入淡出"),
    ("wipeleft", "向左擦除"),
    ("wiperight", "向右擦除"),
    ("wipeup", "向上擦除"),
    ("wipedown", "向下擦除"),
    ("slideleft", "向左滑动"),
    ("slideright", "向右滑动"),
    ("circleopen", "圆形打开"),
    ("circleclose", "圆形关闭"),
    ("pixelize", "像素化"),
    ("radial", "径向"),
    ("smoothleft", "平滑向左"),
    ("smoothright", "平滑向右"),
    ("smoothup", "平滑向上"),
    ("smoothdown", "平滑向下"),
    ("circlecrop", "圆形裁剪"),
    ("rectcrop", "矩形裁剪"),
    ("distance", "距离"),
    ("fadeblack", "黑色淡入"),
    ("fadewhite", "白色淡入"),
]

def apply_transition(clip1, clip2, transition, duration=1.0):
    """应用转场效果"""
    out = OUT_DIR / f"trans_{transition}.mp4"
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-i", str(clip1),
        "-i", str(clip2),
        "-filter_complex", f"[0:v][1:v]xfade=transition={transition}:duration={duration}:offset=4[outv]",
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        str(out)
    ]
    subprocess.run(cmd, check=True)
    return out

def concat_videos(videos, output):
    """拼接多个视频"""
    list_file = OUT_DIR / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{v}'" for v in videos), encoding="utf-8")
    
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy",
        str(output)
    ]
    subprocess.run(cmd, check=True)

def main():
    print("生成测试素材...")
    clips = generate_test_clips()
    
    print("应用转场效果...")
    results = []
    for trans, name in TRANSITIONS:
        print(f"  {name} ({trans})...")
        out = apply_transition(clips[0], clips[1], trans)
        results.append(out)
    
    print("拼接所有转场...")
    final = OUT_DIR / "transitions_demo.mp4"
    concat_videos(results, final)
    print(f"完成 → {final}")

if __name__ == "__main__":
    main()
