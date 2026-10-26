"""剧本闸门：videos/ 下的正式视频，剧本没被项目负责人确认之前，不许配音，也不许构建渲染。

规矩见 process/SCRIPT-REVIEW.md（2026-10-26 项目负责人定，不可逾越）：
视频的所有文字（标题、封面字、旁白、字幕、画面上的每一行字）都由项目负责人逐条审核，
和 AI 讨论打磨；负责人明确说"确认剧本完善"之后，才在项目的 SCRIPT.md 里记一行：

    剧本确认：已确认 2026-10-27（项目负责人原话：「确认剧本完善」）

vlab-tts（配音）和 vlab-build（构建）开工前都检查这一行，没有就拒绝执行。
这一行只能在负责人明确确认之后记，AI 不得自行写入。
确认之后又改了任何文字，要把它改回「剧本确认：待审」，重新走审核。
research/ 和 archive/ 下的项目不受限制（试验和存档）。
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]           # toolkit/vlab/tools/script_gate.py → 仓库根
VIDEOS = (ROOT / "videos").resolve()
CONFIRMED = re.compile(r"^\s*剧本确认：已确认\s*\d{4}-\d{2}-\d{2}", re.M)


def formal_project(path) -> Path | None:
    """path 落在 videos/<项目>/ 里就返回项目目录；research、archive 等返回 None（不受闸门限制）。"""
    p = Path(path).resolve()
    try:
        rel = p.relative_to(VIDEOS)
    except ValueError:
        return None
    return VIDEOS / rel.parts[0] if rel.parts else None


def is_confirmed(project_dir: Path) -> bool:
    script = project_dir / "SCRIPT.md"
    return script.exists() and bool(CONFIRMED.search(script.read_text(encoding="utf-8-sig")))


def require_confirmed(path, action: str) -> None:
    """正式视频的剧本没确认就退出，并说明该怎么走流程。"""
    proj = formal_project(path)
    if proj is None or is_confirmed(proj):
        return
    script = (proj / "SCRIPT.md").relative_to(ROOT).as_posix()
    sys.exit(
        f"剧本闸门：{proj.name} 的剧本还没有被项目负责人确认，不能{action}。\n"
        f"  流程见 process/SCRIPT-REVIEW.md：视频的所有文字由项目负责人逐条审核、和 AI 讨论打磨，\n"
        f"  负责人明确说「确认剧本完善」之后，才在 {script} 里记一行\n"
        f"  「剧本确认：已确认 YYYY-MM-DD（项目负责人原话：「…」）」。这一行 AI 不得自行写入。"
    )
