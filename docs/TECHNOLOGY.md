# AI-Vedio 技术路线标准

**效果优先，技术为内容服务。** 不局限于单一方案，可根据内容类型混合使用。

---

## 一、技术方案全景

本节是"已验证 + 未来方向"的总表，按类别分组。字段说明：

- **门槛**：上手难度，以及能否用 vibe coding（说需求 → AI 写代码 → 看结果再改）完成：
  - ★★★ 完全可以：纯代码，命令行就能渲染，AI 能全程自己跑
  - ★★ 基本可以：有脚本接口能后台渲染，但素材或细调需要人参与
  - ★ 部分可以：主要靠图形界面操作，AI 只能写辅助脚本
- **关键经验**：AI 写画面能成功，靠的是"渲染 → 抽帧给 AI 看 → 改"的循环（001/002 的排版问题、风景里鹿腿重影都是看图才发现的）。
  所以**能用命令行快速出一帧图片**的技术，最适合我们的做法。
- 本机现状以 2026-10-20 为准；"已验证"指在本仓库或原开发机上跑通过。

### A. 排版与图示类（科普讲解的主力）


| 技术                | 惊艳/擅长                                          | 典型效果                               | 门槛（含 AI 可写程度）         | 需要环境配置                                                   | 备注                                                                                         |
| ------------------- | -------------------------------------------------- | -------------------------------------- | ------------------------------ | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Manim**           | 几何、数学、物理的连续变形；支持 3D 参数曲面       | 公式推导、图形变形、莫比乌斯环翻面粘合 | 中偏高 · ★★★               | 根目录 uv 环境已含 manim 0.22.0；不用 LaTeX（数字用 Text）     | **已验证**：001、002、research/visual/09-manim-showcase。静态排版弱；2D 约 1× 实时，3D 慢（002 低清约 3 分钟） |
| **HyperFrames**     | 浏览器能画的都能用：排版、渐变、遮罩、字幕逐词高亮 | 数据卡、标题动效、图文混排             | 中 · ★★★（自带 lint 检查） | Node +`npm i hyperframes@0.8.174`；首次渲染下载约 270MB Chrome | **已验证**：000、001 HTML 版。onUpdate 不触发，数字滚动做不了；1.5–2× 实时                 |
| **Pillow 图文卡片** | 模板化量产，换稿子就出片                           | 资讯卡、语录卡                         | 低 · ★★★                   | 已在环境                                                       | **已验证**：000/1_cards。动画弱，像 PPT                                                      |
| **Python 文字动效**（Pillow + numpy） | 每个字单独运动：弹出回弹、数字滚动、沿圆弧排字、遮罩揭示、故障撕裂；每个动作卡在配音的词上 | 金句、歌词、数字冲击开场、标题转场 | 中 · ★★★（`--still` 秒出单帧自检） | 已在环境 | **已验证**：research/visual/12-kinetic-type《光有多快》20 秒，配 71 个自动音效。HyperFrames 做不了的数字滚动这里能做 |
| **Remotion**        | React 组件生态，企业级模板化                       | 产品发布、品牌模板视频                 | 中 · ★★★                   | Node + npm                                                     | **已验证**：research/visual/13、005–007 的镜头卡库。3 人以上公司需买授权；本项目单人使用，适用免费授权（项目负责人确认，2026-10-26）                                                             |

### B. 程序化与生成艺术类（风景、氛围、空镜）


| 技术                                             | 惊艳/擅长                                            | 典型效果                                           | 门槛（含 AI 可写程度）                        | 需要环境配置                                                                     | 备注                                                                                          |
| ------------------------------------------------ | ---------------------------------------------------- | -------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Python 程序化 2.5D**（numpy + Pillow）         | 分层插画风景、透视水面倒影、逆光剪影动物             | 日落湖景：山、水、鹿、雁群、跃鱼                   | 中高 · ★★★（`--still` 几秒出单帧自检）    | 已在环境                                                                         | **已验证**：research/visual/06-landscape，12 秒竖屏约 4.5 分钟。上限是插画/剪影风格，写实动物做不了 |
| **像素风人物故事**（numpy + Pillow） | 角色前后一致、动作帧可控、整片同一套色板；比 AI 生成的像素图稳定得多 | 像素小人走路/抬头/举起/挥手、猫跳、流星、RPG 对话框逐字打字 | 中 · ★★★（字符网格画精灵，`--still` / `--sheet` 秒出图自检） | 已在环境；对白用系统自带宋体 12/16px 点阵字 | **已验证**：research/visual/11-pixel-story《掉落的星星》30 秒，含配音、代码合成的芯片音乐和音效 |
| **着色器光线步进**（GLSL，Shadertoy 一类）       | 几百行代码在 GPU 上逐像素算真实光照，惊艳/成本比最高 | 无限海洋、体积云、云海飞越雪山、外星地形、分形宇宙 | 中高（要懂图形数学）· ★★★ 单文件          | 已用 Python `moderngl` 离屏渲染（根环境已装），共享模块 `toolkit/vlab/render/glsl.py`；也可走浏览器 WebGL | **已验证**：research/visual/07 云海飞越雪山（GTX 1060，2×2 超采样约 0.65 秒/帧）；003 大气散射天空。参考 Shadertoy 和 Inigo Quilez 的文章                                   |
| **Three.js / WebGL + 后期**                      | 网页 3D + 辉光、景深                                 | 粒子星系、数据地球、3D 文字、科技感片头            | 中 · ★★★                                  | Node + three；渲染可复用 HyperFrames 的逐帧截图                                  | **待验证**                                                                                    |
| **生成艺术**（Python + OpenCV，Processing 风格） | 分形、粒子、流场、利萨如曲线                         | 分形树、粒子引力、流场线条                         | 中 · ★★★                                  | 需`opencv-python`（根环境未装）                                                  | **已验证**：research/visual/05（原开发机）。脚本里写死了原机 ffmpeg 路径，换机要改                  |
| **p5.js**                                        | 生成艺术、跟着音乐动                                 | 音乐可视化、抽象动态海报                           | 低中 · ★★★                                | 浏览器即可                                                                       | **待验证**                                                                                    |
| **TouchDesigner**                                | 实时节点式视觉、音频响应                             | 演出级音乐可视化、粒子装置                         | 中高 · ★（主要靠节点界面，Python 只能辅助） | 需安装；非商用免费版分辨率上限 1280×1280                                        | **待验证**                                                                                    |
| **分形渲染器**（如 Mandelbulber）                | 无限放大的三维分形                                   | 曼德尔球穿梭、分形城市                             | 低（调参数）· ★★（参数文件 + 命令行渲染）  | 需安装                                                                           | **待验证**                                                                                    |

### C. 3D 与写实渲染类（写实风景、动物、产品）


| 技术                                  | 惊艳/擅长                                | 典型效果                                       | 门槛（含 AI 可写程度）                                                   | 需要环境配置                                                                           | 备注                                                                                          |
| ------------------------------------- | ---------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Blender**（Cycles/Eevee、几何节点） | 物理正确的光线追踪，接近照片；程序化地形 | 写实山川湖泊、带动画的动物、产品广告、相机运镜 | 中 · ★★（`bpy` 全脚本 + `blender --background` 后台渲染；素材要下载） | 需安装（约 300MB）；免费素材：Poly Haven（HDRI/材质/模型）、Quaternius（带动画的动物） | **基础已验证**：research/visual/04（原开发机，本机未装）。Cycles 慢，一帧几十秒起。**写实路线首选** |
| **Unreal Engine 5**                   | 实时电影级画质，海量现成素材             | 写实森林、雪山、城市航拍                       | 高 · ★（有 Python 编辑器脚本，主要还是在编辑器里调）                   | 需好显卡、上百 GB 空间                                                                 | **待验证**，视硬件决定                                                                        |
| **Houdini**                           | 影视特效行业标准，全程序化               | 爆炸、破碎、海浪、大规模模拟                   | 高 · ★（Python/VEX 能写，调试靠界面）                                  | 需安装；免费学习版有水印和分辨率限制                                                   | **待验证**                                                                                    |
| **高斯泼溅三维重建**                  | 用手机拍一圈照片重建真实场景，再自由运镜 | 真实景点的无人机式穿梭                         | 中 · ★（重建可脚本化，但素材要人实地拍）                               | 需 NVIDIA 显卡                                                                         | **待验证**。属于逐场景训练的重建，不是生成模型                                                |
| **After Effects**                     | 专业动效，上限最高                       | 商业级片头、复杂合成                           | 高 · ★（脚本能力有限，主要人工）                                       | 付费软件                                                                               | 不作为主路线                                                                                  |

### D. 物理模拟类（高光镜头）


| 技术                             | 惊艳/擅长            | 典型效果                       | 门槛（含 AI 可写程度） | 需要环境配置                            | 备注                                             |
| -------------------------------- | -------------------- | ------------------------------ | ---------------------- | --------------------------------------- | ------------------------------------------------ |
| **Taichi**（Python 的 GPU 计算） | 百万粒子级的真实物理 | 沙子流动、雪崩、水花飞溅、烟雾 | 中 · ★★★           | `uv add taichi`；有显卡更快，CPU 也能跑 | **待验证**。适合做几秒的高光镜头，混剪进别的视频 |

### E. 后期与音频类（所有视频共用）


| 技术         | 惊艳/擅长                                | 典型效果             | 门槛（含 AI 可写程度） | 需要环境配置                                    | 备注                                                        |
| ------------ | ---------------------------------------- | -------------------- | ---------------------- | ----------------------------------------------- | ----------------------------------------------------------- |
| **FFmpeg**   | 合成、转场、滤镜特效、烧字幕、响度标准化 | 20 种转场、15 种特效 | 低 · ★★★           | 本机在 PATH 上（8.1.1）；原开发机在`toolkit/bin/` | **已验证**：所有项目、research/visual/01、02                      |
| **OpenCV**   | 图像处理、边缘检测、风格化               | 卡通化、描边、特征点 | 中 · ★★★           | 需`opencv-python`（根环境未装）                 | **已验证**：research/visual/03（原开发机）                        |
| **Edge TTS** | 免费配音 + 词级时间轴，画面按词对齐      | 所有项目的旁白和字幕 | 低 · ★★★           | 已在环境（7.3.1），需联网                       | **已验证**：所有项目。生成结果可能随时间变，`build/` 要入库 |
| **代码合成音效**（numpy，`vlab.audio.sfx`） | 12 种电子感音效，零素材、无版权问题；画面事件清单直接生成音效轨，和画面严丝合缝 | 字弹出、转场呼啸、数字咔嗒、亮点铃音 | 低 · ★★★ | 已在环境 | **已验证**：research/audio/09、research/visual/12。写实声音（脚步、水、风）要靠 CC0 音效库 |
| **自动避让混音**（ffmpeg，`vlab.audio.mix`） | 说话时配乐稳定压低 8 dB、停顿时回来；两遍响度标准化到立体声 -14 LUFS | 所有带配乐的成片 | 低 · ★★★ | 已在环境 | **已验证**：research/audio/02，用电平曲线实测 |
| **程序化配乐**（numpy，`vlab.audio.music`） | 按时长和速度生成背景音乐，自己合成、无版权问题 | 和弦铺底 + 琶音 + 轻鼓；芯片音乐 | 中 · ★★★ | 已在环境 | **部分验证**：目前只有两种风格，扩展见 research/audio/03 |

### F. 对照：AI 像素级生成（当前路线排除）


| 技术                                 | 惊艳/擅长                | 典型效果           | 门槛（含 AI 可写程度）   | 需要环境配置       | 备注                                 |
| ------------------------------------ | ------------------------ | ------------------ | ------------------------ | ------------------ | ------------------------------------ |
| **像素级生成**（Seedance/可灵/Sora） | 真人、实拍质感、复杂光影 | 真人出镜、实景短片 | 低 · 不写代码，靠提示词 | 在线服务，按秒计费 | 不可控、要抽卡、贵；只在真人场景考虑 |

### 内容类型 → 技术选择


| 内容类型                     | 首选                   | 备选            | 混合策略                                  |
| ---------------------------- | ---------------------- | --------------- | ----------------------------------------- |
| 数学科普（公式/几何/变形）   | **Manim**              | HyperFrames     | Manim 做几何 + HyperFrames 做文字         |
| 数据可视化（图表/数字）      | **HyperFrames**        | Manim           | HyperFrames 做图表 + Manim 做动画         |
| 产品发布（版式/文字）        | **HyperFrames**        | Remotion        | -                                         |
| 模板化量产（资讯/语录）      | **Pillow**             | HyperFrames     | -                                         |
| 风景、自然氛围（插画风）     | **Python 程序化 2.5D** | 着色器光线步进  | 程序化画面 + Edge TTS 旁白                |
| 人物小故事、童话、怀旧游戏感 | **像素风** | Manim | 精灵动画 + RPG 对话框 + 芯片音乐 |
| 金句、歌词、数字冲击 | **Python 文字动效** | HyperFrames | 逐词动效 + 事件音效 + 自动避让配乐 |
| 风景、动物（写实）           | **Blender**            | Unreal Engine 5 | Blender 出空镜 + Manim/HyperFrames 叠文字 |
| 震撼开场、空镜、转场         | **着色器光线步进**     | Three.js        | 几秒高光镜头 + FFmpeg 转场接正片          |
| 物理现象科普（流体、沙、雪） | **Taichi**             | Blender 模拟    | 模拟片段 + Manim 标注讲解                 |
| 音乐可视化                   | **p5.js**              | TouchDesigner   | -                                         |
| 真人/实拍                    | **像素级生成**         | After Effects   | -                                         |

---

## 二、标准工作流

### 流程概览

```
选题 → 写剧本 (SCRIPT.md + content/xxx.json)
       ↓
     项目负责人逐条审核、讨论打磨，明确确认（剧本闸门，process/SCRIPT-REVIEW.md）
       ↓
     配音 (uv run vlab-tts)
       ↓
     生成 narration.wav + timeline.json + subs.ass/srt
       ↓
     渲染画面 (manim/scene.py 或 hyperframes/index.html)
       ↓
     合成 (uv run vlab-finalize；有配乐、音效时用 vlab.audio.mix)
       ↓
     成片 (renders/xxx_final.mp4)
```

### 1. 剧本格式

```json
{
  "id": "项目 ID",
  "title": "视频标题",
  "voice": "zh-CN-YunxiNeural",
  "rate": "+8%",
  "scenes": [
    {
      "id": "分镜 ID",
      "narration": "旁白文案",
      "headline": "画面标题"
    }
  ]
}
```

### 2. 配音链路（toolkit/vlab/pipeline/tts.py，命令 `vlab-tts`，所有视频共用）

**输入**：`content/xxx.json`**输出**：

- `build/xxx/narration.wav`（-16 LUFS 标准化）
- `build/xxx/timeline.json`（词级时间点，WordBoundary）
- `build/xxx/subs.ass` / `subs.srt`（智能断行字幕）

**关键参数**：

- `LEAD = 0.25s`（画面切入后停顿再开口）
- `TRAIL = 0.35s`（说完后停顿再切下一镜）
- `END_HOLD = 1.6s`（片尾多停）
- `MAX_LINE = 13`（字幕每行最多字数）

### 3. 渲染画面

**Manim**：

```powershell
uv run python -m manim render manim/scene.py SceneName --format mp4
```

**看图**（每个分镜最终画面拼成一张图）：

```powershell
uv run vlab-preview media/videos/scene/1920p30/SceneName.mp4 --timeline build/xxx/timeline.json
```

**HyperFrames**：

```powershell
npm run render
```

### 4. 合成（toolkit/vlab/pipeline/finalize.py，命令 `vlab-finalize`）

**输入**：无声画面.mp4 + build/xxx/
**输出**：`renders/xxx_final.mp4`

**处理**：

- 烧字幕（subs.ass）
- 合配音（narration.wav）
- 单声道→立体声（pan 滤镜）
- 响度标准化（-16 LUFS）

**有配乐、音效时**：改用 `vlab.audio.mix.mux(无声画面, narration.wav, 输出, music=..., sfx=...)`。
配乐在说话时自动压低 8 dB，成片两遍标准化到立体声 -14 LUFS、真峰值 -1.5 dBTP（规范和实测见 `research/audio/02-mix-ducking`）。
`mux` 不烧字幕、画面原样复制，需要字幕就先画进画面。

---

## 三、项目结构规范

### 仓库顶层（按类别分区）

```
videos/        【项目结果】正式视频
research/      【开发测试】visual/ 画面技术、audio/ 音频、frontier/ 前沿视频生成、content/ 创作内容
toolkit/       【工具】vlab/ 公共代码包（uv sync 后 vlab-* 命令在任意目录可用）；bin/ 本机可选的 ffmpeg 等程序
docs/          【文档】TECHNOLOGY.md、VIDEO-TYPES.md、TODO.md、design/
process/       【流程】内容路线、剧本审核、传播与节奏规范、发布清单、入库与提交（必须遵守）
archive/       【存档】000 参考项目的只读快照；001–006 归档的探索作品
```

依赖方向：`videos/`、`research/` 只依赖 `toolkit/vlab/`，彼此不互相引用；可复用的东西先提升进 `toolkit/vlab/` 再用。

### 正式视频项目（videos/三位编号-英文 slug/）

```
content/           # 剧本稿子 (json)；用视频工程时是 project.yaml
manim/             # Manim 动画 (scene.py)
shader/            # 着色器片段的渲染脚本（着色器本身放 toolkit/vlab/scenes/shaders/）- 可选
hyperframes/       # HyperFrames 动画 (index.html、package.json、vendor/) - 可选
build/             # 配音产物 (narration.wav, timeline.json, subs.ass)，入库
media/clips/       # 多技术混剪时的分镜片段，入库（拼接成片不用重渲染）
renders/           # 成片 (mp4)，入库
build.py           # 多技术混剪时的总装脚本 - 可选
```

### 公共代码（toolkit/vlab/）

```
toolkit/vlab/pipeline/     tts.py 配音、finalize.py 合成
toolkit/vlab/render/       glsl.py 着色器 → 视频片段（分块渲染防显卡超时）
toolkit/vlab/scenes/       landscape.py 程序化湖景；shaders/ 云海、大气散射
toolkit/vlab/videokit/     视频工程：project.py、build.py、manim_templates.py、style_extract.py
toolkit/vlab/tools/        preview.py 抽帧拼图、check_env.py 环境自检
toolkit/vlab/audio/        sfx.py 合成音效、music.py 程序化配乐、mix.py 混音规范（自动避让 + 响度）
toolkit/vlab/fonts.py      项目字体：思源黑体（OFL 可商用），文件在 vlab/assets/fonts/，随仓库入库
```

---

## 四、关键技术细节

### Manim

**版本**：0.22.0
**安装**：`python -m pip install manim -i https://mirrors.aliyun.com/pypi/simple/`

**踩坑记录**：

1. RGBA 颜色不支持 → 用十六进制 + opacity
2. VGroup 只能包含 VMobject → 用 Group 代替
3. 3D 曲面用 `Surface` 而非 `ParametricSurface`
4. `disable_caching = True`（避免缓存导致时间轴错位）

### HyperFrames

**版本**：0.8.174
**安装**：`npm i hyperframes@0.8.174`

**踩坑记录**：

1. PowerShell 执行策略 → 必须用 `npm.cmd`
2. GSAP 不走 CDN → 本地化到 `vendor/`
3. 字体映射 → 加 `@font-face { src: local(...) }`
4. 对比度 → 深色背景文字不透明度 ≥ 0.55
5. **onUpdate 回调不触发** → 只能用纯属性补间，数字滚动做不了

### 画幅：竖屏和横屏

稿子里写 `"aspect": "landscape"` 出横屏 1920×1080，不写就是竖屏 1080×1920（`vlab.pipeline.tts.ASPECTS`）。
字幕字号、左右边距、每行字数都跟着画幅走（竖屏每行 13 字，横屏 22 字）。
Manim 场景要自己设 `config.frame_width, config.frame_height = 16, 9` 和对应的像素尺寸。
平台取向见 `research/content/03-platforms/`：B站等平台都在扶持横屏中长视频。

### Edge TTS

**版本**：7.3.1
**安装**：`python -m pip install edge-tts`

**关键**：

- 用 `boundary="WordBoundary"` 获取真实词级时间点
- 响度标准化到 -16 LUFS（短视频平台标准）
- 单声道配音复制成左右声道（pan 滤镜，不用 -ac 2）

### FFmpeg

**版本**：7.1
**位置**：`toolkit/bin/ffmpeg.exe`

**常用命令**：

```powershell
# 响度标准化
ffmpeg -i input.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" output.wav

# 烧字幕
ffmpeg -i video.mp4 -vf "subtitles=subs.ass" output.mp4

# 单声道→立体声
ffmpeg -i input.wav -af "pan=stereo|c0=c0|c1=c0" output.wav
```

---

## 五、命名约定


| 类型     | 格式                   | 示例                   |
| -------- | ---------------------- | ---------------------- |
| 正式视频 | `videos/三位编号-英文 slug` | `videos/007-regression`  |
| 归档视频 | `archive/三位编号-英文 slug` | `archive/004-green-star`  |
| 存档     | `archive/000-claude-xxx`    | `archive/000-claude-video-lab` |
| 技术测试 | `research/visual/两位编号-英文用途`     | `research/visual/07-shader-raymarch`      |
| 音频研究 | `research/audio/两位编号-英文用途`   | `research/audio/02-mix-ducking`            |
| 前沿研究 | `research/frontier/两位编号-英文用途` | `research/frontier/02-code-controlled` |
| 内容研究 | `research/content/两位编号-英文用途` | `research/content/01-directions` |
| 公共代码 | `toolkit/vlab/<职责>/`              | `toolkit/vlab/scenes/landscape.py`    |

---

## 六、未来方向（建议测试顺序）

排序依据：惊艳程度、能否 vibe coding、本机能否直接开始。详细字段见第一节总表。


| 顺序 | 方向                          | 理由                                          | 前置条件                              |
| ---- | ----------------------------- | --------------------------------------------- | ------------------------------------- |
| 1    | **着色器光线步进** ✅ 已完成  | 惊艳/成本比最高，单文件、零素材，最适合 AI 写 | 已完成：research/visual/07、003 大气散射    |
| 2    | **Blender 写实风景 + 动物**   | 写实路线唯一现实的选择，脚本可全程后台跑      | 安装 Blender，下载免费动物模型和 HDRI |
| 3    | **Taichi 物理模拟**           | 几秒高光镜头，混剪价值高                      | `uv add taichi`                       |
| 4    | **Three.js + 后期**           | 科技感片头、粒子、3D 文字                     | `npm i three`                         |
| 5    | **Remotion**                  | 模板化品牌视频，和 HyperFrames 二选一         | Node；注意授权条款                    |
| 6    | **Unreal Engine 5 / Houdini** | 上限最高，但 AI 只能辅助，硬件门槛高          | 好显卡、大硬盘，视需求再定            |
| -    | 像素级生成（Seedance/可灵）   | 真人场景才用                                  | 在线服务，按秒付费                    |
