"""视频工程：读取 project.yaml 和 style.yaml、校验、计算镜头指纹。

设计见 docs/design/DESIGN-video-project.md。
"""

import hashlib
import json
import os
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

# 渲染器：一个镜头用哪个后端出片。
#   manim     —— 参数化模板（manim_templates.py），适合图表/文字类
#   remotion  —— 镜头卡（toolkit/vlab/render/remotion/src/cards），适合高密度动效
#   glsl      —— 项目内的 .frag，适合粒子/场，走 render/glsl.py
#   custom    —— 项目自带的 .py 脚本，适合一次性特殊镜头（接口见 build.py 的 custom 分支）
RENDERERS = {"manim", "remotion", "glsl", "custom"}

# 模板需要的参数（校验用）。模板代码在 manim_templates.py
TEMPLATE_PARAMS = {
    "title_card": ["title"],
    "bar_compare": ["title", "bars"],
    "bullet_list": ["title", "items"],
}
ANIMS = {"fade", "fade_up", "pop", "write", "grow"}
CUE_KEYS = {"on", "nth", "offset", "anim"}
OVERRIDE_KEYS = {"dx", "dy", "scale", "color"}


class _Loader(yaml.SafeLoader):
    """YAML 1.1 会把 on/off/yes/no 当成布尔值（cues 里的 `on: 蓝光` 会变成 `True: 蓝光`）。
    这里改成和 YAML 1.2 一样，只有 true/false 才是布尔值。"""


_Loader.yaml_implicit_resolvers = {k: [r for r in v if r[0] != "tag:yaml.org,2002:bool"]
                                   for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
_Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
                              list("tTfF"))


def load_yaml(path):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_Loader)

DEFAULT_STYLE = {
    "name": "default",
    "palette": {"bg": "#070b16", "bg2": "#0f1a33", "ink": "#f8fafc", "dim": "#9ca3af",
                "accent1": "#fb7185", "accent2": "#60a5fa", "accent3": "#fbbf24"},
    "font": {"family": "Microsoft YaHei", "title_size": 56, "body_size": 40},
    "layout": {"title_y": 5.6, "content_y": 1.2},
    "motion": {"enter": "fade_up", "duration": 0.5, "stagger": 0.12, "easing": "smooth"},
    "texture": {"vignette": 0.0, "grain": 0},
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load_style(path) -> dict:
    data = load_yaml(path) or {}
    return _merge(DEFAULT_STYLE, data)


def resolve_color(style: dict, name: str) -> str:
    """颜色名（风格里的 ink、accent1…）或 #rrggbb → #rrggbb"""
    if isinstance(name, str) and name.startswith("#"):
        return name
    return style["palette"][name]


class Project:
    def __init__(self, path, style_path=None):
        self.path = Path(path).resolve()
        self.dir = self.path.parent
        self.data = load_yaml(self.path)
        self.id = self.data["id"]
        sp = Path(style_path) if style_path else self.dir / self.data.get("style", "")
        self.style_path = sp.resolve() if sp.suffix else None
        self.style = load_style(self.style_path) if self.style_path else dict(DEFAULT_STYLE)
        self.scenes = self.data["scenes"]
        self.fps = self.data.get("fps", 30)
        # 两种叙事模式：
        #   voice —— 有旁白，时长由配音定（原有做法）
        #   grid  —— 无旁白，时长由拍格定（写 grid: {bpm, beat}，每镜写 hold=占多少拍）
        self.grid = self.data.get("grid") or None
        self.mode = "grid" if self.grid else "voice"
        self.aspect = self.data.get("aspect", "portrait")

    # ----- 路径 -----
    @property
    def build_dir(self):
        return self.dir / "build" / self.id

    @property
    def timeline_path(self):
        return self.build_dir / "timeline.json"

    def clip_dir(self):
        sub = self.style["name"] + ("_preview" if os.environ.get("PREVIEW") == "1" else "")
        return self.dir / "media" / "clips" / sub

    # ----- 校验：渲染前把能发现的错误一次全列出来 -----
    def validate(self) -> list[str]:
        errs = []
        ids = [s.get("id") for s in self.scenes]
        if len(ids) != len(set(ids)):
            errs.append(f"镜头 id 重复：{ids}")
        for s in self.scenes:
            sid = s.get("id", "?")
            renderer = s.get("renderer", "manim")
            if renderer not in RENDERERS:
                errs.append(f"[{sid}] 渲染器「{renderer}」不认识，可选：{sorted(RENDERERS)}")
                continue
            params = s.get("params") or {}
            if renderer == "manim":
                tpl = s.get("template")
                if tpl not in TEMPLATE_PARAMS:
                    errs.append(f"[{sid}] 没有模板「{tpl}」，可选：{list(TEMPLATE_PARAMS)}")
                    continue
                for p in TEMPLATE_PARAMS[tpl]:
                    if p not in params:
                        errs.append(f"[{sid}] 模板 {tpl} 缺参数「{p}」")
                for c in _colors_in(params) + [o.get("color") for o in (s.get("overrides") or {}).values() if o.get("color")]:
                    if not c.startswith("#") and c not in self.style["palette"]:
                        errs.append(f"[{sid}] 颜色名「{c}」不在风格 {self.style['name']} 的色板里")
            elif renderer == "remotion":
                card = s.get("card")
                names = remotion_cards()
                if s.get("template"):
                    errs.append(f"[{sid}] renderer 是 remotion 时用 card 字段，不写 template")
                if not card:
                    errs.append(f"[{sid}] renderer 是 remotion，但没写 card")
                elif names and card not in names:
                    errs.append(f"[{sid}] 没有镜头卡「{card}」，可选：{', '.join(sorted(names))}")
            elif renderer == "custom":
                script = s.get("script")
                if not script:
                    errs.append(f"[{sid}] renderer 是 custom，但没写 script（相对项目目录的 .py）")
                elif not (self.dir / script).exists():
                    errs.append(f"[{sid}] 找不到自定义脚本 {script}")
            else:  # glsl
                frag = s.get("frag")
                if not frag:
                    errs.append(f"[{sid}] renderer 是 glsl，但没写 frag（相对项目目录的 .frag 路径）")
                elif not (self.dir / frag).exists():
                    errs.append(f"[{sid}] 找不到着色器 {frag}")
            narration = s.get("narration", "")
            if self.mode == "voice":
                if not narration:
                    errs.append(f"[{sid}] 没有旁白 narration")
            else:
                hold = s.get("hold")
                if not isinstance(hold, (int, float)) or hold <= 0:
                    errs.append(f"[{sid}] 拍格模式要写 hold（占几拍），现在是 {hold!r}")
            if self.mode == "grid":
                continue          # 拍格模式没有词时间点，cues/overrides 的绑定检查不适用
            for el, cue in (s.get("cues") or {}).items():
                bad = set(cue or {}) - CUE_KEYS
                if bad:
                    errs.append(f"[{sid}] 元素 {el} 的出场设置里有不认识的字段 {sorted(map(str, bad))}，可用：{sorted(CUE_KEYS)}")
                w = (cue or {}).get("on")
                if w and narration.count(w) < (cue.get("nth", 1)):
                    errs.append(f"[{sid}] 元素 {el} 绑定的词「{w}」在旁白里出现不到 {cue.get('nth', 1)} 次")
                if cue and cue.get("anim") and cue["anim"] not in ANIMS:
                    errs.append(f"[{sid}] 元素 {el} 的入场方式「{cue['anim']}」不认识，可选：{sorted(ANIMS)}")
            for el, o in (s.get("overrides") or {}).items():
                bad = set(o or {}) - OVERRIDE_KEYS
                if bad:
                    errs.append(f"[{sid}] 元素 {el} 的微调里有不认识的字段 {sorted(map(str, bad))}，可用：{sorted(OVERRIDE_KEYS)}")
        return errs

    # ----- 配音：从工程生成 tts.py 要的稿子 -----
    def content_json(self) -> dict:
        if self.mode == "grid":
            g = self.grid or {}
            bpm = float(g.get("bpm", 100))
            out = {"id": self.id, "title": self.data.get("title", self.id), "mode": "grid",
                   "fps": self.fps, "aspect": self.aspect,
                   "grid": {"bpm": bpm, "beat": float(g.get("beat") or 60.0 / bpm),
                            "lead": float(g.get("lead", 0.0))},
                   "scenes": [{"id": s["id"], "text": s.get("text", ""), "hold": s.get("hold"),
                               "sub_in": s.get("sub_in"), "sub_out": s.get("sub_out")} for s in self.scenes]}
            if "end_hold" in self.data:
                out["end_hold"] = self.data["end_hold"]
            return out
        v = self.data.get("voice", {})
        out = {"id": self.id, "title": self.data.get("title", self.id),
               "voice": v.get("name", "zh-CN-YunxiNeural"), "rate": v.get("rate", "+8%"),
               "scenes": [{"id": s["id"], "narration": s["narration"]} for s in self.scenes]}
        for k in ("aspect", "end_hold"):      # 可选：画幅、片尾停留（默认竖屏 / 1.6s）
            if k in self.data:
                out[k] = self.data[k]
        return out

    def narration_hash(self) -> str:
        return _sha(self.content_json())

    # ----- 镜头指纹：内容 + 风格 + 时间轴上的位置 + 渲染器代码，任何一项变了就重渲染 -----
    def scene_hash(self, scene: dict, tl_scene: dict) -> str:
        style = {k: v for k, v in self.style.items() if k not in ("source", "note")}   # 只算影响画面的字段，备注和来源路径变了不必重渲染
        renderer = scene.get("renderer", "manim")
        # fx_default 在工程顶层，不在 scene 里：不合并进来的话，改了全局特效（比如关白闪）
        # 指纹不变，镜头会被“复用”，改了半天等于没改
        fx = {"_default": self.data.get("fx_default") or {}, **(scene.get("fx") or {})}
        return _sha({"scene": scene, "style": style, "fx": fx, "start": tl_scene["start"], "end": tl_scene["end"],
                     "words": tl_scene["words"], "code": _code_hash(self.dir, scene, renderer), "fps": self.fps,
                     "preview": os.environ.get("PREVIEW") == "1"})


def _code_hash(project_dir: Path, scene: dict, renderer: str) -> str:
    """把渲染器代码也算进指纹：改了模板/卡片/着色器，相关镜头才会重渲染。"""
    if renderer == "manim":
        return hashlib.sha1((HERE / "manim_templates.py").read_bytes()).hexdigest()
    if renderer == "glsl":
        frag = project_dir / (scene.get("frag") or "")
        return hashlib.sha1(frag.read_bytes()).hexdigest() if frag.exists() else "missing"
    if renderer == "custom":
        script = project_dir / (scene.get("script") or "")
        h = hashlib.sha1(script.read_bytes() if script.exists() else b"missing")
        h.update(json.dumps(scene.get("args") or [], ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()
    # remotion：把 src 下所有 ts/tsx 一起算，改任何一张卡都会让 remotion 镜头失效；
    # 桥本身（像素格式、帧数算法）也会影响产物，一起算进去
    root = HERE.parent / "render" / "remotion" / "src"
    h = hashlib.sha1()
    bridge = HERE.parent / "render" / "remotion_bridge.py"
    if bridge.exists():
        h.update(bridge.read_bytes())
    for f in sorted(root.rglob("*.ts*")):
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


_CARDS: list[str] | None = None


def remotion_cards() -> list[str]:
    """可用镜头卡名（从 TS 注册表解析，避免 Python 侧再维护一份）。"""
    global _CARDS
    if _CARDS is None:
        from vlab.render.remotion_bridge import card_names
        _CARDS = card_names()
    return _CARDS


def _colors_in(params) -> list[str]:
    out = []
    if isinstance(params, dict):
        for k, v in params.items():
            if k == "color" and isinstance(v, str):
                out.append(v)
            else:
                out += _colors_in(v)
    elif isinstance(params, list):
        for v in params:
            out += _colors_in(v)
    return out


def _sha(obj) -> str:
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
