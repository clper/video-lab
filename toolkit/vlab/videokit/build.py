"""视频工程构建：project.yaml → 成片。改了什么只重做什么。

用法（任意目录）:
    uv run vlab-build research/visual/08-video-spec/project.yaml
    uv run vlab-build <project.yaml> --style <style.yaml>   # 临时换风格（缓存分开存）
    uv run vlab-build <project.yaml> --check                # 只校验，不渲染
    uv run vlab-build <project.yaml> --force                # 全部重渲染
    设环境变量 PREVIEW=1 出低清快速版

流程：校验 → 配音（旁白没变就跳过）→ 逐镜头渲染（指纹没变就复用）→ 帧数校验 → 拼接 + 质感 → 合配音字幕 → 预览拼图
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vlab.videokit.project import Project

HERE = Path(__file__).resolve().parent


def frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


def ensure_narration(P: Project, force: bool):
    content = P.content_json()
    content_path = P.dir / "content" / f"{P.id}.json"          # tts.py 按"稿子所在项目"决定输出目录
    hash_file = P.build_dir / "narration.hash"
    h = P.narration_hash()
    if not force and P.timeline_path.exists() and hash_file.exists() and hash_file.read_text() == h:
        print("配音：旁白没变，复用")
        return
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print("配音：生成中（需要联网）…")
    subprocess.run([sys.executable, "-m", "vlab.pipeline.tts", str(content_path)], cwd=P.dir, check=True)
    hash_file.write_text(h)


def check_cue_words(P: Project, tl: dict) -> list[str]:
    errs = []
    tls = {s["id"]: s for s in tl["scenes"]}
    for s in P.scenes:
        words = tls[s["id"]]["words"]
        for el, cue in (s.get("cues") or {}).items():
            w = (cue or {}).get("on")
            if not w:
                continue
            hits = [x for x in words if x["text"].strip() == w] or [x for x in words if w in x["text"]]
            if len(hits) < cue.get("nth", 1):
                errs.append(f"[{s['id']}] 元素 {el} 绑定的「{w}」没被配音切成独立的词，可用的词：{[x['text'].strip() for x in words]}")
    return errs


def render_scene(P: Project, scene: dict, tl_scene: dict, style_arg, force: bool) -> str:
    sid = scene["id"]
    clip = P.clip_dir() / f"{sid}.mp4"
    hash_file = clip.with_suffix(".hash")
    h = P.scene_hash(scene, tl_scene)
    if not force and clip.exists() and hash_file.exists() and hash_file.read_text() == h:
        return f"  复用 {sid}"
    media = P.dir / "media" / "manim" / P.style["name"] / sid
    env = dict(os.environ, VK_PROJECT=str(P.path), VK_SCENE=sid, VK_STYLE=str(style_arg or ""), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-m", "manim", "render", str(HERE / "manim_templates.py"), "SpecScene",
                        "--format", "mp4", "--media_dir", str(media), "--progress_bar", "none"],
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"镜头 {sid} 渲染失败：\n{r.stdout[-1500:]}\n{r.stderr[-3000:]}")
    late = [ln.strip() for ln in r.stdout.splitlines() if "[晚了]" in ln]
    out = next(media.rglob("SpecScene.mp4"))
    clip.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out, clip)
    hash_file.write_text(h)
    return f"  渲染 {sid}" + (f"（{'；'.join(late)}）" if late else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--style")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--jobs", type=int, default=3)
    args = ap.parse_args()

    P = Project(args.project, args.style)
    print(f"工程 {P.id}（{len(P.scenes)} 个镜头），风格 {P.style['name']}")
    errs = P.validate()
    if errs:
        sys.exit("校验没通过：\n  " + "\n  ".join(errs))
    print("校验：通过")
    if args.check:
        return

    ensure_narration(P, args.force)
    tl = json.loads(P.timeline_path.read_text(encoding="utf-8"))
    errs = check_cue_words(P, tl)
    if errs:
        sys.exit("配音后校验没通过：\n  " + "\n  ".join(errs))
    tls = {s["id"]: s for s in tl["scenes"]}

    fps = 15 if os.environ.get("PREVIEW") == "1" else P.fps
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for msg in ex.map(lambda s: render_scene(P, s, tls[s["id"]], args.style, args.force), P.scenes):
            print(msg)

    clips = [P.clip_dir() / f"{s['id']}.mp4" for s in P.scenes]
    bad = []
    for s, c in zip(P.scenes, clips):
        want = round(tls[s["id"]]["end"] * fps) - round(tls[s["id"]]["start"] * fps)
        if frames(c) != want:
            bad.append(f"{s['id']}: {frames(c)} 帧，应为 {want}")
    if bad:
        sys.exit("帧数不对（会和配音错位）：\n  " + "\n  ".join(bad))
    print(f"帧数校验：{len(clips)} 个镜头全部对齐")

    final = P.dir / "renders" / f"{P.id}_{P.style['name']}.mp4"
    tex = P.style.get("texture", {})
    # 总装指纹：所有镜头指纹 + 质感 + 配音；都没变且成片还在，就不用重新拼接编码
    asm_hash = "|".join([c.with_suffix(".hash").read_text() for c in clips] + [json.dumps(tex, sort_keys=True), P.narration_hash()])
    asm_file = P.clip_dir() / "_assembly.hash"
    if not args.force and final.exists() and asm_file.exists() and asm_file.read_text() == asm_hash:
        print(f"成片：没有变化，跳过拼接 → {final}")
        return
    lst = P.dir / "media" / f"concat_{P.style['name']}.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    vf = []
    if tex.get("vignette"):
        vf.append(f"vignette=angle={0.08 + 0.22 * float(tex['vignette']):.3f}*PI")
    if tex.get("grain"):
        vf.append(f"noise=alls={int(tex['grain'])}:allf=t")
    silent = P.dir / "media" / f"silent_{P.style['name']}.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    *(["-vf", ",".join(vf)] if vf else []), "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                    "-pix_fmt", "yuv420p", "-r", str(fps), str(silent)], check=True)
    subprocess.run([sys.executable, "-m", "vlab.pipeline.finalize", str(silent), str(P.build_dir), str(final)], check=True)
    silent.unlink()                      # 无声中间文件只是合配音前的过渡，体积大，用完就删
    sheet = P.dir / "media" / f"{P.id}_{P.style['name']}_preview.png"
    subprocess.run([sys.executable, "-m", "vlab.tools.preview", str(final), "--timeline", str(P.timeline_path),
                    "--out", str(sheet), "--cols", str(min(6, len(P.scenes)))], check=True)
    asm_file.write_text(asm_hash)


if __name__ == "__main__":
    main()
