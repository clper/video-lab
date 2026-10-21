# research/visual：画面技术试验

**类别：开发测试。** 每个目录是一项画面技术的试验，自带脚本和 `renders/` 输出。

| 编号 | 试验 | 内容 | 备注 |
|---|---|---|---|
| 01 | ffmpeg-transitions | FFmpeg 20 种转场 | |
| 02 | ffmpeg-effects | FFmpeg 15 种特效 | |
| 03 | opencv-basics | OpenCV 图像处理 8 项 | 需先 `uv add opencv-python` |
| 04 | blender-basics | Blender 材质 + 相机环绕 | 需安装 Blender，用 `blender --background --python` 运行 |
| 05 | processing-basics | 生成艺术 5 种（Python + OpenCV 实现 Processing 风格） | 需先 `uv add opencv-python` |
| 06 | landscape | 程序化日落湖景：山、水、鹿、雁群、跃鱼 | 渲染代码已提升为 `toolkit/vlab/scenes/landscape.py` |
| 07 | shader-raymarch | GLSL 着色器：云海飞越雪山 | 着色器在 `toolkit/vlab/scenes/shaders/` |
| 08 | video-spec | 视频工程层 + 风格参考原型 | 代码在 `toolkit/vlab/videokit/` |
| 09 | manim-showcase | Manim 能力展示：3D 相机、粒子、变形、分形等 | |
| 10 | manim-fractal | Manim 分形：有限面积、无限边界 | |
| 11 | pixel-story | 像素风小故事《掉落的星星》 | 含配音、RPG 对话框、芯片音乐 |

01–05 最早在原开发机上完成；本机上 01、02 已重新跑通。
