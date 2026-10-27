"""009 的镜头渲染脚本（videokit 的 custom 渲染器）：读这一镜的动作数据，交给 Remotion 卡 stickScene 画。

动作数据由 motion.py 算好、按镜头切成 build/009-redirect/shots/<镜头>.json（每段多带几帧前情，光迹和残影接得上）。
vlab-build 以 `python shots/stick.py --scene <临时 json>` 调用本脚本，JSON 里有 out / frames / fps / params / start。
"""
import json
import sys
from pathlib import Path

from vlab.render.remotion_bridge import render_shot

HERE = Path(__file__).resolve().parent.parent


def main():
    spec = json.loads(Path(sys.argv[sys.argv.index("--scene") + 1]).read_text(encoding="utf-8"))
    sid = spec["params"]["shot"]
    data = json.loads((HERE / "build" / "009-redirect" / "shots" / f"{sid}.json").read_text(encoding="utf-8"))
    want = spec["frames"]
    have = data["frames"] - data["offset"]
    if have != want:
        sys.exit(f"{sid}：动作数据 {have} 帧，镜头要 {want} 帧——project.yaml 改过拍数的话，先重跑 motion.py")
    fx = {"handheld": False, "stardust": False, "sweep": False, "flash": False}
    fx.update(spec["params"].get("fx") or {})
    render_shot("stickScene", spec["out"], spec["seconds"], params={"data": data}, fps=spec["fps"], frames=want,
                fx=fx, t0=round(spec["start"] * spec["fps"]), width=spec["width"], height=spec["height"],
                concurrency=3, quiet=True)


if __name__ == "__main__":
    main()
