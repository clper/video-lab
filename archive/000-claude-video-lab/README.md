# video-lab：不用 AI 视频模型做视频

同一个题目「蜂巢为什么是六边形」（约 50 秒竖屏科普），用三种做法各做一版。
画面全部由代码画出来，不调用任何 AI 视频生成模型（Sora / Veo / 可灵 / Wan 之类）。
稿子是 AI 写的（这次直接由 Claude 写），配音用免费的 Edge TTS。

打开 [compare.html](compare.html) 可以三版并排同步播放。

## 流程

```
稿子 content/hexagon.json
  │
  ▼  shared/tts.py   每个分镜单独配音 → 整条配音 + 每个词的时间点 + 字幕
build/hexagon/  narration.wav · timeline.json · subs.ass
  │
  ├─► ① 1_cards/        Pillow 画静态卡片，FFmpeg 叠化拼接
  ├─► ② 2_hyperframes/  HTML + GSAP 写动画，Chrome 逐帧渲染
  └─► ③ 3_manim/        Manim 数学动画
  │
  ▼  shared/finalize.py  合配音、烧字幕（② 的配音和字幕已在 HTML 里，不走这步）
out/hexagon_*.mp4
```

核心思路是**先配音、后做画面**：配音先出来，拿到每个词的真实时间点（比如"三角形"在 8.98 秒），
画面再按这个时间轴去对齐——念到哪个词，对应的图形就出现。三种做法共用同一份 `timeline.json`。

## 目录

| 路径 | 内容 |
|---|---|
| `content/hexagon.json` | 稿子：7 个分镜，每个分镜一句旁白 + 标题 + 画面要用的数据 |
| `shared/tts.py` | 稿子 → 配音（Edge TTS，响度拉到约 -16 LUFS）+ 时间轴 + 字幕 |
| `shared/finalize.py` | 无声画面 + 配音 + 字幕 → 成片 |
| `1_cards/render.py` | 做法①：图文卡片 |
| `2_hyperframes/build.py` | 做法②：读 timeline 生成 `index.html`（HTML + GSAP 动画，字幕和配音也在里面），`--render` 连渲染一起跑 |
| `3_manim/scene.py` | 做法③：Manim 动画 |
| `build/hexagon/` | 中间产物（配音、时间轴、字幕、卡片图） |
| `out/` | 成片 |

## 怎么跑

```powershell
cd video-lab
uv run python shared/tts.py content/hexagon.json   # 配音 + 时间轴 + 字幕（要联网）
uv run python 1_cards/render.py build/hexagon      # ① 图文卡片，约 1 分钟（含合成）

uv run python 2_hyperframes/build.py hexagon --render   # ② 生成 index.html → lint → 渲染，约 3 分钟；首次会下载约 270MB 的 Chrome

cd 3_manim
uv run manim render scene.py Hexagon --format mp4  # ③ 无声画面，约 50 秒；设 $env:PREVIEW='1' 可出低清预览
cd ..
uv run python shared/finalize.py 3_manim/media/videos/scene/1920p30/Hexagon.mp4 build/hexagon out/hexagon_3_manim.mp4
```

Python 环境由 `uv` 管理（`pyproject.toml` 里配了清华 PyPI 镜像，国内装包快）。
HyperFrames 的匿名使用统计已关闭（`npx hyperframes telemetry disable`）。

## 三种做法的体会

| | ① 图文卡片 | ② HyperFrames | ③ Manim |
|---|---|---|---|
| 画面 | 静态卡片逐条出现，像 PPT | 浏览器能画的都能用：SVG、渐变、遮罩、flex 排版，字幕逐词高亮 | 几何连续变形：图形轮廓"滚"成直线、蜂蜜液面上涨 |
| 出一条的耗时 | 约 1 分钟 | 约 2.5 分钟（逐帧截图，约 15 帧/秒）；改版时用 `snapshot` 抽几帧看，30 秒内 | 渲染约 50 秒 + 合成 15 秒 |
| 上手难度 | 低：会 Pillow 画图就行 | 中：会 HTML/CSS/GSAP 就顺手，但要守它的规矩（lint 能抓大部分，少数问题只有看画面才发现） | 中偏高：要懂 Manim 的 API，还要踩帧取整、缓存等坑 |
| 换题目要改什么 | 每个分镜一个画图函数（约 130 行），画图小工具可复用 | 条形图、数据卡、"年份/人物/结论"三种画面按 data 的形状自动选，不用改代码；本题专属插画（hook/tiling/question/outro）每个 40–60 行要重画 | 7 个分镜方法（约 250 行）基本重写，对齐框架（约 120 行）可复用 |
| 适合 | 模板化量产：换稿子就能出 | 排版、文字、数据卡为主的科普；真要大批量走它自带的"子合成 + 变量 + `render --batch`" | 一个题目一个程序的精品几何/数学科普 |

共同点：三种做法改文案都很省事——稿子变了就重跑 `tts.py`、重渲染、再合成，画面会自动跟着新的时间轴对齐；
如果某个触发词从稿子里删掉了，代码会直接报"找不到词"，不会悄悄错位。

### ② HyperFrames 的坑（已在代码里绕过）
- `render` 不用系统 Chrome，会自己下载钉死版本的 chrome-headless-shell（约 270MB，放在 `%USERPROFILE%\.cache\hyperframes\chrome`，`npx hyperframes browser clear` 可删）。下不动时可以设环境变量 `HYPERFRAMES_BROWSER_PATH` 指向本机 Chrome/Edge（源码里有这个开关，这次没用到）。
- GSAP 不走 CDN（jsdelivr 在国内可能不通）：`npm i gsap` 后把 `gsap.min.js` 复制到 `assets/` 本地引用。
- GSAP 给 SVG 做缩放入场时整组图形会跑偏：起止两头都写 `transformOrigin`，并设 `smoothOrigin: false`。lint 抓不到，只能看截图。
- 渲染是逐帧跳到指定时间截图，不触发 `onUpdate` 这类回调：只能用纯属性补间，数字滚动这种效果做不了。
- 非内置字体要声明 `@font-face`：写成 `src: local("Microsoft YaHei")`。
- lint 有 34 个 warning，都是"文件太长、建议拆成子合成"，不影响渲染。
- 它把单声道配音原样复制成左右两声道，LUFS 读数因此比单声道高 3 dB（R128 把两个声道的能量相加）。`finalize.py` 也改成同样的做法（注意 `-ac 2` 会把音量乘 0.707，要用 `pan` 滤镜原样复制），三版测出来都是约 -14 LUFS，正好是短视频平台常见的目标响度。

### ③ Manim 的坑（已在代码里绕过）
- 等待和动画的帧数取整方式不一样，累计会差一帧：一律按"当前真实时间"去补齐，不手算累加。
- 命中缓存的动画按名义时长计时，和真实帧数对不上：关掉缓存（`config.disable_caching = True`）。
- 脚本顶部设的分辨率会盖掉命令行的 `-ql`：低清预览改用环境变量 `PREVIEW=1` 切换。
- 没装 LaTeX：数字一律用 `Text`，不用 `MathTex`/`DecimalNumber`。
