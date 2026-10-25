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


def _marks() -> tuple[str, str]:
    """勾叉只在控制台能编码时才用：Windows 默认 GBK 控制台里 ✓（U+2713）不在码表，
    直接 print 会抛 UnicodeEncodeError，整份自检结果全看不到。"""
    enc = sys.stdout.encoding or "utf-8"
    try:
        "✓".encode(enc)
        return "✓", "✗"
    except (UnicodeEncodeError, LookupError):
        return "OK", "NG"


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

    # 项目字体：思源黑体，随仓库入库（vlab/assets/fonts），Manim、Pillow、字幕都用它
    try:
        from vlab import fonts as vfonts
        miss = [p.name for p in (vfonts.REGULAR, vfonts.BOLD, vfonts.LICENSE) if not p.exists()]
        if miss:
            check("必需", "项目字体 思源黑体", False, f"缺 {miss}：它们应随仓库入库，检查克隆是否完整")
        else:
            vfonts.register_manim()
            check("必需", "项目字体 思源黑体（Manim、Pillow、字幕）", True, f"{vfonts.FAMILY}，已注册给 Manim")
    except Exception as e:  # noqa: BLE001
        check("必需", "项目字体 思源黑体", False, f"Manim 注册失败：{e}")

    # 旧片子的字体：001–003 和早期试验还没换字体，只有重渲它们时才需要
    try:
        import manimpango
        installed = set(manimpango.list_fonts())
    except Exception:  # noqa: BLE001
        installed = set()
    for f, why in (("Microsoft YaHei", "重渲 001–003 和早期试验；不能用于商业发布"),
                   ("Cascadia Mono", "重渲 001 的代码字体；`winget install Microsoft.CascadiaCode`")):
        check("按需", f"字体 {f}", f in installed, "可用" if f in installed else f"没装；只影响{why}")

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
              "videos/003-sunset-red/build/sunset-red/timeline.json", "research/visual/08-video-spec/media/clips/landscape/intro.hash",
              "videos/004-green-star/renders/green-star.mp4", "videos/004-green-star/media/clips/s01_sky.mp4"]
    missing = [e for e in expect if not (ROOT / e).exists()]
    check("必需", "仓库里的成片和分镜片段", not missing, "齐全" if not missing else f"缺：{missing}（克隆不完整，或用了 Git LFS 但没 `git lfs pull`）")

    # ---------- 输出 ----------
    yes, no = _marks()
    width = max(len(r[2]) for r in results)
    bad_required = False
    for level in ("必需", "按需"):
        print(f"\n【{level}】")
        for lv, ok, name, detail in results:
            if lv != level:
                continue
            print(f"  {yes if ok else no} {name.ljust(width)}  {detail}")
            bad_required |= (lv == "必需" and not ok)
    print("\n结论：" + ("必需项有缺失，按上面的提示补齐后再跑一次" if bad_required else "必需项全部通过，可以构建"))
    sys.exit(1 if bad_required else 0)


if __name__ == "__main__":
    main()
