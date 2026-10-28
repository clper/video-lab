# 009《他比我重一倍，我借了他的力》

**路线**：火柴人 VS 物理（试水，2026-10-27 项目负责人定）　**剧本**：[SCRIPT.md](SCRIPT.md)（v0.2，2026-10-27 确认）
**形态**：16:9 横屏，无旁白，正好 120 秒（120 BPM 拍格，240 拍）；音效代码合成，配乐由项目负责人剪辑时从曲库加

## 怎么重出

```powershell
uv run vlab-build videos/009-redirect/project.yaml --jobs 2
```

- 动作由 `vlab-build` 自动算（project.yaml 的 `precompute` 跑 `motion.py`）：`choreo.py` 或 `toolkit/vlab/stick/` 改了才重算，
  按时间轴切成 `build/009-redirect/shots/<镜头>.json`，每镜用 `params_files` 交给镜头卡 `stickScene`；数据没变的镜头直接复用。
- `uv run python videos/009-redirect/motion.py --sheet 16,38,100 --name=xxx`：只出骨架拼图（几秒），改动作时先看这个。
- 成片：`renders/009-redirect_neon.mp4`（只有音效）；单独的音效轨：`build/009-redirect/sfx.wav`。

## 文件

| 文件 | 内容 |
|---|---|
| `choreo.py` | 全片的动作编排：两个人的关键帧、四段布偶（被打飞两次、扑倒、过肩摔）、羽毛、物理标注、相机、粒子和音效事件 |
| `motion.py` | 预计算：跑 `choreo.py`，按时间轴切镜头数据，写音效事件表 |
| `project.yaml` | 24 镜的拍数（合计 240 拍）和内容说明（note）、配乐提示（music_cues）、体检破例 |
| `styles/neon.yaml` | 配色：金 = 小个子，青 = 大块头 |

公共代码在 `toolkit/vlab/stick/`（骨架、布偶物理、场景导出）和镜头卡 `toolkit/vlab/render/remotion/src/cards/StickScene.tsx`。

## 关键点时刻表（剪配乐用）

`vlab-build` 生成：[renders/009-redirect_cues.md](renders/009-redirect_cues.md)。
同名的 `.srt` 可以导入剪映当字幕轨，每一条就是一个标记。要改提示，改 project.yaml 的 `music_cues`。

画面按 120 BPM 编排：每拍 0.5 秒、每小节 2 秒。选 120 BPM 左右的曲子，第一拍对齐片头，关键动作就落在拍上。

## 体检（第一版，2026-10-27）

- `vlab-review`：24 镜、120.00 秒、响度 -14.5 LUFS、逐帧没有黑屏空屏；公共组件覆盖 100%（全部由镜头卡 stickScene 画）。
- 没过的 4 项都是有意的，理由写在 `project.yaml` 开头：同款连镜 24（一场连续的打斗）、S19 6 秒、S24 8 秒（落点）、平均镜长 5.0 秒。
- motion 基线（STYLE-IMPACT 规矩 3）：全片 1.03（第一版 0.73，加了跟拍、主光、背景雾、手持微动以后），没有 2 秒以上的死帧；低于 1.0 的段落都是剧本里有意安静的地方，理由同样写在 `project.yaml` 开头。

## 物理（画面上算出来的部分）

- 重力 9.8 m/s²，按小个子 1.70 米、大块头 2.05 米换算成像素（1 米 ≈ 190 px）。
- 被打飞、被推飞、扑倒、过肩摔落地都交给 Verlet 布偶算（`toolkit/vlab/stick/ragdoll.py`）；过肩摔的前 0.7 秒是"绕支点转"的脚本动作，之后交给布偶。
- S15 的两支箭头：挡要抵消全部动量；只让方向偏 10°、速度不变，所需冲量是 2·sin5° ≈ 0.17（约六分之一）——短箭头就按这个比例画，屏上标"示意"。
- S17 的重心按人体各段的质量比例算（Dempster / Winter 表，见 `toolkit/vlab/stick/rig.py`）；支撑面是两脚之间，重心越过前脚的那一帧变红。
- 羽毛：跟着空气走（τ = 0.05 s，静止空气里 0.58 m/s 下落）；手掌扫过时的气流用圆柱绕流的偶极子解，屏上标"示意"。
