"""着色器光线步进测试：云海飞越雪山（GLSL 在显卡上逐像素计算，moderngl 离屏渲染）

画面全部由 vlab/scenes/shaders/cloudsea.frag 一个片元着色器算出：程序化山地、体积云海、天空和大气雾，
没有贴图和模型（003 的开场也用同一个着色器）。渲染器是 vlab/render/glsl.py（分块渲染，防 Windows 显卡超时）。

用法（任意目录）：
    uv run python lab/07-shader-raymarch/render_shader.py --still 3       # 只出一帧 PNG，调画面用
    uv run python lab/07-shader-raymarch/render_shader.py                 # 成片 renders/cloudsea.mp4
    uv run python lab/07-shader-raymarch/render_shader.py --ss 2          # 2×2 超采样抗锯齿（慢 4 倍）

依赖：支持 OpenGL 3.3 的显卡、PATH 上的 ffmpeg。
"""

import argparse
import time
from pathlib import Path

from PIL import Image

from vlab.render.glsl import ShaderRenderer, render_clip
from vlab.scenes import SHADERS

OUT_DIR = Path(__file__).resolve().parent / "renders"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--ss", type=int, default=1, help="超采样倍数，2 = 2×2")
    ap.add_argument("--still", type=float, default=None, help="只渲染这一秒的一帧 PNG")
    ap.add_argument("--out", default=str(OUT_DIR / "cloudsea.mp4"))
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    r = ShaderRenderer(SHADERS / "cloudsea.frag", ss=args.ss)
    print("显卡：", r.ctx.info["GL_RENDERER"])
    t0 = time.time()
    if args.still is not None:
        p = OUT_DIR / f"cloudsea_still_{args.still:.1f}s.png"
        Image.fromarray(r.frame(args.still)).save(p)
        print(f"静帧 → {p}（{time.time() - t0:.2f}s）")
        return
    n = int(args.seconds * args.fps)
    render_clip(r, args.out, n, t0=0.0, fps=args.fps, log_every=30)
    print(f"成片 → {args.out}（{n} 帧，用时 {time.time() - t0:.0f}s）")


if __name__ == "__main__":
    main()
