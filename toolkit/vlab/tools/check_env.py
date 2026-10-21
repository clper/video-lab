"""环境自检：克隆后（或换机器后）第一件事跑这个，缺什么、怎么补一次列清楚。

用法（在仓库根目录）:
    uv sync                              # 先按 uv.lock 建好 .venv（同时把 vlab 装成命令）
    uv run vlab-check

分两级：
    必需 —— 缺了就不能用（看成片不需要，但任何构建都需要），退出码非 0
    按需 —— 只在特定操作时需要（重渲染着色器镜头要显卡、重新配音要联网、000 的 HyperFrames 版要 Node）
"""

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]      # toolkit/vlab/tools/check_env.py → 仓库根


def main() -> None:
    global results
    results = []          # (级别, 是否通过, 项目, 说明/修复办法)


    def check(level, name, ok, detail):
        results.append((level, ok, name, detail))


    # ---------- 必需 ----------
    in_venv = Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    check("必需", "Python 环境用的是仓库的 .venv", in_venv,
          f"当前 {sys.prefix}" if in_venv else f"当前是 {sys.prefix}；在仓库根目录运行 `uv sync`，再用 `uv run python ...` 执行")
    check("必需", "Python ≥ 3.11", sys.version_info >= (3, 11), sys.version.split()[0])

    for mod, why in [("manim", "Manim 动画"), ("edge_tts", "配音"), ("PIL", "图文/字幕叠加"), ("numpy", "程序化画面"),
                     ("moderngl", "着色器渲染"), ("yaml", "视频工程文件")]:
        try:
            m = importlib.import_module(mod)
            check("必需", f"Python 包 {mod}（{why}）", True, getattr(m, "__version__", "已安装"))
        except Exception as e:  # noqa: BLE001
            check("必需", f"Python 包 {mod}（{why}）", False, f"{e}；运行 `uv sync`")

    for exe in ("ffmpeg", "ffprobe"):
        path = shutil.which(exe)
        if path:
            ver = subprocess.run([exe, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
            check("必需", exe, True, ver[:60])
        else:
            check("必需", exe, False, "没在 PATH 上；Windows 可 `winget install Gyan.FFmpeg`，装完重开终端")

    try:
        import manimpango
        fonts = set(manimpango.list_fonts())
        for f in ("Microsoft YaHei", "Cascadia Mono"):
            check("必需", f"字体 {f}（Manim 用）", f in fonts,
                  "可用" if f in fonts else "没装；Manim 会悄悄换成别的字体，画面和成片不一致。Cascadia Mono 可 `winget install Microsoft.CascadiaCode`")
    except Exception as e:  # noqa: BLE001
        check("必需", "字体检查", False, f"manimpango 不可用：{e}")
    for p in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"):
        check("必需", f"字体文件 {Path(p).name}（Pillow 叠字用）", Path(p).exists(), "存在" if Path(p).exists() else "缺失：需要 Windows 自带的微软雅黑")

    # ---------- 按需 ----------
    try:
        import moderngl
        ctx = moderngl.create_standalone_context(require=330)
        check("按需", "显卡 OpenGL 3.3（重渲染着色器镜头）", True, ctx.info["GL_RENDERER"])
        ctx.release()
    except Exception as e:  # noqa: BLE001
        check("按需", "显卡 OpenGL 3.3（重渲染着色器镜头）", False,
              f"{str(e)[:80]}；只影响重渲染 003 hook/noon/sunset 和 research/visual/07，拼接成片不需要")

    node = shutil.which("node")
    check("按需", "Node.js（000 的 HyperFrames 版）", bool(node),
          subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() if node else "没装；只影响 archive/000 的 2_hyperframes")
    hf = ROOT / "archive" / "000-claude-video-lab" / "2_hyperframes"
    check("按需", "000 的 node_modules", (hf / "node_modules").exists(),
          "已安装" if (hf / "node_modules").exists() else f"在 {hf.relative_to(ROOT)} 里运行 `npm ci`（PowerShell 下用 `npm.cmd ci`）")

    # ---------- 成果是否齐全（克隆是否完整） ----------
    expect = ["videos/001-float-precision/renders/float-precision_final.mp4",
              "videos/002-mobius-strip/renders/mobius-strip_final.mp4",
              "videos/003-sunset-red/renders/sunset-red_final.mp4", "videos/003-sunset-red/media/clips/hook.mp4",
              "videos/003-sunset-red/build/sunset-red/timeline.json", "research/visual/08-video-spec/media/clips/landscape/intro.hash"]
    missing = [e for e in expect if not (ROOT / e).exists()]
    check("必需", "仓库里的成片和分镜片段", not missing, "齐全" if not missing else f"缺：{missing}（克隆不完整，或用了 Git LFS 但没 `git lfs pull`）")

    # ---------- 输出 ----------
    width = max(len(r[2]) for r in results)
    bad_required = False
    for level in ("必需", "按需"):
        print(f"\n【{level}】")
        for lv, ok, name, detail in results:
            if lv != level:
                continue
            print(f"  {'✓' if ok else '✗'} {name.ljust(width)}  {detail}")
            bad_required |= (lv == "必需" and not ok)
    print("\n结论：" + ("必需项有缺失，按上面的提示补齐后再跑一次" if bad_required else "必需项全部通过，可以构建"))
    sys.exit(1 if bad_required else 0)


if __name__ == "__main__":
    main()
