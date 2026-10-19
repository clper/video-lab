# AI-Vedio 技术路线标准

**效果优先，技术为内容服务。** 不局限于单一方案，可根据内容类型混合使用。

---

## 一、技术方案全景

### 方案对比

| 方案 | 擅长 | 局限 | 渲染速度 | 学习曲线 | 成本 |
|---|---|---|---|---|---|
| **Manim** | 几何/数学/物理连续变形 | 静态排版弱，API 复杂 | 快（1× 实时） | 中偏高 | 免费 |
| **HyperFrames** | 排版/文字/数据卡/版式 | 几何动画弱，onUpdate 不触发 | 中（1.5-2× 实时） | 中 | 免费 |
| **Pillow 图文卡片** | 模板化量产，简单直接 | 动画能力弱，像 PPT | 快（1× 实时） | 低 | 免费 |
| **Remotion** | React 组件生态，企业级 | 许可限制（>3 人付费） | 中 | 中 | 免费/付费 |
| **像素级生成**（Seedance/可灵/Sora） | 真人/实拍/复杂光影 | 不可控，抽卡，贵 | 慢（按秒计费） | 低 | 高 |
| **Blender** | 3D 场景/产品渲染 | 学习曲线陡 | 慢 | 高 | 免费 |
| **After Effects** | 专业动效，上限最高 | 需人工，难自动化 | 中 | 高 | 付费 |

### 内容类型 → 技术选择

| 内容类型 | 首选 | 备选 | 混合策略 |
|---|---|---|---|
| 数学科普（公式/几何/变形） | **Manim** | HyperFrames | Manim 做几何 + HyperFrames 做文字 |
| 数据可视化（图表/数字） | **HyperFrames** | Manim | HyperFrames 做图表 + Manim 做动画 |
| 产品发布（版式/文字） | **HyperFrames** | Remotion | - |
| 模板化量产（资讯/语录） | **Pillow** | HyperFrames | - |
| 真人/实拍 | **像素级生成** | After Effects | - |
| 3D 场景 | **Blender** | - | - |

---

## 二、标准工作流

### 流程概览

```
选题 → 写剧本 (content/xxx.json)
       ↓
     配音 (shared/tts.py)
       ↓
     生成 narration.wav + timeline.json + subs.ass/srt
       ↓
     渲染画面 (manim/scene.py 或 hyperframes/index.html)
       ↓
     合成 (shared/finalize.py)
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

### 2. 配音链路（shared/tts.py）

**输入**：`content/xxx.json`  
**输出**：
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
python -m manim render manim/scene.py SceneName --format mp4
```

**HyperFrames**：
```powershell
npm run render
```

### 4. 合成（shared/finalize.py）

**输入**：无声画面.mp4 + build/xxx/  
**输出**：`renders/xxx_final.mp4`

**处理**：
- 烧字幕（subs.ass）
- 合配音（narration.wav）
- 单声道→立体声（pan 滤镜）
- 响度标准化（-16 LUFS）

---

## 三、项目结构规范

### 正式视频项目

```
三位编号-英文 slug/
├── content/           # 剧本稿子 (json)
├── manim/             # Manim 动画 (scene.py)
├── hyperframes/       # HyperFrames 动画 (index.html) - 可选
├── shared/            # 复用工具 (tts.py, finalize.py)
├── build/             # 中间产物 (narration.wav, timeline.json, subs.ass)
└── renders/           # 最终输出 (mp4)
```

### 参考项目

```
000-claude-xxx/        # Claude 开发的参考项目
```

### 公共资源

```
tools/                 # 公共工具 (ffmpeg.exe, ffprobe.exe)
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

### Edge TTS

**版本**：7.3.1  
**安装**：`python -m pip install edge-tts`

**关键**：
- 用 `boundary="WordBoundary"` 获取真实词级时间点
- 响度标准化到 -16 LUFS（短视频平台标准）
- 单声道配音复制成左右声道（pan 滤镜，不用 -ac 2）

### FFmpeg

**版本**：7.1  
**位置**：`tools/bin/ffmpeg.exe`

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

| 类型 | 格式 | 示例 |
|---|---|---|
| 正式视频 | `三位编号 - 英文 slug` | `001-float-precision` |
| 参考项目 | `000-claude-xxx` | `000-claude-video-lab` |
| 测试项目 | `_test-用途` | `_test-render` |
| 公共库 | `_lib-用途` | `_lib-templates` |

---

## 六、待验证方案

| 方案 | 优先级 | 验证状态 |
|---|---|---|
| Remotion | 中 | 待测试 |
| 像素级生成（Seedance/可灵） | 低（真人场景才用） | 待测试 |
| Blender | 低（3D 场景才用） | 待测试 |
