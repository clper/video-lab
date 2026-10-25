"""vlab：本仓库所有视频共用的代码（uv sync 后以可编辑模式安装，任意目录都能 import / 用命令）。

    vlab.pipeline   配音 tts、合成 finalize                         命令：vlab-tts、vlab-finalize
    vlab.render     渲染器：glsl（着色器 → 视频片段）
    vlab.scenes     可复用的画面生成器：landscape（程序化湖景）、shaders/（云海、大气散射）
    vlab.videokit   视频工程：project.yaml + 风格文件 → 成片            命令：vlab-build、vlab-style
    vlab.tools      预览拼图、环境自检                               命令：vlab-preview、vlab-check
"""
