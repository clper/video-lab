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

| 编号 | 项目 | 技术 | 时长 | 状态 |
|---|---|---|---|---|
| 001 | [float-precision](001-float-precision/) | Manim 2D | 45.74 秒 | ✅ 完成 |
| 002 | [mobius-strip](002-mobius-strip/) | Manim 3D | 52.62 秒 | ✅ 完成 |

### 001-float-precision《0.1 + 0.2 为什么不等于 0.3》

**题材**：浮点数精度（计算机科普）  
**技术**：Manim 2D 几何动画 + Edge TTS 配音 + 字幕烧录  
**亮点**：二进制位流动、尾数格子截断、误差累积可视化

### 002-mobius-strip《莫比乌斯环：只有一个面的奇迹》

**题材**：拓扑学（数学/几何科普）  
**技术**：Manim 3D 参数曲面 + Edge TTS 配音 + 字幕烧录  
**亮点**：莫比乌斯环连续变形、蚂蚁爬行路径、剪开动画

---

## 参考项目

| 项目 | 说明 |
|---|---|
| [000-claude-video-lab](000-claude-video-lab/) | Claude 开发的参考项目，同一题目「蜂巢为什么是六边形」用三种技术各做一版（Pillow/HyperFrames/Manim） |

---

## 技术路线

详见 [TECHNOLOGY.md](TECHNOLOGY.md) —— 技术选型、工作流、踩坑记录、命名约定。

**核心原则**：效果优先，技术为内容服务，可以混合使用。

| 内容类型 | 首选技术 |
|---|---|
| 数学科普/抽象概念 | Manim（几何连续变形） |
| 数据可视化/动态图表 | HyperFrames 或 Remotion |
| 图文卡片/简单动画 | Pillow 或 HyperFrames |
| 真人/实拍 | 像素级生成（Seedance/可灵） |
| 3D 场景 | Blender |

---

## 目录结构

```
AI-Vedio/
├── 000-claude-video-lab/    # 参考项目（Claude 开发）
├── 001-float-precision/     # 正式视频 001
── 002-mobius-strip/        # 正式视频 002
├── tools/                   # 公共工具（ffmpeg/ffprobe）
├── TECHNOLOGY.md            # 技术路线标准
└── README.md                # 本文件
```

---

## 快速开始

### 渲染已有视频

```powershell
# 001 浮点数精度
cd 001-float-precision
python -m manim render manim/scene.py FloatPrecision --format mp4

# 002 莫比乌斯环
cd 002-mobius-strip
python -m manim render manim/scene.py MobiusStrip --format mp4
```

### 开发新视频

1. 创建项目目录：`003-xxx/`
2. 写剧本：`content/xxx.json`
3. 复制 shared/：从 001 或 002 复制 `shared/` 目录
4. 跑 TTS：`python shared/tts.py content/xxx.json`
5. 写动画：`manim/scene.py`
6. 渲染：`python -m manim render manim/scene.py SceneName --format mp4`
7. 合成：`python shared/finalize.py renders/raw.mp4 build/xxx renders/final.mp4`

---

## 许可证

本项目代码采用 MIT 许可证。视频内容（文案、配音）版权归作者所有。
