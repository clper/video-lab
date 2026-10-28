# 做一条片子：按片型走

写给开新片的人和 AI。规则以 `process/` 为准（路线、剧本闸门、风格硬规矩、发布清单），这里只讲"按哪种片型、怎么用工具做出来"。
工程文件的字段见 [design/DESIGN-video-project.md](design/DESIGN-video-project.md)。

## 所有片型都一样的部分

1. **选题**：只从 `process/ROUTES.md` 已定的路线里出。
2. **剧本**：建 `videos/三位编号-英文名/`，写 `SCRIPT.md`：全部文字按镜号列出，事实和数字标来源，开头写"剧本确认：待审"。
   项目负责人逐条审完、明确确认之前，`vlab-build` 和 `vlab-tts` 都会拒绝执行（`process/SCRIPT-REVIEW.md`）。
3. **工程**：写 `project.yaml`。配乐剪辑时从曲库加，所以 `audio.music: false`；音效用代码合成（`audio.sfx` 或 `audio.sfx_file`）。
   每镜写一句 `note`（这一镜在演什么），剪辑时刻表要用。
4. **构建**：`uv run vlab-build videos/xxx/project.yaml`。改了什么只重做什么；想先快速看，设 `$env:PREVIEW='1'`。
5. **看图**：`uv run vlab-preview <成片> --timeline <timeline.json>`，逐项核对内容和标签（颜色像不像名字、数字是不是脚本里的值）。
6. **体检**：`uv run vlab-review videos/xxx/project.yaml --loudness`。有意破的硬指标，理由写进 `SCRIPT.md`，
   同时写进 `project.yaml` 的 `review.waive`，体检就会列为"破例（已说明）"。
7. **剪辑**：按 `renders/<id>_cues.md` 配乐（同名 `.srt` 导入剪映就是一条标记轨），曲库授权按 `process/PUBLISH.md` 第 4 条。
8. **发布**：过 `process/PUBLISH.md` 清单；发布 72 小时后按路线复盘。

改了 `toolkit/vlab/` 的公共代码，跑一遍 `uv run python -m vlab.tools.smoke`（十几秒）；改了镜头卡，加 `--tsc`。

## 片型 A：有旁白的讲解片（主线、科学史；例子 007、008）

- **时间轴由配音定**：每镜写 `narration`，`vlab-build` 先配音，成片长度由字数定（约 0.236 秒/字）。
  呼吸镜不写旁白的话写 `min_hold`。
- **画面跟着词走**：元素用 `cues: {元素: {on: 词}}` 绑定配音里的词，不写死秒数。
  Edge TTS 的分词和直觉不同，先把 `timeline.json` 的词表打出来看一遍再绑。
- **镜头**：常规镜头用公共镜头卡（`renderer: remotion` + `card`），`uv run vlab-cards --out x.png` 看卡库长什么样；
  卡库盖不住的再考虑 manim 模板、着色器或 custom。
- 不要随手重跑配音：旁白文字没改就别动，时间轴一变整条片子都要重渲。

## 片型 B：无旁白的动作片（火柴人 VS 物理；例子 009）

- **时间轴由拍格定**：`grid: {bpm: 120}`，每镜写 `hold`（占几拍）。关键动作落在小节第一拍，配乐好对拍。
- **先算动作、再按镜头画**：
  - 动作编排写在项目里（009 的 `choreo.py`），用公共的 `vlab.stick`（骨架、关键帧、布偶物理、场景导出）。
  - 预计算脚本（009 的 `motion.py`）按时间轴把整片动作切成每镜一份 JSON，写在 `build/<id>/shots/`。
  - `project.yaml` 顶层写 `precompute: {script: motion.py, inputs: [choreo.py, ../../toolkit/vlab/stick]}`，
    每镜写 `card: stickScene, renderer: remotion, params_files: {data: build/<id>/shots/<镜头>.json}`。
  - 改动作时先出骨架拼图看（`motion.py --sheet 16,38,100`，几秒），满意了再构建。
    动作数据按 30 fps 逐帧算，这类片子不能用 `PREVIEW=1`（构建会报帧数对不上）。
- **配乐提示**：在 `music_cues` 里写清哪里重拍、哪里留静音，构建时进剪辑时刻表。
- 无旁白要满足 STYLE-IMPACT 规矩 2 的三条（≤120 秒、每 5 秒有画面事件、音乐本身有叙事），理由写进 `SCRIPT.md`。

## 片型 C：数据驱动的模拟片（候选路线"模拟实验室"等）

和片型 B 同一套做法，区别只在数据从哪来：

- 预计算脚本跑模拟（堵车、火灾蔓延、排队……），按时间轴把结果切成每镜一份 JSON；
- 画面用公共卡吃数据（`params_files`）。现有的卡吃不下这种数据，就新做一张卡放进 `toolkit/vlab/render/remotion/src/cards/`，
  不要在项目里写一次性的 custom 套壳；
- 有旁白就用片型 A 的时间轴（预计算脚本读 `VLAB_TIMELINE` 就能按配音切），无旁白就用拍格。
- 模拟要可重现：固定随机种子，同样的输入每次算出同样的数据（不然缓存会一直失效）。

## 片型 D：历史讲解片（今后的主要方向，还没做过第一条）

2026-10-28 项目负责人定历史为今后的主要方向。做法待细化；一种可参考的讲法是：
反常识钩子 → 一手史料 → 把机制画出来 → 数据 → 落点。

- **时间轴**：一般有旁白，用片型 A。
- **史料**：`SCRIPT.md` 里每个年份、人名、数字、引文都标出处，优先一手史料（档案、律令、正史原文）；有争议的说清楚。
- **画面**：人物和古代场景不画写实形象，用插画、剪影、文物和档案的示意画、字幕。
- **地图是红线**：不画省界、国界和历史疆域（`process/PUBLISH.md` 第 8 条）。要表达路线，用不带真实边界的示意线路图
  （起点、终点、中间一串站点）。
- **还缺的公共能力**（做第一条之前补进 `toolkit/`，见 `docs/TODO.md`）：宋体字体（思源宋体，OFL 可商用）、
  大字标题和关键词高亮、档案卷轴（竖排字、印章）、示意线路图、扁平插画场景、数据阶梯图。
