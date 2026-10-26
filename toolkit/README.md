# toolkit：工具

**类别：工具。** 所有项目共用的东西，只有一份；改这里会影响所有视频和试验。

| 内容 | 说明 |
|---|---|
| [vlab/](vlab/) | 公共代码包（Python 里 `import vlab`）：`pipeline` 配音合成、`audio` 音效配乐混音、`fonts` 项目字体（思源黑体，随仓库入库）、`render` 渲染器、`scenes` 可复用画面、`videokit` 视频工程、`tools` 预览和自检 |
| [bin/](bin/) | 可选：放本机的 ffmpeg.exe 等程序（不入库）；没有就用系统 PATH 上的 |

命令（`uv sync` 后任意目录可用）：`vlab-tts`、`vlab-finalize`、`vlab-preview`、`vlab-build`、`vlab-style`、`vlab-check`，用法见根目录 README。

规则：

- 被两个以上项目用到、或在 `research/` 里验证成熟的代码，才提升进 `vlab/`。
- 改了 `vlab/` 之后跑一遍 `uv run vlab-check`。
- `vlab/tools/script_gate.py` 是剧本闸门：`videos/` 下的正式项目没有项目负责人的剧本确认记录时，`vlab-tts` 和 `vlab-build` 拒绝执行。不要削弱或绕过它（流程见 `process/SCRIPT-REVIEW.md`）。
- 改 `vlab/videokit/manim_templates.py` 会让视频工程的缓存全部失效（它的内容参与镜头指纹），改之前想清楚。
