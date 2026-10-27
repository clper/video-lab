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
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vlab.videokit.project import Project

HERE = Path(__file__).resolve().parent


def frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    # ffprobe 的输出末尾可能带逗号（多流时还会多行），直接 int() 会炸，取第一个整数即可
    m = re.search(r"\d+", out.stdout)
    if not m:
        raise RuntimeError(f"读不到 {path.name} 的帧数：{out.stdout!r} {out.stderr[-300:]!r}")
    return int(m.group(0))


def ensure_narration(P: Project, force: bool):
    content = P.content_json()
    content_path = P.dir / "content" / f"{P.id}.json"          # tts.py 按“稿子所在项目”决定输出目录
    hash_file = P.build_dir / "narration.hash"
    h = P.narration_hash()
    if not force and P.timeline_path.exists() and hash_file.exists() and hash_file.read_text() == h:
        print("时间轴：没变，复用" if P.mode == "grid" else "配音：旁白没变，复用")
        return
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    if P.mode == "grid":
        print("时间轴：按拍格生成…")
    else:
        print("配音：生成中（需要联网）…")
    subprocess.run([sys.executable, "-m", "vlab.pipeline.tts", str(content_path)], cwd=P.dir, check=True)
    hash_file.write_text(h)


def check_cue_words(P: Project, tl: dict) -> list[str]:
    errs = []
    tls = {s["id"]: s for s in tl["scenes"]}
    for s in P.scenes:
        words = tls[s["id"]]["words"]
        if not words:
            continue          # 拍格模式没有词时间点
        for el, cue in (s.get("cues") or {}).items():
            w = (cue or {}).get("on")
            if not w:
                continue
            hits = [x for x in words if x["text"].strip() == w] or [x for x in words if w in x["text"]]
            if len(hits) < cue.get("nth", 1):
                errs.append(f"[{s['id']}] 元素 {el} 绑定的「{w}」没被配音切成独立的词，可用的词：{[x['text'].strip() for x in words]}")
    return errs


def render_scene(P: Project, scene: dict, tl_scene: dict, style_arg, force: bool, fps: int = 30) -> str:
    sid = scene["id"]
    clip = P.clip_dir() / f"{sid}.mp4"
    hash_file = clip.with_suffix(".hash")
    h = P.scene_hash(scene, tl_scene)
    if not force and clip.exists() and hash_file.exists() and hash_file.read_text() == h:
        return f"  复用 {sid}"
    clip.parent.mkdir(parents=True, exist_ok=True)
    renderer = scene.get("renderer", "manim")
    secs = tl_scene["end"] - tl_scene["start"]
    # 帧数以 timeline 的毫秒级时间为准：先分别取整再相减，和帧数校验用同一套算法
    want = max(1, round(tl_scene["end"] * fps) - round(tl_scene["start"] * fps))
    size = (tl_scene.get("width") or 1080, tl_scene.get("height") or 1920)

    if renderer == "remotion":
        from vlab.render.remotion_bridge import render_shot
        # 全局特效默认值（project.yaml 的 fx_default）+ 本镜覆盖：
        # 切点白闪默认关，章节切换用 dip；t0 让背景相位跨镜连续
        fx = {**(P.data.get("fx_default") or {}), **(scene.get("fx") or {})}
        render_shot(scene["card"], clip, secs, params=scene.get("params") or {}, fps=fps, frames=want,
                    fx=fx or None, t0=round(tl_scene["start"] * fps), brand=P.data.get("brand"), slug=P.id,
                    width=size[0], height=size[1])
    elif renderer == "glsl":
        from vlab.render.glsl import ShaderRenderer, render_clip
        r = ShaderRenderer(P.dir / scene["frag"], ss=int(scene.get("ss", 2)),
                           size=(tl_scene.get("width", 1080), tl_scene.get("height", 1920)))
        uniforms = scene.get("uniforms") or scene.get("params") or {}
        # t0：着色器时间的起点（秒）。连续两镜用同一个着色器飞行时，第二镜写 t0 = 第一镜的时长，画面就接得上
        # fade_in / fade_out（秒）：着色器镜头没有 dip 层，亮场的云海接在暗场之后就是一次"开灯"，
        # 所以首尾各压一段黑（STYLE-RHYTHM：切点不许发亮）
        g_t0 = float(scene.get("t0", 0.0))
        g_fi, g_fo = float(scene.get("fade_in", 0) or 0), float(scene.get("fade_out", 0) or 0)
        g_dur = want / fps

        def _fade(t, img, _t0=g_t0, _fi=g_fi, _fo=g_fo, _dur=g_dur):
            u = t - _t0
            k = 1.0
            if _fi > 0:
                k = min(k, u / _fi)
            if _fo > 0:
                k = min(k, (_dur - u) / _fo)
            k = max(0.0, min(1.0, k))
            return img if k >= 0.999 else img.point(lambda v, _k=k: int(v * _k))

        render_clip(r, clip, want, t0=g_t0, fps=fps,
                    uniforms=(lambda t, u=uniforms: dict(u)) if uniforms else None,
                    overlay=_fade if (g_fi > 0 or g_fo > 0) else None)
    elif renderer == "custom":
        # 项目自带脚本：从 --scene 读一份 JSON（out/frames/fps/params/words…），自己写出 out。
        # 只给“这张卡库表达不了”的一次性镜头用，长得像固定模板了就搬回 cards/
        spec = {"out": str(clip.resolve()), "frames": want, "fps": fps, "seconds": round(secs, 3),
                "width": tl_scene.get("width", 1080), "height": tl_scene.get("height", 1920),
                "start": tl_scene["start"], "end": tl_scene["end"],
                "params": scene.get("params") or {}, "words": tl_scene.get("words") or []}
        fd, spec_path = tempfile.mkstemp(suffix=".json", prefix="vlab_custom_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False)
        try:
            r = subprocess.run([sys.executable, str(P.dir / scene["script"]), "--scene", spec_path,
                                *[str(a) for a in (scene.get("args") or [])]],
                               cwd=str(P.dir), capture_output=True, text=True, encoding="utf-8", errors="replace")
        finally:
            Path(spec_path).unlink(missing_ok=True)
        if r.returncode != 0:
            raise RuntimeError(f"镜头 {sid} 的自定义脚本失败：\n{r.stdout[-1500:]}\n{r.stderr[-2000:]}")
        if not clip.exists():
            raise RuntimeError(f"镜头 {sid} 的自定义脚本没写出 {clip.name}")
    else:
        media = P.dir / "media" / "manim" / P.style["name"] / sid
        env = dict(os.environ, VK_PROJECT=str(P.path), VK_SCENE=sid, VK_STYLE=str(style_arg or ""), PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-m", "manim", "render", str(HERE / "manim_templates.py"), "SpecScene",
                            "--format", "mp4", "--media_dir", str(media), "--progress_bar", "none"],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"镜头 {sid} 渲染失败：\n{r.stdout[-1500:]}\n{r.stderr[-3000:]}")
        late = [ln.strip() for ln in r.stdout.splitlines() if "[晚了]" in ln]
        out = next(media.rglob("SpecScene.mp4"))
        shutil.copyfile(out, clip)
        hash_file.write_text(h)
        return f"  渲染 {sid}" + (f"（{'；'.join(late)}）" if late else "")
    hash_file.write_text(h)
    return f"  渲染 {sid}（{renderer}）"


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
    # 剧本闸门：videos/ 下的正式视频，剧本没被项目负责人确认之前不许配音和渲染（process/SCRIPT-REVIEW.md）
    from vlab.tools import script_gate
    script_gate.require_confirmed(args.project, "配音和渲染")

    ensure_narration(P, args.force)
    tl = json.loads(P.timeline_path.read_text(encoding="utf-8"))
    errs = check_cue_words(P, tl)
    if errs:
        sys.exit("配音后校验没通过：\n  " + "\n  ".join(errs))
    tls = {s["id"]: s for s in tl["scenes"]}

    fps = 15 if os.environ.get("PREVIEW") == "1" else P.fps
    # glsl 渲染器在一个进程里共用一个 OpenGL 上下文，必须串行；remotion 在 Windows 上并发降到 2
    serial = [s for s in P.scenes if s.get("renderer") == "glsl"]
    parallel = [s for s in P.scenes if s.get("renderer") != "glsl"]
    jobs = args.jobs
    if any(s.get("renderer") == "remotion" for s in parallel):
        jobs = min(jobs, 2)
    for s in serial:
        print(render_scene(P, s, tls[s["id"]], args.style, args.force, fps))
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for msg in ex.map(lambda s: render_scene(P, s, tls[s["id"]], args.style, args.force, fps), parallel):
            print(msg)

    clips = [P.clip_dir() / f"{s['id']}.mp4" for s in P.scenes]
    bad = []
    for s, c in zip(P.scenes, clips):
        want = round(tls[s["id"]]["end"] * fps) - round(tls[s["id"]]["start"] * fps)
        got = frames(c)
        if got != want:
            bad.append(f"{s['id']}: {got} 帧，应为 {want}")
    if bad:
        sys.exit("帧数不对（会和配音错位）：\n  " + "\n  ".join(bad))
    print(f"帧数校验：{len(clips)} 个镜头全部对齐")

    final = P.dir / "renders" / f"{P.id}_{P.style['name']}.mp4"
    tex = P.style.get("texture", {})
    # 总装指纹：所有镜头指纹 + 质感 + 配音；都没变且成片还在，就不用重新拼接编码
    # subs.ass 也要算：字幕样式/分行变了要重新烧，否则会沿用旧成片
    subs = P.build_dir / "subs.ass"
    _audio = P.data.get("audio") if isinstance(P.data.get("audio"), dict) else {}
    _sfx_file = P.dir / _audio["sfx_file"] if _audio.get("sfx_file") else None
    asm_hash = "|".join([c.with_suffix(".hash").read_text() for c in clips]
                        + [json.dumps(tex, sort_keys=True), json.dumps(P.data.get("audio") or {}, sort_keys=True),
                           P.narration_hash(), subs.read_text(encoding="utf-8-sig") if subs.exists() else "",
                           # 音效事件表在文件里时，文件内容变了也要重新混音
                           _sfx_file.read_text(encoding="utf-8") if _sfx_file and _sfx_file.exists() else ""])
    asm_file = P.clip_dir() / "_assembly.hash"
    if not args.force and final.exists() and asm_file.exists() and asm_file.read_text() == asm_hash:
        print(f"成片：没有变化，跳过拼接 → {final}")
        return
    vf = []      # 质感在 concat 之后加，保证整片一致（逐镜头加的话接缝处会看出差别）
    if tex.get("vignette"):
        vf.append(f"vignette=angle={0.08 + 0.22 * float(tex['vignette']):.3f}*PI")
    if tex.get("grain"):
        vf.append(f"noise=alls={int(tex['grain'])}:allf=t")
    # 片尾淡出：最后一帧直接断掉会有"没剪完"的感觉，0.45s 落到黑
    tail = float(tl.get("duration") or 0)
    if tail > 1.0:
        vf.append(f"fade=t=out:st={tail - 0.45:.3f}:d=0.45")
    silent = P.dir / "media" / f"silent_{P.style['name']}.mp4"
    # 用 concat 滤镜逐路解码再拼，不用 concat demuxer：
    # 各渲染器产物的 time_base 不一样（remotion 1/90000、着色器 1/15360），
    # demuxer 会按首个文件的参数去解其余文件，实测最后一镜整段丢帧（成片短 5 秒）。
    chains = [f"[{i}:v]fps={fps},format=yuv420p,setsar=1[v{i}]" for i in range(len(clips))]
    joined = "".join(f"[v{i}]" for i in range(len(clips)))
    graph = ";".join(chains) + f";{joined}concat=n={len(clips)}:v=1:a=0[cc];[cc]" + ",".join(vf or ["null"]) + "[out]"
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    *[a for c in clips for a in ("-i", str(c))],
                    "-filter_complex", graph, "-map", "[out]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                    "-pix_fmt", "yuv420p", "-r", str(fps), str(silent)], check=True)
    # 拼接这一步也要校验帧数：镜头各自对齐不代表串起来是对的（丢一整镜时时长会短一截）
    total = sum(round(tls[s["id"]]["end"] * fps) - round(tls[s["id"]]["start"] * fps) for s in P.scenes)
    got = frames(silent)
    if got != total:
        sys.exit(f"拼接后帧数不对：{got} 帧，应为 {total}（镜头串接丢帧）")
    print(f"拼接：{got} 帧（{got / fps:.2f}s，配音 {tl['duration']:.2f}s）")
    # 先合配音+烧字幕，再用 mix 做配乐与响度（mix 走 -c:v copy，不二次压画面）
    pre = P.dir / "media" / f"premix_{P.style['name']}.mp4"
    print("合配音 + 烧字幕…")
    subprocess.run([sys.executable, "-m", "vlab.pipeline.finalize", str(silent), str(P.build_dir), str(pre)], check=True)
    silent.unlink()                      # 无声中间文件只是合配音前的过渡，体积大，用完就删
    audio_cfg = P.data.get("audio") if isinstance(P.data.get("audio"), dict) else {}
    from vlab.audio import mix as _mix
    music_path = None
    if audio_cfg.get("music"):
        from vlab.audio import music as _music
        # 配乐函数可选（默认 ambient_pulse）：长片用带段落的 fold_score 这类
        fn_name = str(audio_cfg.get("music_fn") or "ambient_pulse")
        fn = getattr(_music, fn_name, None) or _music.ambient_pulse
        # 版本号进文件名：改了生成算法就换个号，不然会一直复用旧 wav
        ver = int(audio_cfg.get("music_v", 1))
        music_path = P.build_dir / (f"music_{fn_name}.wav" if ver <= 1 else f"music_{fn_name}_v{ver}.wav")
        if args.force or not music_path.exists():
            print(f"配乐：{fn_name} 生成中…")
            kw = {}
            if audio_cfg.get("music_segs"):          # 段落表跟着本片的章节走（fold_score 必填）
                kw["segs"] = [(float(a), float(b), dict(c or {})) for a, b, c in audio_cfg["music_segs"]]
            _music.write_wav(music_path, fn(tl["duration"] + 0.5, bpm=int(audio_cfg.get("bpm", 88)),
                                            seed=int(audio_cfg.get("seed", 7)), **kw))
    # 音效：直接写事件表（秒 / kind / gain），渲染成一条轨，mix 时按 sfx_db 合入。
    # 事件多、由程序算出来的（比如火柴人片子里每一次落地），写 sfx_file：相对项目目录的 JSON 事件表
    sfx_path = None
    sfx_cfg = list(audio_cfg.get("sfx") or [])
    if audio_cfg.get("sfx_file"):
        sfx_cfg += json.loads((P.dir / audio_cfg["sfx_file"]).read_text(encoding="utf-8"))
    if sfx_cfg:
        from vlab.audio import sfx as _sfx
        sfx_path = P.build_dir / "sfx.wav"
        fp = hashlib.sha1(json.dumps(sfx_cfg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        side = sfx_path.with_suffix(".hash")
        if args.force or not sfx_path.exists() or not side.exists() or side.read_text() != fp:
            print(f"音效：{len(sfx_cfg)} 个事件…")
            _sfx.write_wav(sfx_path, _sfx.render([dict(e) for e in sfx_cfg], tl["duration"]))
            side.write_text(fp)
    print(f"配乐 + 响度（{audio_cfg.get('music_db', -18)} dB / {audio_cfg.get('lufs', -14)} LUFS）…")
    # 没有旁白时整条音轨就是音乐：不再用配音做 sidechain 避让，音乐走满电平
    voice = P.build_dir / "narration.wav"
    has_voice = voice.exists()
    _mix.mux(pre, voice if has_voice else None, final, music=music_path, sfx=sfx_path, duration=tl["duration"],
             music_db=float(audio_cfg.get("music_db", -18.0 if has_voice else 0.0)),
             sfx_db=float(audio_cfg.get("sfx_db", -1.0)),
             duck=bool(audio_cfg.get("duck", has_voice)),
             lufs=float(audio_cfg.get("lufs", -14.0)))
    pre.unlink(missing_ok=True)
    print(f"成片 → {final}")
    sheet = P.dir / "media" / f"{P.id}_{P.style['name']}_preview.png"
    subprocess.run([sys.executable, "-m", "vlab.tools.preview", str(final), "--timeline", str(P.timeline_path),
                    "--out", str(sheet), "--cols", str(min(6, len(P.scenes)))], check=True)
    asm_file.write_text(asm_hash)


if __name__ == "__main__":
    main()
