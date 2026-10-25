# 《为什么没有绿色的恒星》事实核查

**核查日期**：2026-10-22　**状态**：核心机制已确认，部分数字待补

规则：画面和旁白里出现的每个事实和数字都要在这里有一条。标"自算"的是用物理公式算的，脚本在本目录 `verify.py`。

---

## 核心机制

| # | 说法 | 核实结果 | 来源 |
|---|---|---|---|
| 1 | 恒星发光接近黑体辐射，光谱是连续的，覆盖整个可见光范围 | ✅ 确认 | [Las Cumbres Observatory](https://lco.global/spacebook/light/black-body-radiation/)（页面本机抓取失败，经搜索结果摘要确认；天文学教科书通识） |
| 2 | 峰值波长不决定恒星的视觉颜色 | ✅ 确认。原文："a star's peak wavelength doesn't determine its color, because the light it emits is spread across the whole visible range" | [BBC Science Focus](https://www.sciencefocus.com/space/why-arent-there-any-green-stars) |
| 3 | 峰值在绿色的恒星，红光蓝光也很强，人眼混合后看到白色 | ✅ 确认。原文："Stars with peak wavelengths in the green also emit lots of radiation in the red and blue part of the spectrum. Our eyes combine all of these colors and we see white" | 同上 |
| 4 | 黑体轨迹在色度图上从红经白到蓝，不经过纯绿区 | ✅ 确认。原文："the black-body curve moves away from the locus of spectrally pure colors, and passes through the white region of visible color space" | 维基百科 Green 条目（搜索结果摘要） |

**一句话**：不是没有峰值在绿色的恒星，是峰值在绿色的恒星看起来是白的。太阳就是其中一颗。

---

## 数字

| # | 数字 | 核实结果 | 来源 |
|---|---|---|---|
| 5 | 维恩位移常数 b = 2.897771955×10⁻³ m·K | ✅ CODATA 定义值 | 物理常数 |
| 6 | 太阳表面温度约 5772 K | ✅ 常用值（有效温度）。部分来源写 5700 K 或 5800 K，量级一致 | 搜索结果多处；写稿时用"约 5800 度"口语化 |
| 7 | 太阳的峰值波长约 500 nm，落在绿色附近 | ✅ 自算：b ÷ 5772 K = 502.0 nm | 自算，见 verify.py |
| 8 | 峰值要落在绿色（500–565 nm），温度约 5100–5800 K | ✅ 自算 | 自算 |
| 9 | 太阳在蓝 450nm、绿 550nm、红 650nm 的辐射强度比约 0.99 : 1.00 : 0.88 | ✅ 自算（普朗克定律）。**这是全片最关键的证据** | 自算，见 verify.py |
| 10 | 参宿七（Rigel）约 12100 K，蓝白色，B8Ia 型 | ✅ 维基百科给 12100±150 K | [Wikipedia Rigel](https://en.wikipedia.org/wiki/Rigel)（搜索结果摘要） |
| 11 | 参宿四（Betelgeuse）红超巨星，约 3600 K | 🟡 各来源差异大，2500–3900 K 都有。**画面上写"约 3600 度"并注明是估计值** | 搜索结果，无权威单一值 |
| 12 | 光谱型 OBAFGKM 从热到冷，颜色从蓝到红，没有绿 | ✅ 确认。O 30000–60000K 蓝、B 10000–30000K 蓝白、A 7500–10000K 白、F 6000–7500K 黄白、G 5000–6000K 黄、K 3500–5000K 橙、M <3500K 红 | HyperPhysics（页面本机打不开，经搜索结果摘要确认）；各来源边界略有差异 |

---

## 简化之处（画面上要标注）

| 简化 | 精确说法 | 怎么处理 |
|---|---|---|
| "太阳是黄色的" | 太阳在大气外看是白色的，地面看偏黄是大气散射掉蓝光所致 | 这正是片中的一个转折点，不是错误 |
| 恒星 = 黑体 | 恒星光谱有吸收线，不是理想黑体 | 旁白说"接近黑体"，画面小字注明 |
| 峰值波长用波长表示 | 用频率表示时峰值位置不同（在近红外） | 不展开，画面小字一句带过 |
| 参宿四 3600 K | 各来源 2500–3900 K | 画面写"约 3600 度（估计值）" |

---

## 还要补查

- [ ] 参宿四温度的权威来源（SIMBAD 天体数据库或同行评议论文）
- [ ] 人眼三种视锥细胞的响应峰值波长（讲"人眼怎么混合颜色"时要用）
- [ ] 有没有过"绿色恒星"的历史误报（如果有，是很好的钩子素材）
