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
            sid, tpl = s.get("id", "?"), s.get("template")
            if tpl not in TEMPLATE_PARAMS:
                errs.append(f"[{sid}] 没有模板「{tpl}」，可选：{list(TEMPLATE_PARAMS)}")
                continue
            params = s.get("params") or {}
            for p in TEMPLATE_PARAMS[tpl]:
                if p not in params:
                    errs.append(f"[{sid}] 模板 {tpl} 缺参数「{p}」")
            narration = s.get("narration", "")
            if not narration:
                errs.append(f"[{sid}] 没有旁白 narration")
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
            for c in _colors_in(params) + [o.get("color") for o in (s.get("overrides") or {}).values() if o.get("color")]:
                if not c.startswith("#") and c not in self.style["palette"]:
                    errs.append(f"[{sid}] 颜色名「{c}」不在风格 {self.style['name']} 的色板里")
        return errs

    # ----- 配音：从工程生成 tts.py 要的稿子 -----
    def content_json(self) -> dict:
        v = self.data.get("voice", {})
        return {"id": self.id, "title": self.data.get("title", self.id),
                "voice": v.get("name", "zh-CN-YunxiNeural"), "rate": v.get("rate", "+8%"),
                "scenes": [{"id": s["id"], "narration": s["narration"]} for s in self.scenes]}

    def narration_hash(self) -> str:
        return _sha(self.content_json())

    # ----- 镜头指纹：内容 + 风格 + 时间轴上的位置 + 模板代码，任何一项变了就重渲染 -----
    def scene_hash(self, scene: dict, tl_scene: dict) -> str:
        code = (HERE / "manim_templates.py").read_bytes()
        style = {k: v for k, v in self.style.items() if k not in ("source", "note")}   # 只算影响画面的字段，备注和来源路径变了不必重渲染
        return _sha({"scene": scene, "style": style, "start": tl_scene["start"], "end": tl_scene["end"],
                     "words": tl_scene["words"], "code": hashlib.sha1(code).hexdigest(), "fps": self.fps,
                     "preview": os.environ.get("PREVIEW") == "1"})


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
