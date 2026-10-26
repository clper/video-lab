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

**在做：**

| 编号 | 视频 | 路线 | 状态 |
|---|---|---|---|
| 008 | [你没火，可能只是没被选中](videos/008-cumulative/) | 主线：硬知识 + 人生落点 | 剧本已确认（2026-10-26，剧本闸门见 [process/SCRIPT-REVIEW.md](process/SCRIPT-REVIEW.md)），制作中 |
| 007 | [回归](videos/007-regression/) | 主线：硬知识 + 人生落点 | 暂停（2026-10-26），剧本未审 |

**已归档：** 001–006 是开发过程中的探索作品，2026-10-26 归档到 `archive/`，不再是主力视频。
介绍、重新生成成片的方法和实测结果见 [archive/README.md](archive/README.md)。

| 编号 | 视频 | 技术 | 时长 |
|---|---|---|---|
| 001 | [0.1 + 0.2 为什么不等于 0.3](archive/001-float-precision/) | Manim 2D | 45.74 秒 |
| 002 | [莫比乌斯环：只有一个面的奇迹](archive/002-mobius-strip/) | Manim 3D | 52.62 秒 |
| 003 | [夕阳为什么是红的](archive/003-sunset-red/) | 着色器 + Manim + 程序化风景混剪 | 60.95 秒 |
| 004 | [为什么没有绿色的恒星](archive/004-green-star/) | Manim + 着色器 + 文字动效（横屏） | 210.45 秒 |
| 005 | [涌现](archive/005-emergence/) | Remotion 镜头卡库 + 着色器 | 61.33 秒 |
| 006 | [对折](archive/006-fold/) | Remotion 镜头卡库，纯音乐 + 字幕（横屏） | 180 秒 |

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

根目录只有 6 个文件夹，每个对应一类，首字母各不相同，一眼就能分清：

| 文件夹 | 类别 | 放什么 |
|---|---|---|
| `videos/` | **项目结果** | 正在做的正式视频（现在是 008；007 暂停），一条一个目录；受剧本闸门约束 |
| `research/` | **开发测试** | 试验和调研，结论不一定稳定：`visual/` 画面技术、`audio/` 音频、`frontier/` 前沿视频生成、`content/` 创作内容（方向、平台、合规） |
| `toolkit/` | **工具** | 所有项目共用：`vlab/` 公共代码包（`vlab-*` 命令）、`bin/` 本机可选的程序 |
| `process/` | **流程** | 我们的流程和流程规则：内容路线、剧本审核、传播与节奏规范、发布清单、入库与提交；必须遵守，只由项目负责人改 |
| `docs/` | **文档** | 参考资料：技术路线、视频类型纲要、TODO、设计文档 |
| `archive/` | **存档** | 不再开发的东西：000 参考项目，001–006 归档的探索作品 |

```
AI-Vedio/
├── videos/              【项目结果】
│   ├── 008-cumulative/  《你没火，可能只是没被选中》，制作中
│   └── 007-regression/  《回归》，暂停
├── research/            【开发测试】
│   ├── visual/          画面技术 01–14（13 Remotion 样片、 14 custom 渲染器示例）
│   ├── audio/           音频研究
│   ├── content/         创作内容研究：方向、平台、合规
│   └── frontier/        前沿视频生成
├── toolkit/             【工具】
│   ├── vlab/            pipeline 配音合成 · audio 音效配乐混音 · fonts 项目字体 · render 渲染器 · scenes 可复用画面 · videokit 视频工程 · tools 预览自检
│   └── bin/             可选：本机的 ffmpeg 等程序（不入库）
├── process/             【流程】内容路线 · 剧本审核 · 传播与节奏规范 · 发布清单 · 入库与提交
├── docs/                【文档】
├── archive/             【存档】
│   ├── 000-claude-video-lab/  参考项目（只读快照）
│   └── 001–006/         归档的探索作品，成片不入库，可从入库的输入重新生成
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

重生成成片需要的输入都在仓库里，克隆下来不用重新配音、不用重渲染。`videos/` 下正在做的片子带着成片；`archive/` 和 `research/` 的成片不入库，有 ffmpeg 就能拼出来（规则见 [process/REPO.md](process/REPO.md)）：

| 已在仓库里 | 位置 |
|---|---|
| 配音、配乐、词级时间轴、字幕 | 各项目 `build/<id>/`（narration.wav、music_*.wav、timeline.json、subs.ass/srt） |
| 分镜片段（拼接成片用） | 各项目 `media/clips/`、`media/videos/`（带 `.hash` 指纹的，增量构建直接复用） |
| 项目字体 | `toolkit/vlab/assets/fonts/`（思源黑体） |

需要一条命令重建的（和机器绑定，或者是成片，没有入库）：

| 内容 | 命令 |
|---|---|
| Python 环境 `.venv` | 根目录 `uv sync`（依赖锁在 `pyproject.toml` / `uv.lock`，配了清华 PyPI 镜像） |
| 归档和研究区的成片 | 见下面「重新生成成片」 |
| Remotion 依赖（重渲 remotion 镜头时） | `cd toolkit/vlab/render/remotion; npm.cmd install` |
| 000 的 HyperFrames 依赖 | `cd archive/000-claude-video-lab/2_hyperframes; npm ci` |
| 系统依赖 | PATH 上的 `ffmpeg`；重生成 001–003 的字幕要 Microsoft YaHei，001 要 Cascadia Mono |
| 显卡（只在重渲染着色器镜头时需要） | 支持 OpenGL 3.3 的显卡；只拼接成片不需要 |

2026-10-26 实测：001–004 在归档后的位置重新生成，和原成片逐帧一致，音频一致（见 [archive/README.md](archive/README.md)）。

### 公共命令（任意目录可用）

| 命令 | 作用 |
|---|---|
| `uv run vlab-tts <项目>/content/<稿子>.json` | 稿子 → 配音 + 词级时间轴 + 字幕（写到该项目的 `build/<id>/`） |
| `uv run vlab-finalize <无声画面.mp4> <项目>/build/<id> <输出.mp4>` | 合配音、烧字幕 → 成片 |
| `uv run vlab-preview <视频> --timeline <timeline.json>` | 每个分镜的结尾画面拼成一张图，看图检查 |
| `uv run vlab-build <project.yaml> [--style ...] [--check]` | 视频工程 → 成片（增量渲染） |
| `uv run vlab-review <project.yaml> [--loudness]` | 成片体检：节奏硬指标 + 逐帧质检 + 响度（标准见 `process/STYLE-RHYTHM.md`） |
| `uv run vlab-ab <成片1> <成片2> … --out <png>` | 几条成片并排 A/B 对照图 |
| `uv run vlab-cards --out <png>` | 卡库一览：把每张镜头卡渲一段抽帧拼图 |
| `uv run vlab-style <参考视频> <输出目录>` | 分析参考视频风格 → 草稿风格文件 |
| `uv run vlab-check` | 环境自检 |

### 重新生成成片

```powershell
# 001、002：Manim 中间视频已入库，直接合配音、烧字幕
cd archive/001-float-precision
uv run vlab-finalize media/videos/scene/1920p30/FloatPrecision.mp4 build/float-precision renders/float-precision_final.mp4
cd archive/002-mobius-strip
uv run vlab-finalize media/videos/scene/1920p30/MobiusStrip.mp4 build/mobius-strip renders/mobius-strip_final.mp4

# 003、004：总装脚本跳过已有片段，只做拼接和混音
cd archive/003-sunset-red; uv run python build.py
cd archive/004-green-star; uv run python build.py
```

005 没法完美重生成；006 要先装 Remotion 依赖、重渲全部镜头才能重生成。原因见 [archive/README.md](archive/README.md)。

### 开发新视频

**剧本闸门（不可逾越）**：视频的所有文字都要项目负责人逐条审核、讨论打磨，明确说"确认剧本完善"之后才能配音和渲染。
流程见 [process/SCRIPT-REVIEW.md](process/SCRIPT-REVIEW.md)；`videos/` 下的项目没有确认记录时，`vlab-tts` 和 `vlab-build` 会拒绝执行。

1. 建项目目录 `videos/三位编号-英文名/`，写 `SCRIPT.md`：全部文字按镜号列出，事实和数字标来源，开头写"剧本确认：待审"
2. 项目负责人逐条审核，和 AI 讨论修改，直到负责人明确确认
3. 写 `project.yaml`：每个镜头用哪个渲染器（manim、remotion、glsl、custom）、哪张卡、传什么参数；
   设计见 [docs/design/DESIGN-video-project.md](docs/design/DESIGN-video-project.md)，例子见 `videos/007-regression/`
4. 构建：`uv run vlab-build videos/xxx/project.yaml`（先配音，再按镜头渲染、拼接、混音；增量缓存）
5. 体检：`uv run vlab-review videos/xxx/project.yaml --loudness`，看图：`uv run vlab-preview <成片> --timeline <timeline.json>`

`build/`（配音、时间轴、字幕、配乐）、`media/clips/`（分镜片段）和 `renders/` 的成片都入库；片子归档后成片不再入库，见 [process/REPO.md](process/REPO.md)。

---

## 许可证

本项目代码采用 MIT 许可证。视频内容（文案、配音）版权归作者所有。
