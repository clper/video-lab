"""
Remotion 渲染桥：把「一张镜头卡 + 一组参数」渲染成一个 mp4。

设计：
    - 只有一处会调 Node（npx remotion render），其余全是纯 Python，好测也好查。
    - 卡名以 cards/registry.ts 为准，Python 侧不重复维护一份名单（解析文件即可）。
    - 产物统一落在 <项目>/media/remotion/<镜头>.mp4，和 Manim 的 media/manim 并列。

用法（任意目录）:
    uv run python -m vlab.render.remotion_bridge --list
    uv run python -m vlab.render.remotion_bridge --card flock --seconds 4 \
        --out media/remotion/S1.mp4 --param n=640 --param birth=true
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REMOTION_DIR = HERE / "remotion"
REGISTRY = REMOTION_DIR / "src" / "cards" / "registry.ts"
COMPOSITION = "Shot"
W, H = 1080, 1920
DEFAULT_FPS = 30
RENDER_TIMEOUT = 900      # 单镜上限（秒）。正常镜头 20–60s 出片，900s 只做卡死兜底


class RemotionError(RuntimeError):
    pass


def card_names() -> list[str]:
    """从 registry.ts 里读已登记的卡名（唯一事实来源在 TS 侧）。"""
    if not REGISTRY.exists():
        return []
    text = REGISTRY.read_text(encoding="utf-8")
    block = text.split("export const CARDS", 1)
    if len(block) < 2:
        return []
    body = block[1].split("};", 1)[0]
    return re.findall(r"^\s{2}(\w+):", body, flags=re.M)


def _npx() -> str:
    for name in ("npx.cmd", "npx"):
        found = shutil.which(name)
        if found:
            return found
    raise RemotionError("找不到 npx：先装 Node.js，或确认 PATH 里有 npx.cmd")


def node_ready() -> tuple[bool, str]:
    """环境自检：node 版本 + Remotion 依赖是否已安装。"""
    if not shutil.which("node"):
        return False, "找不到 node"
    if not (REMOTION_DIR / "node_modules" / "remotion").exists():
        return False, f"{REMOTION_DIR} 下没有 node_modules，先在那个目录跑 npm.cmd install"
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:  # pragma: no cover - 环境问题
        return False, f"node 跑不起来：{e}"
    return True, (out.stdout or "").strip()


def probe_duration(path) -> float:
    """用 ffprobe 读时长，给 build 做帧数校验用。"""
    exe = shutil.which("ffprobe")
    if not exe:
        return 0.0
    out = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration", "-of",
         "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def render_shot(
    card: str,
    out,
    seconds: float,
    params: dict | None = None,
    fps: int = DEFAULT_FPS,
    frames: int | None = None,
    fx: dict | None = None,
    t0: int | None = None,
    brand: str | None = None,
    slug: str | None = None,
    concurrency: int | None = None,
    quiet: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> Path:
    """渲染单个镜头。帧数优先用 frames，否则 round(seconds*fps)。返回产物路径。"""
    names = card_names()
    if names and card not in names:
        raise RemotionError(f"没有镜头卡「{card}」，可选：{', '.join(names)}")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    n_frames = frames if frames else max(1, round(seconds * fps))
    props = {"card": card, "params": params or {}, "durationInFrames": n_frames}
    # 画幅由工程定（竖屏 1080×1920 / 横屏 1920×1080），不传就用卡的默认值
    if width and height:
        props["width"], props["height"] = int(width), int(height)
    if fx:
        props["fx"] = fx
    # 本镜在全片的起始帧：给星尘/扫光/呼吸当“时钟”，切镜时背景相位不归零
    if t0:
        props["t0"] = int(t0)
    if brand:
        props["brand"] = brand
    if slug:
        props["slug"] = slug

    # props 走临时文件：Windows 上把 JSON 塞进命令行容易被引号吃掉
    fd, props_path = tempfile.mkstemp(suffix=".json", prefix="vlab_shot_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    # 并发：1080×1920 的镜头每个 Chrome tab 都很重，cpu//2 在多核机器上能开到十几个，
    # 偶发 node/chrome 卡死（进程在、CPU 不动，实测停在 particleText 上十多分钟）。
    # 默认封顶 4；超时重试时再降到 2。
    def _cmd(conc: int) -> list[str]:
        return [
            _npx(), "remotion", "render", "src/index.ts", COMPOSITION, str(out.resolve()),
            f"--props={props_path}",
            "--codec=h264",
            # Remotion 默认写全范围 yuvj420p，和着色器镜头的 yuv420p 不同。
            # 混着拼的时候 concat demuxer 会按首个文件的参数解其余文件，最后一镜整段丢帧，所以这里统一。
            "--pixel-format=yuv420p",
            "--color-space=bt709",
            # 暗场为主的竖屏片：默认 crf 18 在近黑背景上会留下一块块的压缩斑，
            # 16 对体积影响很小（暗场内容本来就压得动），背景干净很多。
            "--crf=16",
            f"--concurrency={conc}",
            "--log=error",
        ]

    conc = concurrency or min(4, max(2, (os.cpu_count() or 4) // 2))
    cmd = _cmd(conc)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", NODE_OPTIONS="--max-old-space-size=4096")
    # Windows 上 remotion 偶尔会卡死（node 进程还在、CPU 不动）：给超时，卡住就杀掉重试一次，
    # 不然整个构建会一直挂着，看起来像“渲染很慢”。
    r = None
    try:
        for attempt in (1, 2):
            try:
                if not quiet:
                    print(f"    remotion {card} · {n_frames} 帧 · {seconds:.2f}s → {out.name}")
                r = subprocess.run([os.environ.get("COMSPEC", "cmd"), "/c", *cmd],
                                   cwd=str(REMOTION_DIR), capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", env=env, timeout=RENDER_TIMEOUT)
            except subprocess.TimeoutExpired:
                if attempt == 2:
                    raise RemotionError(f"remotion 渲染超时两次（{card}，>{RENDER_TIMEOUT}s），可能是 node/chrome 卡死")
                print(f"    remotion {card} 超时 {RENDER_TIMEOUT}s，降并发到 2 重试")
                conc = 2
                cmd = _cmd(conc)
                continue
            if r.returncode == 0 and out.exists():
                return out
            if attempt == 2:
                break
            print(f"    remotion {card} 失败一次，重试")
    finally:
        Path(props_path).unlink(missing_ok=True)
    tail = ((r.stderr or r.stdout or "").strip().splitlines()[-25:] if r else [])
    raise RemotionError(f"remotion 渲染失败（{card}）：\n" + "\n".join(tail))


def _coerce(value: str):
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def cli() -> None:
    args = sys.argv[1:]
    if "--list" in args:
        print("\n".join(card_names()))
        return
    card = out = None
    seconds = 4.0
    params: dict = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--card":
            card = args[i + 1]
            i += 2
        elif a == "--out":
            out = args[i + 1]
            i += 2
        elif a == "--seconds":
            seconds = float(args[i + 1])
            i += 2
        elif a == "--param":
            k, _, v = args[i + 1].partition("=")
            params[k] = _coerce(v)
            i += 2
        elif a == "--json":
            params.update(json.loads(args[i + 1]))
            i += 2
        else:
            raise SystemExit(f"不认识的参数：{a}")
    if not card or not out:
        raise SystemExit("用法：--card <卡名> --out <mp4> [--seconds 4] [--param k=v] [--json '{...}']")
    ok, msg = node_ready()
    if not ok:
        raise SystemExit(msg)
    print(render_shot(card, out, seconds, params=params))


if __name__ == "__main__":
    cli()
