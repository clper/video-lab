"""冒烟测试：几秒钟跑完，专抓"改公共代码，把别的片子或样片弄坏了"这类问题。

    uv run python -m vlab.tools.smoke              # 全部
    uv run python -m vlab.tools.smoke card ragdoll # 只跑名字里带这些词的
    uv run python -m vlab.tools.smoke --tsc        # 另跑一遍 Remotion 的类型检查（十几秒，要 node_modules）

vlab-check 末尾会跑一遍（不含 --tsc）。每条检查是一个函数：没问题就返回一句说明，有问题就 raise。
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]      # toolkit/vlab/tools/smoke.py → 仓库根

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


# ---------- 镜头卡指纹：每张卡只按自己和它引用的代码算 ----------

@check
def card_fingerprint_isolated():
    from vlab.render.remotion_bridge import card_code_files
    stick = {p.name for p in card_code_files("stickScene")}
    for need in ("StickScene.tsx", "Shot.tsx", "GlobalFX.tsx", "tokens.ts", "index.ts", "Root.tsx"):
        assert need in stick, f"stickScene 的指纹没算 {need}"
    for other in ("ParticleText.tsx", "Sample15s.tsx", "Flock.tsx", "registry.ts"):
        assert other not in stick, f"stickScene 的指纹把别的卡 {other} 也算进去了"
    flock = {p.name for p in card_code_files("flock")}
    assert "flock.ts" in flock and "StickScene.tsx" not in flock, f"flock 的指纹不对：{sorted(flock)}"
    return f"stickScene 依赖 {len(stick)} 个文件，flock 依赖 {len(flock)} 个"


@check
def card_fingerprint_every_card():
    from vlab.render.remotion_bridge import card_code_files, card_code_hash, card_names
    names = card_names()
    assert len(names) >= 30, f"只解析出 {len(names)} 张卡"
    for n in names:
        cards = [p for p in card_code_files(n) if p.parent.name == "cards"]
        assert len(cards) == 1, f"卡 {n} 在 cards/ 下对应 {[p.name for p in cards]}（应正好一个文件）"
    assert card_code_hash("stickScene") == card_code_hash("stickScene")
    assert card_code_hash("stickScene") != card_code_hash("flock")
    return f"{len(names)} 张卡都找到了自己的源文件"


@check
def fingerprint_stable_across_checkouts():
    """克隆出来的换行符（core.autocrlf）和机器上生成的文件（public/ 的字体副本）不能影响指纹。"""
    import tempfile
    from vlab.render.remotion_bridge import _imports, card_hash_inputs
    from vlab.videokit.project import _file_bytes
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.json", Path(d) / "b.json"
        a.write_bytes(b'{"x": 1,\n "y": 2}\n')
        b.write_bytes(b'{"x": 1,\r\n "y": 2}\r\n')
        assert _file_bytes(a) == _file_bytes(b), "LF 和 CRLF 的同一份内容算出来不一样"
    inputs = card_hash_inputs("stickScene")
    assert not [p for p in inputs if "public" in p.parts], "指纹不能算 public/（字体副本由 npm 脚本生成，不入库）"
    assert any(p.suffix == ".otf" for p in inputs), "字体要按入库的 vlab/assets/fonts 算"
    got = _imports('﻿import a from "./a"; import b from "./b";\n'
                   'const c = await import("./c");\nimport {\n  x,\n} from "../d";\nexport * from "./e";\n'
                   'import "./f.css";\nimport { y } from "remotion";\n')
    assert got == ["./a", "./b", "./c", "../d", "./e", "./f.css"], got
    return "换行符、字体副本不影响指纹；import 的各种写法都认得"


@check
def scene_hash_uses_card_fingerprint():
    from vlab.render.remotion_bridge import card_code_hash
    from vlab.videokit.project import _code_hash
    assert _code_hash(ROOT, {"card": "flock"}, "remotion") == card_code_hash("flock"), "remotion 镜头没按卡算指纹"
    return "remotion 镜头按卡的依赖闭包算指纹"


# ---------- 预计算 + 数据文件：先算数据、再按镜头画的片子（009 火柴人、模拟类） ----------

def _toy_project(tmp: Path) -> Path:
    """一个最小的拍格工程：两镜都吃预计算写出的数据文件。"""
    (tmp / "calc.py").write_text(
        "import json, os, pathlib\n"
        "tl = json.loads(pathlib.Path(os.environ['VLAB_TIMELINE']).read_text(encoding='utf-8'))\n"
        "k = pathlib.Path('k.txt').read_text()\n"
        "out = pathlib.Path('build/toy/shots'); out.mkdir(parents=True, exist_ok=True)\n"
        "for s in tl['scenes']:\n"
        "    (out / (s['id'] + '.json')).write_text(json.dumps({'k': k, 'start': s['start']}))\n"
        "n = pathlib.Path('runs.txt'); n.write_text(str(int(n.read_text()) + 1 if n.exists() else 1))\n",
        encoding="utf-8")
    (tmp / "k.txt").write_text("1")
    (tmp / "project.yaml").write_text(
        "id: toy\naspect: landscape\ngrid: {bpm: 120}\n"
        "precompute: {script: calc.py, inputs: [k.txt]}\n"
        "scenes:\n"
        "  - {id: A, hold: 2, card: stickScene, renderer: remotion, params: {x: 1}, params_files: {data: build/toy/shots/A.json}}\n"
        "  - {id: B, hold: 2, card: stickScene, renderer: remotion, params_files: {data: build/toy/shots/B.json}}\n",
        encoding="utf-8")
    tl = {"duration": 2.0, "scenes": [{"id": "A", "start": 0.0, "end": 1.0, "words": []},
                                      {"id": "B", "start": 1.0, "end": 2.0, "words": []}]}
    (tmp / "build" / "toy").mkdir(parents=True)
    (tmp / "build" / "toy" / "timeline.json").write_text(json.dumps(tl), encoding="utf-8")
    return tmp / "project.yaml"


@check
def precompute_and_params_files():
    import contextlib
    import io
    import tempfile
    from vlab.videokit.build import run_precompute
    from vlab.videokit.project import Project
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        tmp = Path(d)
        P = Project(_toy_project(tmp))
        assert not P.validate(), f"数据文件还没生成时校验不该报错（有 precompute 会生成）：{P.validate()}"
        assert run_precompute(P) is True and run_precompute(P) is False, "输入没变时不该重跑"
        assert (tmp / "runs.txt").read_text() == "1"
        tl = {s["id"]: s for s in json.loads(P.timeline_path.read_text(encoding="utf-8"))["scenes"]}
        a = P.scenes[0]
        assert P.scene_params(a) == {"x": 1, "data": {"k": "1", "start": 0.0}}, P.scene_params(a)
        h1 = P.scene_hash(a, tl["A"])
        (tmp / "k.txt").write_text("2")
        assert run_precompute(P) is True, "输入变了要重跑"
        assert P.scene_hash(a, tl["A"]) != h1, "数据文件内容变了，镜头指纹要跟着变"
        (tmp / "build" / "toy" / "shots" / "B.json").unlink()
        assert any("B.json" in e for e in Project(tmp / "project.yaml").validate()) is False
        assert run_precompute(P) is True, "印记对得上、但数据文件缺了，也要重跑"
        assert (tmp / "build" / "toy" / "shots" / "B.json").exists()
        from vlab.videokit.build import data_frame_error
        (tmp / "build" / "toy" / "shots" / "B.json").write_text('{"frames": 38, "offset": 8}', encoding="utf-8")
        b = P.scenes[1]
        assert data_frame_error(P, b, 30) is None
        err = data_frame_error(P, b, 15)
        assert err and "PREVIEW" in err, f"帧数对不上要报错（低帧率预览就会这样）：{err}"
        (tmp / "build" / "toy" / "shots" / "B.json").unlink()
        y =(tmp / "project.yaml").read_text(encoding="utf-8").replace("precompute: {script: calc.py, inputs: [k.txt]}\n", "")
        (tmp / "project.yaml").write_text(y, encoding="utf-8")
        assert any("B.json" in e for e in Project(tmp / "project.yaml").validate()), "没有 precompute 时缺数据文件要报错"
    return "预计算按输入指纹跑、数据文件进参数和指纹"


# ---------- 剪辑时刻表：配乐在剪辑时从曲库加，构建时给出对拍用的时刻表 ----------

@check
def cue_sheet():
    import tempfile
    from vlab.videokit import cues
    from vlab.videokit.project import Project
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "project.yaml").write_text(
            "id: toy\ntitle: 玩具\ngrid: {bpm: 120}\n"
            "music_cues:\n  - {t: 16, to: 22, picture: 撞上定格, sound: 重拍然后收住}\n  - {t: 42, sound: 音乐停}\n"
            "  - {t: 20, picture: 解冻}\n  - {t: 30, sound: 鼓点}\n  - {t: 30, picture: 连打}\n  - {t: 30.05, sound: 二}\n"
            "scenes:\n  - {id: S1, hold: 32, note: 四步重脚步}\n  - {id: S2, hold: 60}\n", encoding="utf-8")
        P = Project(tmp / "project.yaml")
        tl = {"duration": 46.0, "scenes": [{"id": "S1", "start": 0.0, "end": 16.0, "words": []},
                                           {"id": "S2", "start": 16.0, "end": 46.0, "words": []}]}
        md, srt = cues.write(P, tl, [{"t": 0.5, "kind": "stomp", "gain": 0.95}, {"t": 3.0, "kind": "step", "gain": 0.3}])
        m = md.read_text(encoding="utf-8")
        for need in ("120 BPM", "S1", "四步重脚步", "重拍然后收住", "音乐停", "0.5 stomp"):
            assert need in m, f"时刻表里没有「{need}」"
        assert "step" not in m, "轻音效不该列进重音效"
        s = srt.read_text(encoding="utf-8")
        assert "00:00:16,000 --> 00:00:20,000" in s and "00:00:42,000 -->" in s, s
        assert "重拍然后收住 · 撞上定格" in s, s
        assert "00:00:22,000" not in s, "字幕条不能重叠（剪映导入重叠字幕会乱），区间要截到下一条开始"
        import re
        spans = [(_srt_sec(a), _srt_sec(b)) for a, b in re.findall(r"(\S+) --> (\S+)", s)]
        assert all(a < b for a, b in spans) and all(b <= c for (_, b), (c, _) in zip(spans, spans[1:])), spans
        assert "鼓点 · 连打" in s, "同一时刻的两条提示要并成一条"
        assert P.scene_hash({"id": "S1", "hold": 32, "note": "a"}, tl["scenes"][0]) == \
            P.scene_hash({"id": "S1", "hold": 32, "note": "b"}, tl["scenes"][0]), "note 只是说明，不该进镜头指纹"
    return "时刻表 md + srt"


def _srt_sec(ts: str) -> float:
    h, m, rest = ts.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


# ---------- 体检：破例写成数据；motion 基线和死帧 ----------

@check
def review_waivers():
    import tempfile
    from vlab.tools.review import rhythm_report, split_waived
    from vlab.videokit.project import Project
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "project.yaml").write_text(
            "id: toy\ngrid: {bpm: 120}\nreview:\n  waive:\n    shot_max: {S1: 一口气的冲锋}\n"
            "scenes:\n  - {id: S1, hold: 12, card: stickScene, renderer: remotion, beats: 3}\n"
            "  - {id: S2, hold: 12, card: stickScene, renderer: remotion, beats: 3}\n", encoding="utf-8")
        P = Project(tmp / "project.yaml")
        tl = {"duration": 12.0, "scenes": [{"id": "S1", "start": 0.0, "end": 6.0, "words": []},
                                           {"id": "S2", "start": 6.0, "end": 12.0, "words": []}]}
        _, fails = rhythm_report(P, tl, quiet=True)
        hard, waived = split_waived(fails, P.data["review"]["waive"])
        keys = {(f["key"], f["sid"]) for f in hard}
        assert ("shot_max", "S2") in keys and ("shot_max", "S1") not in keys, keys
        assert [(f["key"], f["sid"]) for f in waived] == [("shot_max", "S1")] and waived[0]["why"] == "一口气的冲锋"
        assert ("duration", None) in keys, "片长 12 秒应该没过"
    from vlab.tools.review import motion_fails
    fails = motion_fails({"avg": 2.0, "segments": [1.2, 0.6, 1.3, 0.7], "still_max": (0.1, 1.0), "empty_max": (0.0, 0.0)})
    hard, waived = split_waived(fails, {"motion_10s": {"10–20s": "定格"}})
    assert [f["sid"] for f in waived] == ["10–20s"] and [f["sid"] for f in hard] == ["30–40s"], (hard, waived)
    return "破例按 key / 镜头 / 10 秒段生效，没写理由的照样算没过"


@check
def review_motion():
    import subprocess
    import tempfile
    from vlab.tools.review import motion_stats
    with tempfile.TemporaryDirectory() as d:
        v = Path(d) / "m.mp4"
        # 3 秒纯黑静止 + 3 秒测试图（滚动的计数器和色带）
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=480x270:d=3:r=30",
                        "-f", "lavfi", "-i", "testsrc2=s=480x270:d=3:r=30", "-filter_complex",
                        "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", str(v)], check=True)
        m = motion_stats(v, seg=3.0)
        assert len(m["segments"]) == 2 and m["segments"][0] < 0.05 < m["segments"][1], m["segments"]
        assert abs(m["still_max"][0] - 3.0) < 0.2, m["still_max"]
        assert abs(m["empty_max"][0] - 3.0) < 0.6, m["empty_max"]
    return f"全片 {m['avg']:.2f}，静止 {m['still_max'][0]:.1f}s，无主体 {m['empty_max'][0]:.1f}s"


# ---------- 公共代码整体：能 import、各工程能过校验、火柴人和音效算得出来 ----------

# 已知没过、原因写清楚的工程：列出来提醒，不算冒烟测试没过。修好了就从这里删掉
KNOWN_INVALID = {
    "videos/007-regression/project.yaml": "audio.music_fn 是 fold_score 但没写 music_segs（007 暂停中；"
                                          "恢复时按本片章节补段落表，或改成剪辑时从曲库配乐）",
}


@check
def imports():
    import importlib
    import pkgutil
    import vlab
    skip = {"vlab.videokit.manim_templates"}      # 由 manim 带着环境变量 VK_PROJECT 跑，单独 import 会去读工程
    bad, n = [], 0
    for m in pkgutil.walk_packages(vlab.__path__, "vlab."):
        if m.name in skip:
            continue
        try:
            importlib.import_module(m.name)
            n += 1
        except Exception as e:  # noqa: BLE001
            bad.append(f"{m.name}: {type(e).__name__}: {e}")
    assert not bad, "；".join(bad)
    return f"{n} 个模块都能 import"


@check
def projects_validate():
    from vlab.videokit.project import Project
    paths = sorted({*ROOT.glob("videos/*/project.yaml"), *ROOT.glob("research/*/*/project.yaml"),
                    *ROOT.glob("archive/*/project.yaml")})
    bad, known = [], []
    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        errs = Project(p).validate()
        if errs and rel in KNOWN_INVALID:
            known.append(rel)
        elif errs:
            bad.append(f"{rel}：{errs[0]}" + (f" 等 {len(errs)} 条" if len(errs) > 1 else ""))
    assert not bad, "；".join(bad)
    return f"{len(paths) - len(known)} 个工程过校验" + (f"；已知没过：{'、'.join(known)}（原因见 KNOWN_INVALID）" if known else "")


@check
def timeline_frames():
    from vlab.videokit.project import Project
    P = Project(ROOT / "videos/009-redirect/project.yaml")
    tl = json.loads(P.timeline_path.read_text(encoding="utf-8"))
    per = [round(s["end"] * P.fps) - round(s["start"] * P.fps) for s in tl["scenes"]]
    assert sum(per) == round(tl["duration"] * P.fps), f"各镜帧数之和 {sum(per)} ≠ 全片 {round(tl['duration'] * P.fps)}"
    return f"009：{len(per)} 镜帧数之和 = 全片 {sum(per)} 帧"


@check
def ragdoll_stable():
    import math
    from vlab.stick import ragdoll, rig
    tr = rig.Track([rig.K(0, x=500, y=rig.STAND_Y, lean=4, head=0, aF=20, fF=40, aB=-15, fB=10,
                          footF=(530, rig.FOOT_Y), footB=(470, rig.FOOT_Y))], face=1)
    J0, face = tr.joints(0)
    frames, hits = ragdoll.simulate(J0, J0, 1 / 30, face, 120, kick=lambda i: (900.0, -500.0) if i in (1, 2) else (0.0, 0.0))
    torso = math.dist(J0[0], J0[1])
    for k, J in enumerate(frames):
        assert all(math.isfinite(c) for p in J for c in p), f"第 {k} 帧出现 NaN/inf"
        assert abs(math.dist(J[0], J[1]) - torso) < 0.02 * torso, f"第 {k} 帧躯干长度变了（布偶炸开）"
        assert max(p[1] for p in J) <= rig.GROUND + 1, f"第 {k} 帧穿到地面以下"
    assert hits, "被推倒却没有落地事件"
    last = max(math.dist(a, b) for a, b in zip(frames[-1], frames[-2]))
    assert last < 0.5, f"4 秒后还在动（每帧 {last:.1f} px），布偶没停下来"
    drift = frames[-1][0][0] - J0[0][0]
    assert 0 < drift < 400, f"往前推了一把，骨盆横移 {drift:.0f} px（应向前、且不该滑出去太远）"
    return f"推倒后 4 秒静止，落地 {len(hits)} 次，骨盆前移 {drift:.0f} px"


@check
def sfx_kinds():
    import numpy as np
    from vlab.audio import sfx
    for name, fn in sfx.KINDS.items():
        x = fn(seed=0)
        assert len(x) > 0 and np.isfinite(x).all() and np.abs(x).max() <= 1.0 + 1e-6, f"音效 {name} 不对"
    x = sfx.render([{"t": 0.1 * i, "kind": k, "gain": 1.0} for i, k in enumerate(sfx.KINDS)], 0.1 * len(sfx.KINDS) + 1)
    assert np.isfinite(x).all() and np.abs(x).max() <= 0.9 + 1e-6
    return f"{len(sfx.KINDS)} 种音效都合成得出来"


@check
def script_gate_rules():
    import tempfile
    from vlab.tools import script_gate
    assert script_gate.is_confirmed(ROOT / "videos/009-redirect"), "009 的剧本确认记录没认出来"
    assert script_gate.formal_project(ROOT / "research/visual/15-stickfigure/x.yaml") is None
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "SCRIPT.md").write_text("剧本确认：待审\n", encoding="utf-8")
        assert not script_gate.is_confirmed(Path(d))
    return "已确认 / 待审 / research 不受限 都认得对"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    picked = [c for c in CHECKS if not args or any(a in c.__name__ for a in args)]
    if "--tsc" in sys.argv:
        picked.append(_tsc)
    return run(picked)


def run(picked=None) -> int:
    bad = 0
    for fn in picked or CHECKS:
        t = time.perf_counter()
        try:
            msg = fn()
            print(f"  OK {fn.__name__}：{msg}（{time.perf_counter() - t:.1f}s）")
        except Exception as e:  # noqa: BLE001
            bad += 1
            print(f"  NG {fn.__name__}：{type(e).__name__}: {e}")
    print(f"冒烟测试：{len(picked or CHECKS) - bad} 过，{bad} 没过")
    return 1 if bad else 0


def _tsc():
    import subprocess
    from vlab.render.remotion_bridge import REMOTION_DIR, _npx
    import os
    r = subprocess.run([os.environ.get("COMSPEC", "cmd"), "/c", _npx(), "tsc", "--noEmit"], cwd=str(REMOTION_DIR),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, (r.stdout or r.stderr)[-1500:]
    return "Remotion 类型检查 0 报错"


if __name__ == "__main__":
    sys.exit(main())
