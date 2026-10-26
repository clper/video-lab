# custom 渲染器：项目自带脚本画镜头

`project.yaml` 的 `renderer` 除了 `manim` / `remotion` / `glsl`，还有 `custom`：
一个镜头由项目里的 `.py` 自己画。它存在的理由是——卡库和模板覆盖不了的那个镜头，
不该逼着你把整个工程搬出去。

```yaml
scenes:
  - id: S1
    renderer: custom
    script: shots/stripes.py        # 相对项目目录
    narration: 这一镜的画面，是脚本直接画出来的。
    params: {text: CUSTOM}
    # args: ["--fast"]              # 可选：原样透传给脚本
```

## 脚本契约

`vlab-build` 这样调用它：

```
python shots/stripes.py --scene <临时 json> [args…]
```

临时 JSON 的字段：

| 字段 | 含义 |
|---|---|
| `out` | 要写出的 mp4（绝对路径）。脚本必须把它写出来，否则构建报错 |
| `frames` | 帧数。和帧数校验用同一套算法算出来，别自己按秒数取整 |
| `fps` | 帧率 |
| `width` / `height` | 画布尺寸 |
| `seconds` / `start` / `end` | 这一镜的时长和在整片时间轴上的位置 |
| `params` | 这一镜在 `project.yaml` 里的 `params` |
| `words` | 这一镜配音的词表 `[{text, start, end}…]`，可用来对齐画面 |

退出码非 0 或没写出 `out` 都算失败，构建会带着脚本的前后日志报错。

## 什么时候不该用它

`custom` 是逃生口，不是第二个模板库：

- 只是换文案/换数字 → 用 `params`，别写脚本；
- 同一个脚本被复制到第二个项目 → 该抽成 `toolkit/vlab/render/remotion/src/cards/` 的镜头卡，
  或 `manim_templates.py` 的模板；
- 只是要一个粒子/辉光背景 → 写 `.frag` 走 `glsl`，不用起 Python。

## 这个示例

`shots/stripes.py` 用 Pillow 逐帧画斜纹 + 标题 + 帧号，再交给 ffmpeg 编码。
故意包含三件容易做错的事，可以当作 checklist：

1. `-framerate` 与 `-r` 都显式写 `fps`，否则时长会飘；
2. 输出统一 `-pix_fmt yuv420p`——拼接环节按像素格式统一处理，写 `yuvj420p` 会和别的镜头对不上；
3. 帧数用 `frames` 而不是 `seconds * fps`，避免和整片的帧数校验差一帧。

跑法：

```powershell
uv run vlab-build research/visual/14-custom-renderer/project.yaml
uv run vlab-preview research/visual/14-custom-renderer/renders/custom-demo_demo.mp4 --times 1,2.5
```
