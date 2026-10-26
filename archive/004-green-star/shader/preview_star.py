"""星空着色器单帧自检：几秒出一张图，看构图和颜色对不对。"""
import sys
from pathlib import Path

from PIL import Image

from vlab.render.glsl import ShaderRenderer
from vlab.scenes import SHADERS

W, H = 1920, 1080
out = Path(sys.argv[1] if len(sys.argv) > 1 else "star_preview.png")
r = ShaderRenderer(SHADERS / "starfield.frag", ss=1, size=(W, H))
shots = [(0.0, dict(uDrift=0.01, uZoom=1.0, uDim=0.0, uGreenTry=0.0, uTwinkle=1.0)),
         (3.0, dict(uDrift=0.01, uZoom=1.0, uDim=0.0, uGreenTry=0.9, uTwinkle=1.0)),
         (6.0, dict(uDrift=0.01, uZoom=1.0, uDim=0.55, uGreenTry=0.0, uTwinkle=0.4))]
sheet = Image.new("RGB", (W // 2, H // 2 * len(shots)))
for i, (t, u) in enumerate(shots):
    sheet.paste(Image.fromarray(r.frame(t, **u)).resize((W // 2, H // 2), Image.LANCZOS), (0, H // 2 * i))
sheet.save(out)
print("→", out)
