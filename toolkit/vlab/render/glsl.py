"""GLSL 片元着色器 → 视频片段（moderngl 离屏渲染，所有视频共用）。

用法（在别的脚本里）:
    from vlab.render.glsl import ShaderRenderer, render_clip
    from vlab.scenes import SHADERS
    r = ShaderRenderer(SHADERS / "atmosphere.frag", ss=2)
    render_clip(r, "out.mp4", n_frames=210, t0=0.0, uniforms=lambda t: {"uSunElev": 0.5}, overlay=None)

约定：
    着色器里必须有 uniform vec2 iResolution 和 uniform float iTime（和 Shadertoy 一样），其余 uniform 自定。
    分块渲染：单帧太重时一次画完可能超过 Windows 显卡超时（约 2 秒）导致驱动重置，所以按横条分块。
    overlay(t, PIL.Image) 可以在每帧上用 Pillow 画字，返回画好的图。
"""

import shutil
import subprocess
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

W, H = 1080, 1920
_VS = """#version 330
in vec2 pos;
void main() { gl_Position = vec4(pos, 0.0, 1.0); }
"""


class ShaderRenderer:
    def __init__(self, frag, ss: int = 1, tile: int = 160, size=(W, H)):
        self.ctx = moderngl.create_standalone_context(require=330)
        self.prog = self.ctx.program(vertex_shader=_VS, fragment_shader=Path(frag).read_text(encoding="utf-8"))
        vbo = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4").tobytes())
        self.vao = self.ctx.simple_vertex_array(self.prog, vbo, "pos")
        self.out_w, self.out_h = size
        self.w, self.h, self.ss, self.tile = size[0] * ss, size[1] * ss, ss, tile * ss
        self.fbo = self.ctx.simple_framebuffer((self.w, self.h), components=4)
        self.fbo.use()
        self.set(iResolution=(float(self.w), float(self.h)))

    def set(self, **uniforms):
        for k, v in uniforms.items():
            if k in self.prog:            # 着色器里没用到的 uniform 会被编译器优化掉，跳过
                self.prog[k].value = v

    def frame(self, t: float, **uniforms) -> np.ndarray:
        self.set(iTime=float(t), **uniforms)
        for y in range(0, self.h, self.tile):
            self.ctx.scissor = (0, y, self.w, min(self.tile, self.h - y))
            self.vao.render(moderngl.TRIANGLE_STRIP)
            self.ctx.finish()
        self.ctx.scissor = None
        img = np.frombuffer(self.fbo.read(components=3, alignment=1), np.uint8).reshape(self.h, self.w, 3)[::-1]
        if self.ss > 1:
            img = np.asarray(Image.fromarray(img).resize((self.out_w, self.out_h), Image.LANCZOS))
        return np.ascontiguousarray(img)


def open_encoder(out, fps: int = 30, size=(W, H), crf: int = 17):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([shutil.which("ffmpeg") or "ffmpeg", "-y", "-v", "error", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                             "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)


def render_clip(r: ShaderRenderer, out, n_frames: int, t0: float = 0.0, fps: int = 30,
                uniforms=None, overlay=None, log_every: int = 60) -> None:
    """渲染 n_frames 帧：第 i 帧的时间是 t0 + i/fps。uniforms(t) 返回这一帧的额外 uniform。"""
    enc = open_encoder(out, fps, (r.out_w, r.out_h))
    for i in range(n_frames):
        t = t0 + i / fps
        img = r.frame(t, **(uniforms(t) if uniforms else {}))
        if overlay:
            img = np.asarray(overlay(t, Image.fromarray(img)).convert("RGB"))
        enc.stdin.write(img.tobytes())
        if log_every and i % log_every == 0:
            print(f"    {Path(out).name}: 帧 {i}/{n_frames}")
    enc.stdin.close()
    enc.wait()
