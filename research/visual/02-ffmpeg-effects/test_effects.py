"""FFmpeg 视频特效测试

测试各种视频滤镜效果。

用法：
    python test_effects.py

输出：
    renders/effects_demo.mp4
"""

import shutil
import subprocess
from pathlib import Path

# 先找仓库里的 toolkit/bin/ffmpeg.exe（原开发机），没有就用 PATH 上的 ffmpeg
_LOCAL_FFMPEG = Path(__file__).resolve().parents[3] / "toolkit" / "bin" / "ffmpeg.exe"
FFMPEG = str(_LOCAL_FFMPEG) if _LOCAL_FFMPEG.exists() else (shutil.which("ffmpeg") or "ffmpeg")
OUT_DIR = Path(__file__).parent / "renders"
OUT_DIR.mkdir(exist_ok=True)

# 生成测试素材（彩色渐变）
def generate_test_clip():
    """生成 10 秒的彩色渐变视频"""
    out = OUT_DIR / "test_clip.mp4"
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:d=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
        "-vf", "geq=r='X/W*255':g='Y/H*255':b='128'",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        str(out)
    ]
    subprocess.run(cmd, check=True)
    return out

# 特效列表
EFFECTS = [
    ("blur", "boxblur=10:1", "模糊"),
    ("sharpen", "unsharp=5:5:1.0:5:5:0.0", "锐化"),
    ("negate", "negate", "反色"),
    ("sepia", "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131", "复古"),
    ("grayscale", "hue=s=0", "灰度"),
    ("vintage", "curves=vintage", "复古色调"),
    ("cross_process", "curves=cross_process", "交叉冲印"),
    ("brighten", "eq=brightness=0.2:contrast=1.2", "提亮"),
    ("darken", "eq=brightness=-0.2:contrast=1.2", "压暗"),
    ("invert", "negate", "反相"),
    ("edge", "edgedetect=low=0.1:high=0.4", "边缘检测"),
    ("pixelate", "scale=iw/10:ih/10,scale=iw*10:ih*10:flags=neighbor", "像素化"),
    ("wave", "geq=r='r(X,Y)':g='g(X,Y)':b='b(X+sin(Y/10)*20,Y)'", "波浪扭曲"),
    ("vignette", "vignette=PI/4", "暗角"),
    ("noise", "noise=alls=20:allf=t+u", "噪点"),
]

def apply_effect(clip, name, filter_str):
    """应用特效"""
    out = OUT_DIR / f"effect_{name}.mp4"
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-i", str(clip),
        "-vf", filter_str,
        "-c:v", "libx264", "-c:a", "copy",
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
    clip = generate_test_clip()
    
    print("应用特效...")
    results = []
    for name, filter_str, desc in EFFECTS:
        print(f"  {desc} ({name})...")
        out = apply_effect(clip, name, filter_str)
        results.append(out)
    
    print("拼接所有特效...")
    final = OUT_DIR / "effects_demo.mp4"
    concat_videos(results, final)
    print(f"完成 → {final}")

if __name__ == "__main__":
    main()
