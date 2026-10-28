"""009 的动作数据：算动作（choreo.py）→ 按镜头切成 build/009-redirect/shots/<镜头>.json → 音效事件表。

    uv run python videos/009-redirect/motion.py                     # 算动作、切镜头、出音效事件表
    uv run python videos/009-redirect/motion.py --sheet 16,22.5,38  # 另出一张骨架拼图（真实秒），几秒出图，改动作时用
    然后：uv run vlab-build videos/009-redirect/project.yaml

切出来的数据内容不变就不重写，vlab-build 按文件内容算指纹，没变的镜头直接复用。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import choreo  # noqa: E402
from vlab.stick.preview import sheet  # noqa: E402
from vlab.stick.scene import slice_data  # noqa: E402
from vlab.videokit.project import Project  # noqa: E402


def main():
    args = sys.argv[1:]
    sc, info = choreo.build()
    data, sfx = sc.export()
    P = Project(HERE / "project.yaml")
    beat = 60.0 / float(P.grid["bpm"])
    out = HERE / "build" / P.id / "shots"
    out.mkdir(parents=True, exist_ok=True)
    t, changed = 0.0, []
    for s in P.scenes:
        start, end = t, t + float(s["hold"]) * beat
        f0, f1 = round(start * choreo.FPS), round(end * choreo.FPS)
        txt = json.dumps(slice_data(data, f0, f1), ensure_ascii=False, separators=(",", ":"))
        path = out / f"{s['id']}.json"
        if not path.exists() or path.read_text(encoding="utf-8") != txt:
            path.write_text(txt, encoding="utf-8")
            changed.append(s["id"])
        t = end
    (HERE / "build" / P.id / "sfx_events.json").write_text(json.dumps(sfx, ensure_ascii=False, indent=1),
                                                           encoding="utf-8")
    print(f"动作：{data['frames']} 帧 / {t:.1f} 秒，{len(sfx)} 个音效事件；变了的镜头：{', '.join(changed) or '无'}")
    for k, v in info.items():
        print(f"  {k}：{v}")
    if "--sheet" in args:
        i = args.index("--sheet")
        times = [float(x) for x in args[i + 1].split(",")]
        media = HERE / "media"
        media.mkdir(exist_ok=True)
        name = next((a.split("=", 1)[1] for a in args if a.startswith("--name=")), "skeleton")
        print("骨架拼图：", sheet(data, times, media / f"{name}.png", cols=4, onion=1 if "--onion" in args else 0))


if __name__ == "__main__":
    main()
