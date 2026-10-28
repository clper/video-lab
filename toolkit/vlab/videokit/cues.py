"""剪辑时刻表：配乐由项目负责人剪辑时从曲库加（2026-10-27 定），构建时给出对拍用的时刻表。

vlab-build 每次都会写（内容没变就不动文件）：
    renders/<id>_cues.md   配乐提示 + 镜头表（起止、内容、旁白区间）+ 重音效
    renders/<id>_cues.srt  配乐提示做成字幕，导入剪映就是一条标记轨（没写 music_cues 就不出）

配乐提示写在 project.yaml 顶层：
    music_cues:
      - {t: 16, to: 22, picture: 撞上那一刻定格, sound: 重拍，然后音乐收住}
      - {t: 42, sound: 音乐停}
镜头内容取镜头的 note（只是说明，不进镜头指纹）；没写 note 就取旁白开头。
"""

from pathlib import Path

HEAVY_GAIN = 0.8        # 增益到这个数的音效算"重音效"，剪配乐时要让开或者对上


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _sec(t) -> str:
    return f"{float(t):.1f}"


def _write(path: Path, text: str):
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def write(P, tl: dict, sfx_events: list[dict]) -> tuple[Path, Path | None]:
    out = P.dir / "renders"
    md_path, srt_path = out / f"{P.id}_cues.md", out / f"{P.id}_cues.srt"
    music = sorted(P.data.get("music_cues") or [], key=lambda c: float(c["t"]))
    tls = {s["id"]: s for s in tl["scenes"]}

    lines = [f"# {P.data.get('title', P.id)} · 剪辑时刻表", "",
             "vlab-build 自动生成，不要手改：配乐提示改 project.yaml 的 music_cues，镜头内容改镜头的 note。", ""]
    head = f"片长 {float(tl['duration']):.2f} 秒。"
    if P.grid:
        bpm = float(P.grid.get("bpm", 100))
        beat = float(P.grid.get("beat") or 60.0 / bpm)
        head += (f"画面按 {bpm:g} BPM 拍格编排（每拍 {beat:g} 秒，每小节 {4 * beat:g} 秒）："
                 "选同样速度的曲子、第一拍对齐片头，下面的点就落在拍上。")
    else:
        head += "有旁白：镜头表里的旁白区间是要让开的地方，配乐在这些区间压低。"
    lines += [head, ""]
    if music:
        lines += ["## 配乐提示", "", f"同名的 `{srt_path.name}` 可以导入剪映当字幕轨，每一条就是一个标记。", "",
                  "| 时刻（秒） | 画面 | 声音建议 |", "|---|---|---|"]
        for c in music:
            span = _sec(c["t"]) + (f"–{_sec(c['to'])}" if c.get("to") is not None else "")
            lines.append(f"| {span} | {c.get('picture', '')} | {c.get('sound', '')} |")
        lines.append("")

    voiced = any(s.get("voice_end") for s in tl["scenes"])
    lines += ["## 镜头", "", "| 镜头 | 起–止（秒） | 内容 |" + (" 旁白（秒） |" if voiced else ""),
              "|---|---|---|" + ("---|" if voiced else "")]
    for s in P.scenes:
        t = tls[s["id"]]
        what = s.get("note") or (s.get("narration") or "")[:20]
        row = f"| {s['id']} | {_sec(t['start'])}–{_sec(t['end'])} | {what} |"
        if voiced:
            row += f" {_sec(t['voice_start'])}–{_sec(t['voice_end'])} |" if t.get("voice_end") else " — |"
        lines.append(row)
    lines.append("")

    heavy = sorted((e for e in sfx_events if float(e.get("gain", 1.0)) >= HEAVY_GAIN), key=lambda e: float(e["t"]))
    if heavy:
        lines += [f"## 重音效（增益 ≥ {HEAVY_GAIN}）", "",
                  " · ".join(f"{_sec(e['t'])} {e['kind']}" for e in heavy), ""]
    _write(md_path, "\n".join(lines))

    if not music:
        return md_path, None
    # 字幕条不能重叠（剪映导入重叠的字幕会乱）：同一时刻的几条并成一条，每条截到下一条开始
    marks = []                          # [起, 止, 文字]
    for c in music:
        t0 = float(c["t"])
        t1 = float(c["to"]) if c.get("to") is not None else t0 + 1.5
        text = " · ".join(x for x in (c.get("sound"), c.get("picture")) if x)
        if marks and abs(marks[-1][0] - t0) < 1e-6:
            marks[-1][1] = max(marks[-1][1], t1)
            marks[-1][2] += " · " + text
        else:
            marks.append([t0, t1, text])
    items = []
    for i, (t0, t1, text) in enumerate(marks, 1):
        if i < len(marks):
            t1 = min(t1, marks[i][0])
        items.append(f"{i}\n{_ts(t0)} --> {_ts(t1)}\n{text}\n")
    _write(srt_path, "\n".join(items))
    return md_path, srt_path
