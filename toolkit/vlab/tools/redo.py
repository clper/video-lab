"""只重渲指定的几个镜头，其余镜头回写指纹。

为什么要有这个：remotion 的镜头指纹算的是整个 `src/**/*.ts*`，改任何一张卡，全片几十个镜头
全会判成"指纹变了"要重渲，而其中绝大多数镜头画面一模一样。改一张卡的落点通常只影响几个镜头。

用法（任意目录）：
    uv run python -m vlab.tools.redo <项目.yaml> H4 L1 D1 D2

做了两件事：
1. 把要重渲的旧片段改名移到 media/_trash/（不是删除：批量删除会撞上 safe-delete 的轮次阈值，
   而且 render_shot 内部要 out.unlink()，移走之后它就不用删了）；
2. 重渲指定镜头，然后给其余镜头按当前 project.yaml + timeline 回写 .hash，
   下一次 vlab-build 就只做拼接，不会重渲全片。

注意：改了卡的公共代码以后要自己判断哪些镜头受影响；漏掉的镜头会沿用旧画面。
拿不准就先重渲整段（比如用同一张卡的所有镜头），或者干脆跑一次全片 vlab-build。
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from vlab.videokit.project import Project
from vlab.videokit.build import render_scene


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="只重渲指定镜头，其余回写指纹")
    ap.add_argument("project", help="project.yaml 路径")
    ap.add_argument("shots", nargs="+", help="要重渲的镜号，空格分隔")
    ap.add_argument("--jobs", type=int, default=2, help="并发数（remotion 在 Windows 上别超过 2）")
    args = ap.parse_args(argv)

    P = Project(args.project)
    tl = json.loads(P.timeline_path.read_text(encoding="utf-8"))
    tls = {s["id"]: s for s in tl["scenes"]}
    fps = 15 if os.environ.get("PREVIEW") == "1" else P.fps
    redo = set(args.shots)

    unknown = redo - {s["id"] for s in P.scenes}
    if unknown:
        print(f"工程里没有这些镜号：{', '.join(sorted(unknown))}")
        return 1

    trash = P.dir / "media" / "_trash"
    trash.mkdir(parents=True, exist_ok=True)
    moved = 0
    for sid in sorted(redo):
        src = P.clip_dir() / f"{sid}.mp4"
        if src.exists():
            os.replace(str(src), str(trash / f"{sid}.old.mp4"))
            moved += 1

    todo = [s for s in P.scenes if s["id"] in redo]
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        for msg in ex.map(lambda s: render_scene(P, s, tls[s["id"]], None, True, fps), todo):
            print(msg)

    n = 0
    for s in P.scenes:
        if s["id"] in redo:
            continue
        if (P.clip_dir() / f"{s['id']}.mp4").exists():
            (P.clip_dir() / f"{s['id']}.mp4").with_suffix(".hash").write_text(P.scene_hash(s, tls[s["id"]]))
            n += 1
    print(f"重渲 {len(todo)} 个镜头（旧片段移到 {trash.name}/），回写指纹 {n} 个镜头")
    print("旧片段确认没用了再自己删掉 media/_trash/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
