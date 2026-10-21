# AGENTS.md：给 AI 编程助手的说明

这是一个"用代码画科普视频"的仓库：Manim、GLSL 着色器、程序化画面渲染画面，Edge TTS 配音，FFmpeg 合成。
人类读的总览见 `README.md`；技术选型见 `docs/TECHNOLOGY.md`；选题时的风格和内容组合见 `docs/VIDEO-TYPES.md`；进度见 `docs/TODO.md`；设计文档在 `docs/design/`。

## 克隆后第一步（必做）

```powershell
uv sync              # 按 uv.lock 重建 .venv（没入库，和机器绑定），同时把 vlab 包装成命令
uv run vlab-check    # 环境自检：缺什么、怎么补一次列清楚；必需项不过会返回非 0
```

按自检输出补齐后再跑一次，直到"必需项全部通过"。之后所有 Python 命令都用 `uv run ...`，不要用系统 Python。

没入库、需要重建的东西（`.gitignore` 里有原因说明）：

| 内容 | 怎么重建 | 什么时候需要 |
|---|---|---|
| `.venv/` | `uv sync` | 总是 |
| `archive/000-claude-video-lab/2_hyperframes/node_modules/` | 在该目录 `npm ci`（PowerShell 用 `npm.cmd ci`） | 只在重做 000 的 HyperFrames 版时 |
| `ffmpeg`、`ffprobe` | 系统 PATH 上；Windows：`winget install Gyan.FFmpeg` | 总是 |
| 字体 Microsoft YaHei、Cascadia Mono | 系统字体；Cascadia：`winget install Microsoft.CascadiaCode` | 总是（缺了 Manim 会悄悄换字体） |
| 支持 OpenGL 3.3 的显卡 | 硬件 | 只在重渲染着色器镜头时（003 的 hook/noon/sunset、research/visual/07） |
| 联网 | — | 只在重新配音时（Edge TTS 是在线服务） |

## 目录和依赖方向

根目录 5 个文件夹各是一类：

```
videos/      【项目结果】正式视频（001、002、003…），一条一个目录
research/    【开发测试】visual/ 画面技术（01–11）、audio/ 音频研究、frontier/ 前沿视频生成；实验目录都是 NN-主题/
toolkit/     【工具】vlab/ 公共代码包（pipeline 配音合成、render 渲染器、scenes 可复用画面、videokit 视频工程、tools 工具）；bin/ 本机可选的程序
docs/        【文档】TECHNOLOGY.md、VIDEO-TYPES.md、TODO.md、design/
archive/     【存档】000 参考项目的只读快照：不要改，它自带的 shared/ 和环境配置只属于它自己
```

- **新东西放哪**：做成片 → `videos/`；做试验、调研 → `research/` 下对应的区；会被多个项目复用的代码 → `toolkit/vlab/`；说明文档 → `docs/`。
- **`videos/` 和 `research/` 只依赖 `toolkit/vlab/`，彼此不互相引用；`research/` 下三个区之间也不互相引用。**
  想在正式视频里用试验出来的东西，先把它提升进 `toolkit/vlab/`（比如 `toolkit/vlab/scenes/landscape.py` 就是从 research/visual/06 提升上来的），再从两边引用。
- **公共代码只有一份**：不要把 `toolkit/vlab/` 里的文件复制到项目里。Python 里照常 `import vlab`。
- **密钥和模型权重不入库**：API Key 只放本地 `.env`（可以入库不含真实值的 `.env.example`）；模型权重放在 `weights/` 目录或系统缓存里，`.gitignore` 已忽略，在实验 README 里写清下载方式。
- 项目内部按技术分子目录：`manim/`、`shader/`、`hyperframes/`、`landscape/`；`content/` 稿子、`build/` 配音时间轴字幕、`renders/` 成片。

## 仓库里已有的成果：不要轻易重做

仓库带了所有成片、配音、时间轴、字幕和分镜片段，克隆后不用渲染就能看、能拼。

- **不要随手重跑配音**（`vlab-tts`）。Edge TTS 每次生成的语速和词时间点可能不同，
  `build/<id>/timeline.json` 一变，整条视频的画面就要全部重渲染才能对齐。只有旁白文字改了才重跑。
- **003 的着色器片段要显卡才能重渲染**，平时直接用 `videos/003-sunset-red/media/clips/` 里的现成片段，
  `uv run python build.py` 会跳过已有片段、只做拼接。
- **视频工程（videokit）有缓存**：`media/clips/<风格>/*.hash` 是镜头指纹，指纹没变就复用，不要删。

## 常用命令（任意目录可用）

| 要做的事 | 命令 |
|---|---|
| 配音 | `uv run vlab-tts <项目>/content/<稿子>.json` |
| 合配音、烧字幕 | `uv run vlab-finalize <无声画面.mp4> <项目>/build/<id> <输出.mp4>` |
| 看渲染结果 | `uv run vlab-preview <视频> --timeline <timeline.json>` → 每个分镜的结尾画面拼成一张图 |
| 视频工程构建 | `uv run vlab-build research/visual/08-video-spec/project.yaml [--style ...] [--check]` |
| 分析参考视频的风格 | `uv run vlab-style <视频> <输出目录>` |
| 环境自检 | `uv run vlab-check` |
| 003 重新拼成片 | `cd videos/003-sunset-red; uv run python build.py`（`--force` 全部重渲染） |
| 001 / 002 重渲染 | `cd videos/00x-...; uv run python -m manim render manim/scene.py <场景类> --format mp4`，再 `uv run vlab-finalize ...`（见 README） |
| 低清快速预览 | 先设 `$env:PREVIEW='1'`（540×960、15fps） |

## 工作约定

- **渲染 → 看图 → 改**：改画面后一定用 `vlab-preview` 抽帧看图确认，不要只看代码就说"改好了"。
- **画面跟着配音走**：画面元素绑定到配音里的"词"（`timeline.json` 的 words），不要写死秒数。
- **新视频优先用视频工程**（`toolkit/vlab/videokit`，设计见 `docs/design/DESIGN-video-project.md`）：
  文案、数据、颜色、出场时机写在 `project.yaml` 里，常规镜头走模板；只有特殊镜头才写定制代码。
- **入库原则**：渲染成果要入库（克隆即可用），环境和缓存碎片不入库；新增产物类型时先看 `.gitignore` 的规则说明。
- **没有用户明确说"提交"/"推送"，不要 `git commit` / `git push`**。改完列出改动文件，等用户指令。

## 已知坑

- **仓库路径含中文括号【】**：Python 3.11 在中文 Windows 上按 GBK 读 `.pth`（开 UTF-8 模式也一样），
  可编辑安装写进 `.pth` 的仓库路径会被读坏。已在 `pyproject.toml` 里另装一个纯 ASCII 的 `_vlab_root.pth` 解决；
  如果 `import vlab` 失败，先 `uv sync --reinstall-package video-lab`。
- `uv run` 提示 `VIRTUAL_ENV ... does not match`：本机激活了别的虚拟环境，无害，uv 仍用仓库的 `.venv`。
- Manim：要 `config.disable_caching = True`（缓存会让时间轴错位）；分辨率用 `PREVIEW` 环境变量切换，`-ql` 会被脚本里的设置覆盖；
  对齐时间要按"当前真实帧数"补齐，冻结帧和逐帧两种等待的取整方式不同（见各 scene.py 的 `wait_to`）。
- Edge TTS 的分词和直觉不同（如"四次方"切成 四/次/方）：绑定的词必须是 `timeline.json` 里的词；
  videokit 配音后会校验并列出可用的词。
- YAML 1.1 会把 `on`/`yes`/`no` 当布尔值：工程文件一律用 `vlab.videokit.project.load_yaml` 读，别用 `yaml.safe_load`。
- Windows 显卡超时（约 2 秒）会重置驱动：重着色器要分块渲染（`toolkit/vlab/render/glsl.py` 已处理）。
- 这台机器的 ffmpeg `drawtext` 没有字体配置会崩：画面上叠字用 Pillow，不用 drawtext。
- PowerShell 执行策略：npm 要写成 `npm.cmd`。
- `.gitignore` 不支持行尾注释，注释必须单独一行。
