# archive：存档

**类别：存档。** 不再开发的东西放这里。需要参考它们的做法时，把要用的部分重新实现到 `toolkit/vlab/` 或 `research/` 里。

| 内容 | 说明 |
|---|---|
| [000-claude-video-lab/](000-claude-video-lab/) | 最早的参考项目（只读快照）：同一题目「蜂巢为什么是六边形」用 Pillow、HyperFrames、Manim 各做一版。自带一份旧的 `shared/` 和自己的环境配置（`pyproject.toml`、`uv.lock`），只属于它自己 |
| 001–006 | 开发过程中的探索作品，2026-10-26 归档，不再是主力视频。正在做的视频在 `videos/` |

000 目录里如果有 `.venv`，是本机的旧环境，可以删掉；HyperFrames 版要重新渲染时，先在 `2_hyperframes` 里 `npm ci`。

---

## 001–006：归档的探索作品

| 编号 | 视频 | 技术 | 时长 |
|---|---|---|---|
| 001 | [0.1 + 0.2 为什么不等于 0.3](001-float-precision/) | Manim 2D（另有 HyperFrames 版） | 45.74 秒，竖屏 |
| 002 | [莫比乌斯环：只有一个面的奇迹](002-mobius-strip/) | Manim 3D | 52.62 秒，竖屏 |
| 003 | [夕阳为什么是红的](003-sunset-red/) | 着色器 + Manim + 程序化风景混剪 | 60.95 秒，竖屏 |
| 004 | [为什么没有绿色的恒星](004-green-star/) | Manim + 着色器 + 文字动效，第一条横屏片 | 210.45 秒，横屏 |
| 005 | [涌现](005-emergence/) | Remotion 镜头卡库 + 着色器 | 61.33 秒，竖屏 |
| 006 | [对折](006-fold/) | Remotion 镜头卡库，纯音乐 + 字幕，51 镜 | 180 秒，横屏 |

## 成片：归档后不入库，从输入重新生成

按入库规则（`process/REPO.md`），归档片的成片不入库；重生成需要的配音、时间轴、字幕、分镜片段都在各自目录里，照常入库。
有 ffmpeg 就能重新拼出来，不用联网，不用显卡：

```powershell
# 001、002：Manim 渲好的中间视频已入库，直接合配音、烧字幕
cd archive/001-float-precision
uv run vlab-finalize media/videos/scene/1920p30/FloatPrecision.mp4 build/float-precision renders/float-precision_final.mp4
cd archive/002-mobius-strip
uv run vlab-finalize media/videos/scene/1920p30/MobiusStrip.mp4 build/mobius-strip renders/mobius-strip_final.mp4

# 003、004：总装脚本跳过已有片段，只做拼接和混音
cd archive/003-sunset-red; uv run python build.py
cd archive/004-green-star; uv run python build.py
```

**2026-10-26 实测**：四条都在归档后的新位置重新生成，和原成片逐帧比对。

| 编号 | 重生成用时 | 结果 |
|---|---|---|
| 001 | 1.1 分钟 | 帧数一致，画面逐帧一致，音频一致 |
| 002 | 15.8 分钟 | 帧数一致，画面逐帧一致，音频一致 |
| 003 | 1.0 分钟 | 帧数一致，画面逐帧一致，音频一致 |
| 004 | 1.6 分钟 | 帧数一致，画面逐帧一致，音频一致 |

002 慢，是因为当时 Manim 的中间视频从没入库，这次重渲了一遍 3D；渲出的中间视频已经入库，以后也只要拼接。
001、002 的字幕是微软雅黑（当时的字体），重生成要求系统里有这款字体，和原片才会一致。

## 005、006 的情况

| 编号 | 情况 | 处理 |
|---|---|---|
| 005 | 另一个 AI 推上来的版本里没有配音 wav 和分镜片段，只剩指纹文件；成片也不在 | **没法完美重生成**：重跑配音，时间轴会变，画面要全部重做。作为过时的探索作品，不再补救 |
| 006 | 配乐母带、时间轴、字幕都在，缺 Remotion 分镜片段 | **成片不入库**（64 MB，项目负责人的本地磁盘上还有一份）。要重生成，先在 `toolkit/vlab/render/remotion` 里 `npm.cmd install`，再 `uv run vlab-build archive/006-fold/project.yaml`，要重渲全部 51 个镜头；纯音乐片不需要配音，镜头卡禁用无种子随机数，理论上能和原片一致，但没有实测 |
