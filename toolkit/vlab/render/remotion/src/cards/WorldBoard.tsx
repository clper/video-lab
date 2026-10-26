import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp, lerp, mulberry32 } from "../common/random";
import { N_SONGS, appealHeights, heightsOf, makeWorlds } from "../lib/worlds";
import { Badge, Note, Panel, TopLight, barPos, dotPos, ease, span } from "../lib/boardDraw";

// 单块世界板的特写：计数器怎么跳、累积优势怎么在一块板上长出来、倒置实验、还有落点那颗没被点开的光点。
// 和 WorldBoards 共用 lib/boardDraw 的画法，所以"同一块板"在远景和特写里长得一样。

export type BoardMode =
  | "counting"   // 光点下的下载数一个个跳起来
  | "digit"      // 推近一颗光点和它的数字；旁边一闪而过：门口的队、手机上的销量
  | "sim0"       // 空板，全是 0
  | "sim1"       // 开头几次点击随机落下
  | "sim2"       // 一首歌刚好多被点了几下
  | "sim3"       // 后来的人被它吸过去
  | "sim4"       // 领先一点，放大一点：光点长成光柱，差距拉开
  | "term"       // 名词落下：累积优势 / 马太效应
  | "tap"        // 你随手一点，落在最高的那根上
  | "fresh"      // 换一块新板（倒置实验）
  | "flip"       // 板上下翻转
  | "fakebadge"  // 最矮的光柱挂上假的冠军徽章
  | "selffulfil" // 假的人气慢慢变成真的
  | "recover"    // 最好的那几首又爬回来
  | "glide"      // 呼吸镜：光柱回升的近景
  | "alone"      // 只剩一颗暗着的光点
  | "edge"       // 它的轮廓其实很亮
  | "missed"     // 开头那几次点击从它旁边落过
  | "freeze";    // 板定格、变暗

type Props = {
  mode?: BoardMode;
  label?: string;
  label2?: string;
  sub?: string;
  note?: string;
  badge?: string;
  /** 用哪个世界的数据（默认第 3 块板） */
  world?: number;
};

const W = 1920;
const H = 1080;
const PX = 360;
const PY = 176;
const PW = 1200;
const PH = 640;
const SIM_SEED = 1130;

export const WorldBoard: React.FC<Props> = ({ mode = "counting", label = "", label2 = "", sub = "", note = "", badge = "", world = 2 }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();
  const p = clamp(frame / Math.max(1, durationInFrames - 1));
  const data = makeWorlds();
  const appeal = appealHeights(data);
  const finals = heightsOf(data.downloads[world]);
  const best5 = data.byQuality.slice(0, 5);
  const worstSong = data.byQuality[N_SONGS - 1];

  // ---------- 模拟段：一块板上的累积优势 ----------
  // 领头的那首：质量中等偏上（第 9），开头刚好多被点了几下
  const leader = data.byQuality[8];
  const sim = React.useMemo(() => {
    const rnd = mulberry32(SIM_SEED);
    // sim1：6 次随机点击落在 6 首不同的歌上
    const firstClicks = Array.from({ length: 6 }, () => Math.floor(rnd() * N_SONGS));
    // sim3：18 个新来的人，12 个被领头的吸过去，6 个落到别处
    const comers = Array.from({ length: 18 }, (_, i) => ({
      fromX: 120 + rnd() * 1680,
      fromY: -60 - rnd() * 80,
      target: i % 3 === 2 ? Math.floor(rnd() * N_SONGS) : leader,
      delay: i / 18,
      bend: (rnd() - 0.5) * 500,
    }));
    return { firstClicks, comers };
  }, [leader]);

  // 计数器（counting / sim 用）
  const counters = React.useMemo(() => {
    const c = new Array(N_SONGS).fill(0);
    if (mode === "counting") {
      const rnd = mulberry32(77);
      for (let i = 0; i < N_SONGS; i += 1) {
        const target = Math.round(2 + rnd() * 26);
        c[i] = Math.round(target * ease(span(p, 0.1 + rnd() * 0.3, 0.7 + rnd() * 0.3)));
      }
    } else if (mode === "digit") {
      c.fill(0);
      c[19] = Math.round(12 + 14 * ease(span(p, 0.1, 0.7)));
    } else if (mode === "sim1") {
      sim.firstClicks.forEach((song, k) => {
        if (span(p, 0.12 + k * 0.12, 0.13 + k * 0.12) > 0) c[song] += 1;
      });
    } else if (mode === "sim2") {
      sim.firstClicks.forEach((song) => (c[song] += 1));
      c[leader] = 1 + Math.round(2 * ease(span(p, 0.15, 0.7)));
    } else if (mode === "sim3") {
      sim.firstClicks.forEach((song) => (c[song] += 1));
      c[leader] = 3;
      sim.comers.forEach((cm) => {
        if (span(p, 0.1 + cm.delay * 0.75, 0.11 + cm.delay * 0.75) > 0 && p > 0.1 + cm.delay * 0.75 + 0.14) c[cm.target] += 1;
      });
    }
    return c;
  }, [mode, p, sim, leader]);

  // ---------- 柱高 ----------
  const inverted = finals.map((h) => 1.03 - h);
  const heights = (() => {
    if (mode === "sim4" || mode === "term") {
      const k = mode === "sim4" ? ease(span(p, 0.1, 0.9)) : 1;
      return appeal.map((a, i) => {
        const base = 0.1 + a * 0.22;
        const target = i === leader ? 1 : base + (sim.firstClicks.includes(i) ? 0.08 : 0);
        return lerp(base * 0.6, target, k);
      });
    }
    if (mode === "tap") {
      const top = finals.indexOf(Math.max(...finals));
      const k = ease(span(p, 0.42, 0.62));
      return finals.map((h, i) => (i === top ? Math.min(1, h + 0.0001) * (1 + 0.0 * k) : h * (1 - 0.06 * k)));
    }
    if (mode === "fresh") return finals;
    if (mode === "flip") return finals;
    if (mode === "fakebadge") return finals;
    if (mode === "selffulfil") {
      const k = ease(span(p, 0.1, 0.9));
      return finals.map((h, i) => (i === worstSong ? lerp(h, 0.92, k) : lerp(h, inverted[i], 0.62 * k)));
    }
    if (mode === "recover" || mode === "glide") {
      const k = mode === "recover" ? ease(span(p, 0.1, 0.9)) : 1;
      return finals.map((h, i) => {
        const fallen = i === worstSong ? 0.92 : lerp(h, inverted[i], 0.62);
        return best5.includes(i) ? lerp(fallen, Math.max(fallen, h * 0.95), k) : fallen;
      });
    }
    return finals;
  })();

  const isDots = mode === "counting" || mode === "digit" || mode === "sim0" || mode === "sim1" || mode === "sim2" || mode === "sim3" || mode === "alone" || mode === "edge" || mode === "missed" || mode === "freeze";
  const morph = mode === "sim4" ? ease(span(p, 0.0, 0.35)) : isDots ? 0 : 1;
  const grow = mode === "sim4" ? ease(span(p, 0.1, 0.9)) : isDots ? 0 : 1;

  // ---------- 相机 ----------
  const cam = (() => {
    if (mode === "counting") return { sc: 1 + 0.06 * p, ox: 0, oy: 0, origin: "960px 520px" };
    if (mode === "digit") {
      const d = dotPos(19, PX, PY, PW, PH);
      const k = ease(span(p, 0, 0.5));
      const sc = lerp(1.1, 2.6, k);
      return { sc, ox: lerp(0, 960 - d.cx, k), oy: lerp(0, 470 - d.cy, k), origin: `${d.cx}px ${d.cy}px` };
    }
    // 呼吸镜：极慢的推进 + 轻微上浮。原来是 2 倍放大横扫 1040px，实测镜内帧间差 40.6——
    // 全片最高，是 B1（8 块板掠过，17.97）的 2.3 倍。呼吸镜该是全片最安静的位置，
    // 不该比倒置实验（Q5 的 4.27）晃十倍。
    if (mode === "glide") return { sc: lerp(1.88, 2.04, ease(p)), ox: lerp(-70, 70, ease(p)), oy: 220, origin: "960px 540px" };
    if (mode === "alone" || mode === "edge" || mode === "missed" || mode === "freeze") {
      const d = dotPos(27, PX, PY, PW, PH);
      const sc = mode === "alone" ? lerp(2.4, 1.9, ease(p)) : 1.9;
      return { sc, ox: 960 - d.cx, oy: 520 - d.cy, origin: `${d.cx}px ${d.cy}px` };
    }
    if (mode === "fresh") return { sc: 1, ox: lerp(700, 0, ease(span(p, 0, 0.45))), oy: 0, origin: "960px 540px" };
    return { sc: 1, ox: 0, oy: 0, origin: "960px 540px" };
  })();

  // flip：绕水平轴翻 180°，翻到一半换成倒过来的柱高
  const flipK = mode === "flip" ? ease(span(p, 0.15, 0.75)) : 0;
  const flipHeights = mode === "flip" ? (flipK > 0.5 ? inverted : finals) : heights;
  const panelTransform = mode === "flip" ? `perspective(2200px) rotateX(${180 * flipK}deg)` : undefined;

  // ---------- 徽章 / 高亮 / 圈 ----------
  const badges: Badge[] = (() => {
    if (mode === "fakebadge" || mode === "selffulfil" || mode === "recover" || mode === "glide") {
      return [{ song: worstSong, text: badge || "「第 1 名」", color: C.gold, p: mode === "fakebadge" ? span(p, 0.3, 0.6) : 1, fake: true }];
    }
    return [];
  })();
  const highlight = (() => {
    if (mode === "sim2" || mode === "sim3" || mode === "sim4") return { song: leader, color: C.gold, glow: 0.6 + 0.6 * ease(span(p, 0.2, 0.8)) };
    if (mode === "term") return { song: leader, color: C.gold, glow: 1 };
    if (mode === "tap") {
      const top = finals.indexOf(Math.max(...finals));
      return { song: top, color: C.gold, glow: 0.6 + 1.4 * Math.sin(Math.PI * span(p, 0.42, 0.75)) };
    }
    if (mode === "digit") return { song: 19, color: C.ink, glow: 0.8 };
    if (mode === "fakebadge" || mode === "selffulfil") return { song: worstSong, color: C.gold, glow: 0.8 };
    return null;
  })();
  const rings = (() => {
    if (mode === "recover" || mode === "glide") return best5.map((song, k) => ({ song, color: C.gold, p: mode === "recover" ? span(p, 0.1 + k * 0.08, 0.3 + k * 0.08) : 1 }));
    if (mode === "edge") return [{ song: 27, color: C.gold, p: ease(span(p, 0.15, 0.7)), r: 16 }];
    return [];
  })();
  const dim = (() => {
    // 落点四镜：板面不能压成一团黑（实测整帧边缘占比 0.0006，观众看到的是空屏而不是"一万个世界"）。
    // 底噪抬到 0.32 —— 一万个点要看得见，金点才谈得上"只有你亮着"。
    // freeze 整板还要再被 boardDraw 压暗一层，这里给它更高的底噪，压完仍看得见。
    if (mode === "freeze") return new Array(N_SONGS).fill(0.46).map((v, i) => (i === 27 ? 1 : v));
    if (mode === "alone" || mode === "edge" || mode === "missed") return new Array(N_SONGS).fill(0.32).map((v, i) => (i === 27 ? 0.9 : v));
    if (mode === "digit") return new Array(N_SONGS).fill(0.3).map((v, i) => (i === 19 ? 1 : v));
    return undefined;
  })();

  // 点击：sim1 的随机落点、missed 的落在旁边、tap 落在最高柱上
  const clicks: { x: number; y: number; k: number }[] = (() => {
    const out: { x: number; y: number; k: number }[] = [];
    if (mode === "sim1") {
      sim.firstClicks.forEach((song, i) => {
        const d = dotPos(song, PX, PY, PW, PH);
        out.push({ x: d.cx, y: d.cy, k: span(p, 0.12 + i * 0.12, 0.3 + i * 0.12) });
      });
    } else if (mode === "sim2") {
      for (let i = 0; i < 2; i += 1) {
        const d = dotPos(leader, PX, PY, PW, PH);
        out.push({ x: d.cx, y: d.cy, k: span(p, 0.2 + i * 0.25, 0.4 + i * 0.25) });
      }
    } else if (mode === "missed") {
      [26, 28, 19].forEach((song, i) => {
        const d = dotPos(song, PX, PY, PW, PH);
        out.push({ x: d.cx, y: d.cy, k: span(p, 0.15 + i * 0.2, 0.38 + i * 0.2) });
      });
    } else if (mode === "tap") {
      const top = finals.indexOf(Math.max(...finals));
      const b = barPos(top, PX, PY, PW, PH);
      out.push({ x: b.cx, y: b.baseY - b.maxH * finals[top], k: span(p, 0.3, 0.55) });
    }
    return out;
  })();

  // sim3 的新来者：从板顶弯向领头的那首
  const comerDots =
    mode === "sim3"
      ? sim.comers.map((cm) => {
          const k = ease(span(p, 0.1 + cm.delay * 0.75, 0.24 + cm.delay * 0.75));
          if (k <= 0 || k >= 1) return null;
          const d = dotPos(cm.target, PX, PY, PW, PH);
          const mx = (cm.fromX + d.cx) / 2 + cm.bend;
          const my = (cm.fromY + d.cy) / 2 - 120;
          const x = (1 - k) * (1 - k) * cm.fromX + 2 * (1 - k) * k * mx + k * k * d.cx;
          const y = (1 - k) * (1 - k) * cm.fromY + 2 * (1 - k) * k * my + k * k * d.cy;
          return { x, y, k };
        })
      : [];

  // digit 旁边一闪而过的两个影子：门口的队、手机上的销量
  const ghostQueue = mode === "digit" ? Math.sin(Math.PI * span(p, 0.34, 0.56)) : 0;
  const ghostPhone = mode === "digit" ? Math.sin(Math.PI * span(p, 0.6, 0.84)) : 0;

  const frozen = mode === "freeze" ? ease(span(p, 0.25, 0.95)) : 0;
  const panelOpacity = mode === "alone" ? 0.72 : mode === "edge" || mode === "missed" ? 0.82 : mode === "freeze" ? 0.8 : 1;
  const termP = mode === "term" ? ease(span(p, 0.08, 0.45)) : 0;
  const term2P = mode === "term" && label2 ? ease(span(p, 0.3, 0.7)) : 0;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: "50%", top: "50%", width: W, height: H, transform: `translate(-50%, -50%) scale(${s})` }}>
        <TopLight cx={960} cy={140} strength={mode === "alone" || mode === "edge" || mode === "missed" ? 0.35 : 1} />

        <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: `translate(${cam.ox}px, ${cam.oy}px) scale(${cam.sc})`, transformOrigin: cam.origin }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: panelTransform, transformOrigin: `${PX + PW / 2}px ${PY + PH / 2}px` }}>
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
              <Panel
                x={PX}
                y={PY}
                w={PW}
                h={PH}
                heights={flipHeights}
                morph={morph}
                grow={grow}
                opacity={panelOpacity}
                tone="warm"
                counters={isDots && mode !== "alone" && mode !== "edge" && mode !== "missed" && mode !== "freeze" ? counters : null}
                counterSize={20}
                badges={badges}
                highlight={highlight}
                rings={rings}
                dim={dim}
                frozen={frozen}
                ghost={mode === "fakebadge" ? { heights: finals.map((_, i) => (i === worstSong ? 0.92 : 0)), p: ease(span(p, 0.35, 0.7)) } : null}
                shimmer={mode === "fresh" || mode === "tap" || mode === "glide" ? 1 : 0}
                seed={3 + frame * 0.03}
              />
              {/* 点击的圈 */}
              {clicks.map((c, i) =>
                c.k <= 0 ? null : (
                  <g key={i}>
                    <circle cx={c.x} cy={c.y} r={10 + 46 * c.k} fill="none" stroke={C.ink} strokeWidth={2} opacity={(1 - c.k) * 0.9} />
                    <circle cx={c.x} cy={c.y} r={4 + 14 * c.k} fill="none" stroke={C.gold} strokeWidth={1.5} opacity={(1 - c.k) * 0.9} />
                  </g>
                ),
              )}
              {/* 新来的人 */}
              {comerDots.map((d, i) => (d ? <circle key={i} cx={d.x} cy={d.y} r={3.5} fill={C.ink} opacity={0.85} /> : null))}
            </svg>
          </div>
        </div>

        {/* digit：那颗光点旁边一闪而过的影子 */}
        {mode === "digit" ? (
          <>
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: 0.55 * ghostQueue }}>
              <g transform="translate(1180 400)" fill="none" stroke="rgba(226,236,248,0.9)" strokeWidth={2}>
                {[0, 1, 2, 3, 4].map((i) => (
                  <g key={i} transform={`translate(${i * 34} ${i * 4})`}>
                    <circle cx={0} cy={0} r={7} />
                    <path d="M-10 36 L-7 12 Q0 6 7 12 L10 36 Z" />
                  </g>
                ))}
                <rect x={-30} y={-40} width={30} height={80} rx={3} stroke="rgba(243,193,75,0.8)" />
              </g>
            </svg>
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, opacity: 0.55 * ghostPhone }}>
              <g transform="translate(560 420)" fill="none" stroke="rgba(226,236,248,0.9)" strokeWidth={2}>
                <rect x={0} y={0} width={70} height={130} rx={10} />
                <rect x={10} y={16} width={50} height={40} rx={3} />
                <line x1={12} y1={74} x2={58} y2={74} />
                <line x1={12} y1={88} x2={44} y2={88} stroke="rgba(243,193,75,0.9)" />
              </g>
            </svg>
          </>
        ) : null}

        {/* term：名词落下 */}
        {mode === "term" ? (
          <div style={{ position: "absolute", left: 0, right: 0, top: 300, textAlign: "center" }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 150, lineHeight: 1.1, letterSpacing: 10, color: C.ink, opacity: termP, transform: `translateY(${(1 - termP) * 30}px) scale(${0.96 + 0.04 * termP})`, textShadow: "0 0 80px rgba(243,193,75,0.3), 0 4px 30px rgba(0,0,0,0.9)" }}>
              {label}
            </div>
            <div style={{ fontFamily: FONT, fontSize: 26, letterSpacing: 14, color: C.dim, marginTop: 10, opacity: 0.85 * ease(span(p, 0.25, 0.55)) }}>{sub}</div>
            {label2 ? (
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 96, lineHeight: 1.1, letterSpacing: 8, color: C.gold, marginTop: 26, opacity: term2P, transform: `translateY(${(1 - term2P) * 24}px)`, textShadow: "0 0 60px rgba(243,193,75,0.35), 0 4px 30px rgba(0,0,0,0.9)" }}>
                {label2}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* 落点四镜（alone/edge/missed/freeze）：那颗没被点开的光点必须是主角。
            板上的点 dim 到 0.12 后几乎看不见（实测整帧边缘占比 0.0006），相机已把 27 号点放在屏幕 (960,520)，
            这里在屏幕空间叠一颗呼吸的光点：alone 缓慢明灭，freeze 跟着全板一起暗下去 */}
        {mode === "alone" || mode === "edge" || mode === "missed" || mode === "freeze" ? (
          (() => {
            const pulse = 0.62 + 0.2 * Math.sin(frame * 0.14);
            // freeze：全板定格、暗下去，但金点要留成一颗余烬（压到 0.38 会让整帧边缘掉到 0.0009，等于死帧）
            const dimmer = mode === "freeze" ? 1 - 0.3 * frozen : 1;
            const o = pulse * dimmer;
            const rr = 24;
            return (
              <>
                {/* 光晕：一团大范围的暖光，让"只剩它"有重量 */}
                <div
                  style={{
                    position: "absolute",
                    left: 960 - 150,
                    top: 520 - 150,
                    width: 300,
                    height: 300,
                    borderRadius: 150,
                    background:
                      "radial-gradient(circle, rgba(243,193,75,0.16) 0%, rgba(243,193,75,0.05) 46%, rgba(243,193,75,0) 70%)",
                    opacity: o,
                  }}
                />
                {/* 一圈细环：它是被点名的那颗 */}
                <div
                  style={{
                    position: "absolute",
                    left: 960 - 56,
                    top: 520 - 56,
                    width: 112,
                    height: 112,
                    borderRadius: 56,
                    border: "1.5px solid rgba(243,193,75,0.42)",
                    opacity: o * 0.9,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 960 - rr,
                    top: 520 - rr,
                    width: rr * 2,
                    height: rr * 2,
                    borderRadius: rr,
                    background:
                      "radial-gradient(circle at 38% 32%, rgba(255,240,205,0.98) 0%, rgba(243,193,75,0.9) 45%, rgba(122,92,28,0.6) 100%)",
                    boxShadow: "0 0 60px rgba(243,193,75,0.55), 0 0 180px rgba(243,193,75,0.25)",
                    opacity: o,
                  }}
                />
              </>
            );
          })()
        ) : null}

        <Note text={note} p={span(p, 0.2, 0.45)} />
      </div>
    </AbsoluteFill>
  );
};
