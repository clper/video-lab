# archive：存档

**类别：存档。** 只读快照，不再修改。需要参考它的做法时，把要用的部分重新实现到 `toolkit/vlab/` 或 `research/` 里。

| 内容 | 说明 |
|---|---|
| [000-claude-video-lab/](000-claude-video-lab/) | 最早的参考项目：同一题目「蜂巢为什么是六边形」用 Pillow、HyperFrames、Manim 各做一版。自带一份旧的 `shared/` 和自己的环境配置（`pyproject.toml`、`uv.lock`），只属于它自己 |

它目录里如果有 `.venv`，是本机的旧环境，可以删掉；HyperFrames 版要重新渲染时，先在 `2_hyperframes` 里 `npm ci`。
