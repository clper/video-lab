# AGENTS.md：给 AI 编程助手的说明

这是一个"用代码画科普视频"的仓库：Manim、GLSL 着色器、程序化画面渲染画面，Edge TTS 配音，代码合成音效和配乐，FFmpeg 混音合成。
人类读的总览见 `README.md`；**流程和规则见 `process/`（必须遵守）**；技术选型见 `docs/TECHNOLOGY.md`；选题时的风格和内容组合见 `docs/VIDEO-TYPES.md`；进度见 `docs/TODO.md`；设计文档在 `docs/design/`。

## 剧本闸门（不可逾越）

**视频的所有文字**（标题、封面字、旁白、字幕、画面上的每一行字）都必须由项目负责人逐条审核、和 AI 讨论打磨；
负责人明确说"确认剧本完善"之后，才能进入下一步：配音、渲染、合成。流程见 `process/SCRIPT-REVIEW.md`（2026-10-26 项目负责人定）。

- AI 不得自行判定剧本已完成，不得替负责人在 `SCRIPT.md` 里写"剧本确认：已确认"。
- 确认之后改了任何文字，确认作废：把那一行改回"剧本确认：待审"，写明改了什么，重新请负责人审。
- 工具会拦：`videos/` 下的正式项目没有确认记录时，`vlab-tts` 和 `vlab-build` 拒绝执行（`--check` 只校验，不受限）。
  不要绕过：不要把正式项目挪出 `videos/` 去跑，也不要改闸门代码（`toolkit/vlab/tools/script_gate.py`）。
- 想先看画面效果，在 `research/` 下做样片，不用正式剧本的文字冒充定稿。

## 内容路线（按路线走）

每条视频都必须属于一条已定的路线，路线定义在 `process/ROUTES.md`（2026-10-26 项目负责人定）。
现在有两条：**主线**（硬知识 + 人生落点，和比特新语正面比）、**科学史**（人类是怎么知道的）。
另有 8 条候选路线：7 条在提案阶段（模拟实验室、尺度与量级、科技原理、「为什么」身边的科学、数学之美、节气与天象、前沿解读），
「火柴人 VS 物理」2026-10-27 定了试水（下一条视频）。提案在 `research/content/route-*.md`，名单和状态见 `process/ROUTES.md` 第 4 节末尾；**没拍板试水之前，不能按它们开做**。

- 选题只从已定路线里出；路线外的题材，先按 `process/ROUTES.md` 第 4 节写提案、试水、复盘，由项目负责人拍板。
- AI 不能自行开新路线，也不能把路线外的题材塞进现有路线；可以往候选题里补充，写明理由。

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
| 字体 Microsoft YaHei、Cascadia Mono | 系统字体；Cascadia：`winget install Microsoft.CascadiaCode` | 只在重渲 001–003 和早期试验时；新片子用仓库自带的思源黑体（`vlab.fonts`），不用装 |
| 支持 OpenGL 3.3 的显卡 | 硬件 | 只在重渲染着色器镜头时（003 的 hook/noon/sunset、research/visual/07） |
| 联网 | — | 只在重新配音时（Edge TTS 是在线服务） |
| 各片成片 | 用各片子的总装命令从入库的输入重新拼出（命令见 README「重新生成成片」） | 想看成片时 |
| `toolkit/vlab/render/remotion/node_modules/` | 在该目录 `npm.cmd install` | 只在重渲 remotion 镜头时（007 在用） |

## 目录和依赖方向

根目录 6 个文件夹各是一类：

```
videos/      【项目结果】正在做的正式视频（现在是 009；007、008 暂停），一条一个目录；受剧本闸门约束
research/    【开发测试】visual/ 画面技术（01–12）、audio/ 音频研究、frontier/ 前沿视频生成、content/ 创作内容研究（内容方向、平台、合规）；实验目录都是 NN-主题/
toolkit/     【工具】vlab/ 公共代码包（pipeline 配音合成、audio 音效配乐混音、fonts 项目字体、render 渲染器、scenes 可复用画面、videokit 视频工程、tools 工具）；bin/ 本机可选的程序
process/     【流程】我们的流程和流程规则：内容路线、剧本审核、传播与节奏规范、发布清单、入库与提交（必须遵守，只由项目负责人改）
docs/        【文档】参考资料：TECHNOLOGY.md、VIDEO-TYPES.md、TODO.md、design/
archive/     【存档】000 参考项目的只读快照（不要改，它自带的 shared/ 和环境配置只属于它自己）；
             001–006 是开发过程中的探索作品，2026-10-26 归档，不再是主力视频
```

- **新东西放哪**：做成片 → `videos/`；做试验、调研 → `research/` 下对应的区；会被多个项目复用的代码 → `toolkit/vlab/`；说明文档 → `docs/`。
- **`videos/` 和 `research/` 只依赖 `toolkit/vlab/`，彼此不互相引用；`research/` 下各区之间也不互相引用。**
  想在正式视频里用试验出来的东西，先把它提升进 `toolkit/vlab/`（比如 `toolkit/vlab/scenes/landscape.py` 就是从 research/visual/06 提升上来的），再从两边引用。
- **公共代码只有一份**：不要把 `toolkit/vlab/` 里的文件复制到项目里。Python 里照常 `import vlab`。
- **密钥和模型权重不入库**：API Key 只放本地 `.env`（可以入库不含真实值的 `.env.example`）；模型权重放在 `weights/` 目录或系统缓存里，`.gitignore` 已忽略，在实验 README 里写清下载方式。
- 项目内部按技术分子目录：`manim/`、`shader/`、`hyperframes/`、`landscape/`；`content/` 稿子、`build/` 配音时间轴字幕、`renders/` 成片。
- **镜头卡是公共资产**：`toolkit/vlab/render/remotion/src/cards/` 里的 15 张卡（粒子聚字、科技卡、鸟群、生命游戏、量级卡…）跨片子复用，项目里只在 `project.yaml` 写「用哪张卡 + 传什么参数」，不要在项目里复制一份（复制就会漂移）。项目里的 `remotion/` 只放 README 说明。

## 仓库里的成果：输入都在，只有正在做的片子带成片

重生成成片需要的配音和配乐 wav、时间轴、字幕、分镜片段都在仓库里。`videos/` 下正在做的片子，成片也入库；`archive/` 和 `research/` 的成片不入库，有 ffmpeg 就能用各自的总装命令重新拼出来，结果和原成片一致（命令见 README「重新生成成片」，规则见 `process/REPO.md`）。

- **不要随手重跑配音**（`vlab-tts`）。Edge TTS 每次生成的语速和词时间点可能不同，
  `build/<id>/timeline.json` 一变，整条视频的画面就要全部重渲染才能对齐。只有旁白文字改了才重跑。
- **003 的着色器片段要显卡才能重渲染**，平时直接用 `archive/003-sunset-red/media/clips/` 里的现成片段，
  `uv run python build.py` 会跳过已有片段、只做拼接。
- **视频工程（videokit）有缓存**：`media/clips/<风格>/*.hash` 是镜头指纹，指纹没变就复用，不要删。
  指纹按渲染器算：`manim` 算模板文件、`glsl` 算 frag、`remotion` 算整个 `src/**/*.ts*`（改任何一张卡，用卡的镜头都会重渲）。
- **镜头按渲染器分派**：`renderer: manim|remotion|glsl|custom`。glsl 共用一个 OpenGL 上下文必须串行；remotion 在 Windows 上默认并发封顶 4（`cpu//2` 会开到十几个，偶发 node/chrome 卡死），超时重试自动降到 2。
  `custom` 是逃生口：项目内写一个 `.py`，`vlab-build` 以 `python <script> --scene <临时json>` 调它，
  JSON 里有 `out`/`frames`/`fps`/`params`/`words`，脚本必须写出 `out`（例子见 `research/visual/14-custom-renderer/`）。
  帧数统一由 `timeline` 算：`round(end*fps) - round(start*fps)`，渲染器和帧数校验用同一套算法（以前各算各的会让帧差 1，最终和配音错位）。

## 常用命令（任意目录可用）

| 要做的事 | 命令 |
|---|---|
| 配音 | `uv run vlab-tts <项目>/content/<稿子>.json` |
| 合配音、烧字幕 | `uv run vlab-finalize <无声画面.mp4> <项目>/build/<id> <输出.mp4>` |
| 看渲染结果 | `uv run vlab-preview <视频> --timeline <timeline.json>` → 每个分镜的结尾画面拼成一张图 |
| 视频工程构建 | `uv run vlab-build research/visual/08-video-spec/project.yaml [--style ...] [--check] [--force]` |
| 节奏/逐帧/响度体检 | `uv run vlab-review <项目>/project.yaml [--loudness]`（硬指标见 `process/STYLE-RHYTHM.md`） |
| 几条片子 A/B | `uv run vlab-ab <成片1> <成片2> <成片3> --out <输出.png>`（每条一行，同列是同一叙事位置） |
| 看有哪些镜头卡 | `uv run python -m vlab.render.remotion_bridge --list` |
| 看每张卡长什么样 | `uv run vlab-cards --out <输出.png>`（每张卡渲 3.2s 抽一帧拼图） |
| 单独渲染一张卡 | `uv run python -m vlab.render.remotion_bridge <卡名> <输出.mp4> --seconds 4 --params '{"title":"…"}'` |
| 分析参考视频的风格 | `uv run vlab-style <视频> <输出目录>` |
| 环境自检 | `uv run vlab-check` |
| 003 重新拼成片 | `cd archive/003-sunset-red; uv run python build.py`（`--force` 全部重渲染） |
| 001 / 002 重渲染 | `cd videos/00x-...; uv run python -m manim render manim/scene.py <场景类> --format mp4`，再 `uv run vlab-finalize ...`（见 README） |
| 低清快速预览 | 先设 `$env:PREVIEW='1'`（竖屏 540×960、横屏 960×540，15fps） |

## 工作约定

- **渲染 → 看图 → 改**：改画面后一定用 `vlab-preview` 抽帧看图确认，不要只看代码就说"改好了"。
  看图时要逐项核对内容和标签是否对应（色块的颜色像不像它的名字、数字是不是脚本里的值），不只看版式；
  004 的光谱型色块 O 和 B 颜色相同、"黄"显白，版式看着没问题，是逐块对照标签才发现的。有数值的地方打印出来核对。
- **画面跟着配音走**：画面元素绑定到配音里的"词"（`timeline.json` 的 words），不要写死秒数。
- **声音按规范混**：有配乐或音效的成片用 `vlab.audio.mix.mux` 混音（说话时配乐自动压低，成片 -14 LUFS），不要另写 ffmpeg 混音参数；音效由画面的事件清单触发（`vlab.audio.sfx.render`，例子见 research/visual/12）。
- **发布前过发布清单**（`process/PUBLISH.md`，依据在 `research/content/08-compliance/README.md`）：用了 TTS 配音，发布时在平台勾选 AI 声明、必选标签选「含有AI生成内容」（视频画面内不加文字声明，项目负责人定）；配乐和音效要么自己合成，要么用授权明确覆盖多平台商用的曲库。配乐以后用曲库、剪辑时加（项目负责人定，2026-10-27）；抖音、剪映自带的曲库只限站内非商业。
- **字体统一用 `vlab.fonts`**（思源黑体，随仓库入库，SIL OFL 1.1 可商用）：Manim 用 `fonts.register_manim()` 返回的族名，Pillow 用 `fonts.pil(字号, bold)`，不要再写 `C:/Windows/Fonts/...` 的路径。微软雅黑不能用于商业发布。
- **传播优先，但不牺牲质量**：项目的目标是做出比对标账号（比特新语，见 `process/STYLE-IMPACT.md`）更受欢迎的知识短片。
  写稿、定稿、出片都按 `process/STYLE-IMPACT.md` 的五条硬规矩过：情绪落点、人声优先、光影优先、情绪句标题、130–170 秒密度。
  传播决定"讲什么、讲多少、怎么讲"；**事实准确、画面质量、剧本质量是底线，不为传播让步**（项目负责人定，2026-10-26）。
  可以为传播删减和简化，不能说错，简化的地方在画面上标注；不允许"标题先说过头、片尾再更正"。
- **新视频优先用视频工程**（`toolkit/vlab/videokit`，设计见 `docs/design/DESIGN-video-project.md`）：
  文案、数据、颜色、出场时机写在 `project.yaml` 里，常规镜头走模板；只有特殊镜头才写定制代码。
- **片长 2–6 分钟（120–360 秒），时长服从内容**：不做固定 3 分钟，也不为凑时长注水。
  区间内**观感是第一优先级**：`vlab-review` 的硬指标为观感服务，两者冲突时以观感为准，
  并在项目 `SCRIPT.md` 里写明破了哪一条、为什么。镜头数随片长走（≥ max(13, ⌈片长/5.2⌉)）。
  口径见 `process/STYLE-RHYTHM.md`「片长与优先级」。
- **切点不许发亮**：remotion 工程保持 `fx_default: {flash: false}`，章节标点用压暗（`dipIn`/`dipOut`），
  亮场切暗场给亮镜末尾加 `dipOut`。细则和验收脚本见 `process/STYLE-RHYTHM.md`「特效栈的边界」。
- **入库原则**（`process/REPO.md`）：重生成成片需要的输入（配音和配乐 wav、时间轴、字幕、分镜片段）全部入库；成片只有 `videos/` 下正在做的片子入库，`archive/` 和 `research/` 的不入库；「其他AI推进」这类合并来源目录、环境和缓存碎片不入库。新增产物类型时先看 `process/REPO.md` 和 `.gitignore`。
- **没有用户明确说"提交"/"推送"，不要 `git commit` / `git push`**。改完列出改动文件，等用户指令。

## 已知坑

- **仓库路径含中文括号【】**：Python 3.11 在中文 Windows 上按 GBK 读 `.pth`（开 UTF-8 模式也一样），
  可编辑安装写进 `.pth` 的仓库路径会被读坏。已在 `pyproject.toml` 里另装一个纯 ASCII 的 `_vlab_root.pth` 解决；
  如果 `import vlab` 失败，先 `uv sync --reinstall-package video-lab`。
- `uv run` 提示 `VIRTUAL_ENV ... does not match`：本机激活了别的虚拟环境，无害，uv 仍用仓库的 `.venv`。
- Manim：要 `config.disable_caching = True`（缓存会让时间轴错位）；分辨率用 `PREVIEW` 环境变量切换，`-ql` 会被脚本里的设置覆盖；
  对齐时间要按"当前真实帧数"补齐，冻结帧和逐帧两种等待的取整方式不同（见各 scene.py 的 `wait_to`）。
- Edge TTS 的分词和直觉不同（如"四次方"切成 四/次/方，"一颗"切成 一/颗）：绑定的词必须是 `timeline.json` 里的词；
  videokit 配音后会校验并列出可用的词。写画面脚本前先把整段词表打出来看一遍，比逐个试错快。
- **先配音后画面，成片长度由旁白字数定**，不是由分镜表上的"画面时长"定。
  中文配音约 0.236 秒/字（含停顿，实测 003），按这个估，写稿时就能把时长控制住；
  靠拉长镜头留白来凑时长会让片子显得拖。
- YAML 1.1 会把 `on`/`yes`/`no` 当布尔值：工程文件一律用 `vlab.videokit.project.load_yaml` 读，别用 `yaml.safe_load`。
- Windows 显卡超时（约 2 秒）会重置驱动：重着色器要分块渲染（`toolkit/vlab/render/glsl.py` 已处理）。
- **一个进程里用两个着色器会串画面**：各自建独立 OpenGL 上下文、在同一线程交错渲染时，
  一个着色器会画到另一个的缓冲上，现象是某几镜整屏变成另一个着色器的画面。
  `glsl.py` 已改成全进程共用一个上下文（`_ctx()`），不要再自己 `create_standalone_context`。
- 这台机器的 ffmpeg `drawtext` 没有字体配置会崩：画面上叠字用 Pillow，不用 drawtext。
- **烧字幕不给字体目录，libass 会悄悄换字体**：实测找不到思源黑体时先退到 Arial、再退到微软雅黑，画面看着正常、字体却错了。`vlab-finalize` 已传仓库字体目录（`fontsdir`），自己写 ffmpeg 字幕滤镜时也要带上。
- PowerShell 执行策略：npm 要写成 `npm.cmd`；`npx` 同理（桥里已写成 `npx.cmd`，并通过 `COMSPEC /c` 调用）。
- **Remotion 授权**：项目单人使用，适用 Remotion 的免费授权（项目负责人确认，2026-10-26），不用再提。
- **Remotion 的 `node_modules/` 不入库**：`cd toolkit/vlab/render/remotion; npm.cmd install` 一次即可；
  它只是渲染器，不进 Python 依赖，`uv sync` 不会装它。重渲 remotion 镜头前先确认这个目录存在。
- **IDE 会报“找不到模块 remotion”**：类型服务索引陈旧，不是真错。用 `npm.cmd exec tsc --noEmit` 验证，
  0 报错就不用改代码。
- **Remotion 里禁止 `Math.random`**：渲染要可重现，随机一律用 `src/common/random.ts` 的种子随机（`rng`），
  否则同一镜重渲两次画面不一样，也会让帧检看起来像坏了。
- **镜头卡只能靠 props 变，不能靠时长短**：一张卡在 3.5s 和 5s 都要能看（进度都用 0–1 归一），
  否则改一句旁白就会把某个动效切成半截。
- `.gitignore` 不支持行尾注释，注释必须单独一行。
