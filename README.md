# AI-Vedio

**个人 IP 科普视频项目** —— 用代码生成高质量科普视频。

---

## 项目概览

本仓库包含多个 AI 生成的科普视频项目，采用「代码渲染」路线（非像素级 AI 生成），确保：
- **确定性**：改一行代码，重出一版，完全可复现
- **低成本**：本地渲染，零 API 费用
- **Agent 友好**：HTML/Python 是 LLM 最擅长的输出格式

---

## 视频作品

| 编号 | 项目 | 技术 | 时长 | 状态 |
|---|---|---|---|---|
| 001 | [float-precision](videos/001-float-precision/) | Manim 2D（另有 HyperFrames 版） | 45.74 秒 | ✅ 完成 |
| 002 | [mobius-strip](videos/002-mobius-strip/) | Manim 3D | 52.62 秒 | ✅ 完成 |
| 003 | [sunset-red](videos/003-sunset-red/) | 着色器 + Manim + 程序化风景（混剪） | 60.95 秒 | ✅ 完成 |
| 004 | [green-star](videos/004-green-star/) | Manim + 程序化画面（横屏，26 镜） | 210.45 秒 | ✅ 完成 |
| 005 | [emergence](videos/005-emergence/) | Remotion 镜头卡库 + 着色器（竖屏，15 镜） | 61.33 秒 | ✅ 完成 |

### 001-float-precision《0.1 + 0.2 为什么不等于 0.3》

**题材**：浮点数精度（计算机科普）  
**技术**：Manim 2D 几何动画 + Edge TTS 配音 + 字幕烧录；`hyperframes/` 里是 HTML + GSAP 的另一版  
**亮点**：二进制位流动、尾数格子截断、误差累积可视化

### 002-mobius-strip《莫比乌斯环：只有一个面的奇迹》

**题材**：拓扑学（数学/几何科普）  
**技术**：Manim 3D 参数曲面 + Edge TTS 配音 + 字幕烧录  
**亮点**：莫比乌斯环连续变形、蚂蚁爬行路径、剪开动画

### 003-sunset-red《夕阳为什么是红的》

**题材**：瑞利散射（物理/大气科普）  
**技术**：多技术混剪，每个分镜用最合适的技术，帧数按配音时间轴精确拼接——
开场 GLSL 着色器云海飞越雪山；原理讲解 Manim；中午蓝天和日落晚霞用按真实物理公式计算的大气散射着色器（只改太阳高度，蓝天、红日、晚霞都是公式算出来的）；结尾复用程序化日落湖景  
**一键重出**：`cd videos/003-sunset-red; uv run python build.py`

### 004-green-star《为什么没有绿色的恒星》

3 分 30 秒，横屏 1920×1080，26 镜。Manim 讲光谱和普朗克曲线，着色器画星空、太阳和大气，
文字动效做转折。关键数据：太阳在蓝、绿、红三段的强度是 0.99 : 1.00 : 0.88，几乎相等，所以看起来是白的。

**一键重出**：`cd videos/004-green-star; uv run python build.py`（先 `--check` 看缺哪些片段）

### 005-emergence《涌现》

61 秒，竖屏 1080×1920，15 镜。对标头部知识区 UP 主的第一条全量片：13 个镜头由 Remotion
镜头卡库拼出（鸟群、科技卡、生命游戏、量级卡、粒子聚字…），2 个是着色器背景，
画面密度按 `docs/STYLE-RHYTHM.md` 的硬指标反推着排（平均 4.09s、最长 5.05s、组件覆盖 100%）。

**重建 + 体检**：`uv run vlab-build videos/005-emergence/project.yaml`
然后 `uv run vlab-review videos/005-emergence/project.yaml --loudness`

---

## 存档：参考项目

| 项目 | 说明 |
|---|---|
| [000-claude-video-lab](archive/000-claude-video-lab/) | Claude 开发的参考项目（只读快照），同一题目「蜂巢为什么是六边形」用三种技术各做一版（Pillow/HyperFrames/Manim） |

---

## 技术路线

详见 [docs/TECHNOLOGY.md](docs/TECHNOLOGY.md) —— 技术选型、工作流、踩坑记录、命名约定、未来方向。进度见 [docs/TODO.md](docs/TODO.md)。
选题时先查 [docs/VIDEO-TYPES.md](docs/VIDEO-TYPES.md) —— 画面风格可做纲要、内容形态、两者怎么组合。

**核心原则**：效果优先，技术为内容服务，可以混合使用。

| 内容类型 | 首选技术 |
|---|---|
| 数学科普/抽象概念 | Manim（几何连续变形） |
| 数据可视化/动态图表 | HyperFrames 或 Remotion |
| 图文卡片/简单动画 | Pillow 或 HyperFrames |
| 风景、氛围、震撼空镜 | 程序化风景 / GLSL 着色器 |
| 人物小故事、复古游戏感 | 像素风（research/visual/11） |
| 金句、歌词、数字冲击 | 文字动效（research/visual/12） |
| 真人/实拍 | 像素级生成（Seedance/可灵） |
| 写实 3D 场景 | Blender |

---

## 目录结构

根目录只有 5 个文件夹，每个对应一类，首字母各不相同，一眼就能分清：

| 文件夹 | 类别 | 放什么 |
|---|---|---|
| `videos/` | **项目结果** | 正式视频，一条一个目录：稿子、配音、分镜片段、成片 |
| `research/` | **开发测试** | 试验和调研，结论不一定稳定：`visual/` 画面技术、`audio/` 音频、`frontier/` 前沿视频生成、`content/` 创作内容（方向、平台、合规） |
| `toolkit/` | **工具** | 所有项目共用：`vlab/` 公共代码包（`vlab-*` 命令）、`bin/` 本机可选的程序 |
| `docs/` | **文档** | 技术路线、视频类型纲要、TODO、设计文档 |
| `archive/` | **存档** | 只读快照（000 参考项目），不再修改 |

```
AI-Vedio/
├── videos/              【项目结果】
│   ├── 001-float-precision/
│   ├── 002-mobius-strip/
│   ├── 003-sunset-red/
│   ├── 004-green-star/  第一条横屏片
│   └── 005-emergence/   第一条 Remotion 全量片（竖屏）
├── research/            【开发测试】
│   ├── visual/          画面技术 01–14（13 Remotion 样片、 14 custom 渲染器示例）
│   ├── audio/           音频研究
│   ├── content/         创作内容研究：方向、平台、合规
│   └── frontier/        前沿视频生成
├── toolkit/             【工具】
│   ├── vlab/            pipeline 配音合成 · audio 音效配乐混音 · fonts 项目字体 · render 渲染器 · scenes 可复用画面 · videokit 视频工程 · tools 预览自检
│   └── bin/             可选：本机的 ffmpeg 等程序（不入库）
├── docs/                【文档】
├── archive/             【存档】
│   └── 000-claude-video-lab/
└── README.md  AGENTS.md  CLAUDE.md  pyproject.toml  uv.lock  .gitignore
```

依赖方向：`videos/` 和 `research/` 只依赖 `toolkit/vlab/`，彼此不互相引用；可复用的东西先提升进 `toolkit/vlab/` 再用。
每个文件夹里都有一份简短的 README，写明它放什么、不放什么。

---

## 快速开始

### 克隆后直接使用

```powershell
uv sync              # 重建 Python 环境，同时把 vlab 装成命令
uv run vlab-check    # 环境自检：缺什么、怎么补一次列清楚
```

AI 助手请先读根目录的 `AGENTS.md`（Claude Code 读 `CLAUDE.md`，内容相同）：里面写了重建步骤、哪些成果不要轻易重做、已知坑。

仓库里已经带了所有成果，克隆下来不用重新配音、不用重渲染：

| 已在仓库里 | 位置 |
|---|---|
| 成片 | `videos/*/renders/`、`research/visual/*/renders/`、`archive/000-claude-video-lab/out/` |
| 配音、词级时间轴、字幕 | `videos/*/build/<id>/`（narration.wav、timeline.json、subs.ass/srt） |
| 分镜片段（拼接成片用） | `videos/003-sunset-red/media/clips/`、`media/videos/`；`research/visual/08-video-spec/media/clips/`（带 `.hash` 指纹，增量构建直接复用） |
| Manim 成品视频 | 各项目 `media/videos/**/1920p30/` |

需要一条命令重建的（和机器绑定，没有入库）：

| 内容 | 命令 |
|---|---|
| Python 环境 `.venv` | 根目录 `uv sync`（依赖锁在 `pyproject.toml` / `uv.lock`，配了清华 PyPI 镜像） |
| 000 的 HyperFrames 依赖 | `cd archive/000-claude-video-lab/2_hyperframes; npm ci` |
| 系统依赖 | PATH 上的 `ffmpeg`；Microsoft YaHei、Cascadia Mono 字体 |
| 显卡（只在重渲染着色器镜头时需要） | 支持 OpenGL 3.3 的显卡；只拼接成片不需要 |

验证过：只拿入库的文件放到空目录里，`uv sync` 后 003 的 `build.py` 不渲染任何片段直接拼出成片，
视频工程演示的两种风格直接命中缓存。

### 公共命令（任意目录可用）

| 命令 | 作用 |
|---|---|
| `uv run vlab-tts <项目>/content/<稿子>.json` | 稿子 → 配音 + 词级时间轴 + 字幕（写到该项目的 `build/<id>/`） |
| `uv run vlab-finalize <无声画面.mp4> <项目>/build/<id> <输出.mp4>` | 合配音、烧字幕 → 成片 |
| `uv run vlab-preview <视频> --timeline <timeline.json>` | 每个分镜的结尾画面拼成一张图，看图检查 |
| `uv run vlab-build <project.yaml> [--style ...] [--check]` | 视频工程 → 成片（增量渲染） |
| `uv run vlab-review <project.yaml> [--loudness]` | 成片体检：节奏硬指标 + 逐帧质检 + 响度（标准见 `docs/STYLE-RHYTHM.md`） |
| `uv run vlab-ab <成片1> <成片2> … --out <png>` | 几条成片并排 A/B 对照图 |
| `uv run vlab-cards --out <png>` | 卡库一览：把每张镜头卡渲一段抽帧拼图 |
| `uv run vlab-style <参考视频> <输出目录>` | 分析参考视频风格 → 草稿风格文件 |
| `uv run vlab-check` | 环境自检 |

### 重新渲染已有视频

```powershell
# 001 浮点数精度（build/ 里已有配音和时间轴，可直接渲染；改了稿子才需要重跑 vlab-tts）
cd videos/001-float-precision
uv run python -m manim render manim/scene.py FloatPrecision --format mp4
uv run vlab-finalize media/videos/scene/1920p30/FloatPrecision.mp4 build/float-precision renders/float-precision_final.mp4

# 002 莫比乌斯环
cd videos/002-mobius-strip
uv run python -m manim render manim/scene.py MobiusStrip --format mp4
uv run vlab-finalize media/videos/scene/1920p30/MobiusStrip.mp4 build/mobius-strip renders/mobius-strip_final.mp4

# 003 夕阳为什么是红的（多技术混剪，缺哪段渲染哪段再拼接）
cd videos/003-sunset-red
uv run python build.py
```

低清预览：先设 `$env:PREVIEW='1'` 再渲染（540×960、15fps，输出在 `media/videos/scene/960p15/`）。

### 开发新视频

两种方式：

- **常规镜头为主**：用视频工程（`toolkit/vlab/videokit`，设计见 [docs/design/DESIGN-video-project.md](docs/design/DESIGN-video-project.md)），
  写 `project.yaml` 选模板填参数，`uv run vlab-build project.yaml`；示例见 `research/visual/08-video-spec/`。
- **定制镜头为主**：
  1. 创建项目目录：`videos/004-xxx/`
  2. 写剧本：`content/xxx.json`
  3. 跑配音：`uv run vlab-tts content/xxx.json`
  4. 写动画：`manim/scene.py`（可复用的画面放进 `toolkit/vlab/scenes/`）
  5. 渲染：`uv run python -m manim render manim/scene.py SceneName --format mp4`
  6. 看图：`uv run vlab-preview media/videos/scene/1920p30/SceneName.mp4 --timeline build/xxx/timeline.json`
  7. 合成：`uv run vlab-finalize media/videos/scene/1920p30/SceneName.mp4 build/xxx renders/xxx_final.mp4`

`build/`（配音、时间轴、字幕）和 `renders/`（成片）都要入库，见 `.gitignore` 里的说明。

---

## 许可证

本项目代码采用 MIT 许可证。视频内容（文案、配音）版权归作者所有。
