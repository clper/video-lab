import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp, mulberry32 } from "../common/random";
import { ease, span } from "../lib/boardDraw";

// 生活里的"下载数"：外卖的销量、视频的播放量、电影的票房。
// 每个图标下面挂着实验里同款的计数器——观众一眼认出"这就是那个数字"。图标是通用的形状，不出现任何平台和品牌。
// city：光柱化成夜里城市的一片灯（接在原理段之后）。

export type LifeMode = "city" | "takeout" | "video" | "movie";

type Props = {
  mode?: LifeMode;
  label?: string;
  value?: number;
  suffix?: string;
  decimals?: number;
};

const W = 1920;
const H = 1080;

const Icon: React.FC<{ kind: LifeMode; p: number; size?: number }> = ({ kind, p, size = 1 }) => {
  const draw = ease(p);
  const common = { fill: "none", stroke: C.ink, strokeWidth: 4, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - draw };
  return (
    <g transform={`scale(${size})`}>
      {kind === "takeout" ? (
        <>
          <path d="M-90 -40 L90 -40 L70 120 L-70 120 Z" {...common} />
          <path d="M-50 -40 Q-50 -120 0 -120 Q50 -120 50 -40" {...common} />
          <path d="M-40 20 L40 20" {...common} stroke={C.gold} />
        </>
      ) : null}
      {kind === "video" ? (
        <>
          <rect x={-120} y={-80} width={240} height={160} rx={16} {...common} />
          <path d="M-22 -40 L46 0 L-22 40 Z" {...common} stroke={C.gold} />
          <path d="M-120 110 L120 110" {...common} />
        </>
      ) : null}
      {kind === "movie" ? (
        <>
          <path d="M-130 -70 L130 -70 Q130 -40 160 -40 L160 40 Q130 40 130 70 L-130 70 Q-130 40 -160 40 L-160 -40 Q-130 -40 -130 -70 Z" {...common} />
          <path d="M20 -70 L20 70" {...common} strokeDasharray="0.03 0.03" stroke={C.dim} />
          <path d="M-100 0 L-20 0" {...common} stroke={C.gold} />
        </>
      ) : null}
    </g>
  );
};

export const LifeCounters: React.FC<Props> = ({ mode = "takeout", label = "", value = 0, suffix = "", decimals = 0 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { s } = useStage();
  const p = clamp(frame / Math.max(1, durationInFrames - 1));

  // city：22 栋楼，窗子一扇扇亮起来
  const city = React.useMemo(() => {
    const rnd = mulberry32(20261028);
    return Array.from({ length: 22 }, (_, i) => {
      const bw = 60 + rnd() * 90;
      const bh = 160 + rnd() * 420;
      const bx = -20 + i * 90 + rnd() * 30;
      const cols = Math.max(2, Math.floor(bw / 22));
      const rows = Math.max(3, Math.floor(bh / 28));
      const wins = Array.from({ length: cols * rows }, (_, k) => ({ c: k % cols, r: Math.floor(k / cols), on: rnd() > 0.42, delay: rnd(), warm: rnd() > 0.3 }));
      return { bx, bw, bh, cols, rows, wins };
    });
  }, []);

  // 前面几镜的图标留在左边（小、淡）
  const earlier: LifeMode[] = mode === "video" ? ["takeout"] : mode === "movie" ? ["takeout", "video"] : [];

  const shown = value * ease(span(p, 0.18, 0.78));
  const text = decimals > 0 ? shown.toFixed(decimals) : Math.round(shown).toLocaleString("en-US");

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: "50%", top: "50%", width: W, height: H, transform: `translate(-50%, -50%) scale(${s})` }}>
        {mode === "city" ? (
          <>
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, #05070f 0%, #0b1024 55%, #1a1a30 100%)" }} />
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0 }}>
              {city.map((b, i) => {
                const rise = ease(span(p, 0.02 + (i % 7) * 0.03, 0.4 + (i % 7) * 0.03));
                const top = 900 - b.bh * rise;
                return (
                  <g key={i}>
                    <rect x={b.bx} y={top} width={b.bw} height={900 - top} fill="#070a14" stroke="rgba(255,255,255,0.05)" />
                    {b.wins.map((w, k) => {
                      if (!w.on) return null;
                      const on = ease(span(p, 0.3 + w.delay * 0.6, 0.38 + w.delay * 0.6)) * rise;
                      return <rect key={k} x={b.bx + 8 + w.c * 22} y={top + 14 + w.r * 28} width={10} height={14} fill={w.warm ? "rgba(255,205,130,0.9)" : "rgba(170,210,255,0.8)"} opacity={on * 0.9} />;
                    })}
                  </g>
                );
              })}
              <rect x={0} y={900} width={W} height={180} fill="#04050a" />
              {/* 地面上的反光 */}
              <rect x={0} y={900} width={W} height={60} fill="url(#lc-ref)" opacity={0.35 * ease(span(p, 0.4, 0.9))} />
              <defs>
                <linearGradient id="lc-ref" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="rgba(255,205,130,0.5)" />
                  <stop offset="1" stopColor="rgba(255,205,130,0)" />
                </linearGradient>
              </defs>
            </svg>
          </>
        ) : (
          <>
            <div style={{ position: "absolute", inset: 0, background: "radial-gradient(900px 600px at 50% 46%, rgba(255,232,180,0.10) 0%, rgba(255,232,180,0.03) 45%, rgba(0,0,0,0) 72%)" }} />
            <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
              {earlier.map((k, i) => (
                <g key={k} transform={`translate(${300 + i * 260} 420)`} opacity={0.28}>
                  <Icon kind={k} p={1} size={0.42} />
                </g>
              ))}
              <g transform="translate(960 430)">
                <Icon kind={mode} p={span(p, 0.02, 0.45)} />
              </g>
            </svg>
            {/* 实验里同款的计数器 */}
            <div style={{ position: "absolute", left: 0, right: 0, top: 600, textAlign: "center" }}>
              <div style={{ fontFamily: FONT, fontSize: 24, letterSpacing: 10, color: C.dim, opacity: ease(span(p, 0.15, 0.4)) }}>{label}</div>
              <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 14, marginTop: 8, opacity: ease(span(p, 0.15, 0.35)) }}>
                <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 120, lineHeight: 1, color: C.gold, fontVariantNumeric: "tabular-nums", textShadow: "0 0 50px rgba(243,193,75,0.3)" }}>{text}</div>
                {suffix ? <div style={{ fontFamily: FONT, fontSize: 44, color: C.ink }}>{suffix}</div> : null}
              </div>
              <div style={{ margin: "26px auto 0", width: 420, height: 2, background: "rgba(255,255,255,0.10)", overflow: "hidden" }}>
                <div style={{ width: `${100 * ease(span(p, 0.2, 0.8))}%`, height: "100%", background: `linear-gradient(90deg, ${C.gold}, ${C.cyan})` }} />
              </div>
            </div>
          </>
        )}
      </div>
    </AbsoluteFill>
  );
};
