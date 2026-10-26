// 一块"世界板"的画法：玻璃板 + 48 颗光点（8×6）→ 48 根光柱。
// WorldBoards（8 块总览）和 WorldBoard（单板特写）都用它，所以光点怎么变成光柱、徽章和圈长什么样，只写一遍。
//
// 坐标全在 1920×1080 的设计舞台里（common/stage.ts），外面统一缩放。
import React from "react";
import { C, FONT } from "../design/tokens";
import { clamp, lerp } from "../common/random";
import { N_SONGS } from "./worlds";

export const COLS = 8;
export const ROWS = 6;

export type Tone = "warm" | "cool" | "grey";
export type Ring = { song: number; color: string; p: number; r?: number };
export type Badge = { song: number; text: string; color: string; p: number; fake?: boolean };

export type PanelProps = {
  x: number;
  y: number;
  w: number;
  h: number;
  /** 每首歌的柱高 0..1 */
  heights?: number[];
  /** 0 = 光点阵列，1 = 光柱 */
  morph?: number;
  /** 柱子长到几成 */
  grow?: number;
  opacity?: number;
  tone?: Tone;
  /** 光点下面的数字（只在光点态显示） */
  counters?: number[] | null;
  counterSize?: number;
  /** 虚线轮廓：直觉里"好歌在哪都会火"的那条一样的曲线；shatter 让它碎开 */
  dashed?: { heights: number[]; p: number; shatter?: number } | null;
  rings?: Ring[];
  badges?: Badge[];
  /** 被点中的那首歌：发光 */
  highlight?: { song: number; color: string; glow?: number } | null;
  /** 每首歌的透明度倍数（压暗别的歌） */
  dim?: number[];
  /** 板子上方的小标签（对照组 / 质量排名） */
  label?: string;
  /** 角上的小编号 */
  tag?: string;
  /** 0..1：冻住（去色、变暗） */
  frozen?: number;
  /** 虚影柱（倒置实验里"显示出来的人气"）：按歌给高度，画成空心虚线柱 */
  ghost?: { heights: number[]; p: number } | null;
  /** 一种随机抖动，用来让光柱微微呼吸 */
  shimmer?: number;
  seed?: number;
};

const toneColors = (tone: Tone) => {
  if (tone === "cool") return { hi: C.cyan, mid: "#9fe8df", lo: "#3f7a78", glass: "rgba(73,227,209,0.09)", edge: "rgba(73,227,209,0.30)" };
  if (tone === "grey") return { hi: "#c9ced8", mid: "#8d95a6", lo: "#4b5262", glass: "rgba(200,210,230,0.05)", edge: "rgba(200,210,230,0.18)" };
  return { hi: C.gold, mid: "#e9e1cf", lo: "#5b6478", glass: "rgba(226,236,248,0.06)", edge: "rgba(226,236,248,0.22)" };
};

export const barColor = (h: number, tone: Tone): string => {
  const t = toneColors(tone);
  if (h > 0.72) return t.hi;
  if (h > 0.34) return t.mid;
  return t.lo;
};

/** 光点在板上的位置（阵列态） */
export const dotPos = (i: number, x: number, y: number, w: number, h: number) => {
  const cellW = (w - 40) / COLS;
  const cellH = (h - 64) / ROWS;
  return { cx: x + 20 + cellW * ((i % COLS) + 0.5), cy: y + 30 + cellH * (Math.floor(i / COLS) + 0.5), cellH };
};

/** 光柱的底座位置（柱态） */
export const barPos = (i: number, x: number, y: number, w: number, h: number) => {
  const slot = (w - 40) / N_SONGS;
  return { cx: x + 20 + slot * (i + 0.5), baseY: y + h - 26, slot, maxH: h - 70 };
};

export const Panel: React.FC<PanelProps> = ({
  x,
  y,
  w,
  h,
  heights,
  morph = 0,
  grow = 0,
  opacity = 1,
  tone = "warm",
  counters = null,
  counterSize = 13,
  dashed = null,
  rings = [],
  badges = [],
  highlight = null,
  dim,
  label,
  tag,
  frozen = 0,
  ghost = null,
  shimmer = 0,
  seed = 1,
}) => {
  const t = toneColors(tone);
  const hs = heights ?? new Array(N_SONGS).fill(0.2);
  const id = `pnl-${Math.round(x)}-${Math.round(y)}-${Math.round(w)}`;
  const base = barPos(0, x, y, w, h);
  const barW = Math.max(3.2, base.slot * 0.62);

  const items = Array.from({ length: N_SONGS }, (_, i) => {
    const d = dotPos(i, x, y, w, h);
    const b = barPos(i, x, y, w, h);
    const sh = shimmer ? 1 + shimmer * 0.06 * Math.sin(seed * 1.7 + i * 2.3) : 1;
    const hgt = Math.max(barW, b.maxH * clamp(hs[i]) * clamp(grow) * sh);
    const cx = lerp(d.cx, b.cx, morph);
    const cyBottom = lerp(d.cy + 5, b.baseY, morph);
    const width = lerp(10, barW, morph);
    const height = lerp(10, hgt, morph);
    const col = morph < 0.5 ? t.mid : barColor(hs[i], tone);
    const o = (dim ? dim[i] : 1) * (morph < 0.5 ? 0.82 : 0.92);
    const isHi = highlight && highlight.song === i;
    return { i, cx, top: cyBottom - height, width, height, col, o, isHi, d, b };
  });

  const dashSegs = dashed
    ? Array.from({ length: N_SONGS - 1 }, (_, i) => {
        const a = barPos(i, x, y, w, h);
        const b = barPos(i + 1, x, y, w, h);
        const ya = a.baseY - a.maxH * clamp(dashed.heights[i]);
        const yb = b.baseY - b.maxH * clamp(dashed.heights[i + 1]);
        const shown = clamp(dashed.p * (N_SONGS - 1) - i);
        const sh = dashed.shatter ?? 0;
        const ang = Math.sin(seed * 3.1 + i * 12.9) * 1.2;
        const dx = Math.sin(i * 7.3 + seed) * 70 * sh;
        const dy = -(30 + Math.abs(Math.cos(i * 5.1)) * 80) * sh;
        return { i, xa: a.cx, ya, xb: b.cx, yb, shown, sh, ang, dx, dy };
      })
    : [];

  return (
    <g style={{ opacity, filter: frozen > 0 ? `grayscale(${clamp(frozen)}) brightness(${1 - 0.55 * clamp(frozen)})` : undefined }}>
      <defs>
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={t.glass} />
          <stop offset="0.5" stopColor="rgba(226,236,248,0.015)" />
          <stop offset="1" stopColor="rgba(0,0,0,0)" />
        </linearGradient>
      </defs>
      {/* 玻璃板 */}
      <rect x={x} y={y} width={w} height={h} rx={10} fill={`url(#${id}-g)`} stroke={t.edge} strokeWidth={1} />
      {/* 板顶一条亮边 */}
      <line x1={x + 18} y1={y + 1} x2={x + w - 18} y2={y + 1} stroke="rgba(255,255,255,0.18)" strokeWidth={1} />

      {label ? (
        <text x={x + w / 2} y={y - 18} textAnchor="middle" fontFamily={FONT} fontSize={20} letterSpacing={4} fill={tone === "cool" ? C.cyan : C.gold} opacity={0.9}>
          {label}
        </text>
      ) : null}
      {tag ? (
        <text x={x + w - 14} y={y + 20} textAnchor="end" fontFamily={FONT} fontSize={13} letterSpacing={2} fill={C.dim} opacity={0.7}>
          {tag}
        </text>
      ) : null}

      {/* 虚影柱：显示出来的、假的人气 */}
      {ghost
        ? items.map((it) => {
            const gh = it.b.maxH * clamp(ghost.heights[it.i]) * clamp(ghost.p);
            if (gh < 2) return null;
            return (
              <rect
                key={`g${it.i}`}
                x={it.b.cx - barW / 2}
                y={it.b.baseY - gh}
                width={barW}
                height={gh}
                rx={Math.min(2.5, barW / 2)}
                fill="none"
                stroke="rgba(243,193,75,0.45)"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
            );
          })
        : null}

      {/* 48 颗光点 / 光柱 */}
      {items.map((it) => (
        <rect
          key={it.i}
          x={it.cx - it.width / 2}
          y={it.top}
          width={it.width}
          height={it.height}
          rx={Math.min(5, it.width / 2)}
          fill={it.isHi ? highlight!.color : it.col}
          opacity={it.isHi ? 1 : it.o}
          style={it.isHi ? { filter: `drop-shadow(0 0 ${8 + 10 * (highlight!.glow ?? 1)}px ${highlight!.color})` } : undefined}
        />
      ))}

      {/* 光点下的数字 */}
      {counters && morph < 0.5
        ? items.map((it) => (
            <text
              key={`c${it.i}`}
              x={it.d.cx}
              y={it.d.cy + it.d.cellH * 0.34 + counterSize * 0.4}
              textAnchor="middle"
              fontFamily={FONT}
              fontSize={counterSize}
              fill={counters[it.i] > 0 ? C.ink : C.dim}
              opacity={(1 - morph * 2) * (counters[it.i] > 0 ? 0.95 : 0.55)}
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {counters[it.i]}
            </text>
          ))
        : null}

      {/* 虚线轮廓 */}
      {dashSegs.map((s) =>
        s.shown <= 0 ? null : (
          <line
            key={`d${s.i}`}
            x1={s.xa}
            y1={s.ya}
            x2={lerp(s.xa, s.xb, s.shown)}
            y2={lerp(s.ya, s.yb, s.shown)}
            stroke="rgba(243,193,75,0.75)"
            strokeWidth={2}
            strokeDasharray="7 6"
            opacity={1 - s.sh}
            transform={s.sh > 0 ? `translate(${s.dx} ${s.dy}) rotate(${s.ang * 40 * s.sh} ${s.xa} ${s.ya})` : undefined}
          />
        ),
      )}

      {/* 圈：最好的（金）/ 最差的（灰） */}
      {rings.map((r, k) => {
        if (r.p <= 0) return null;
        const it = items[r.song];
        const rr = (r.r ?? 11) * (0.6 + 0.4 * clamp(r.p));
        return (
          <circle
            key={`r${k}`}
            cx={it.cx}
            cy={it.top}
            r={rr}
            fill="none"
            stroke={r.color}
            strokeWidth={2}
            opacity={clamp(r.p)}
            style={{ filter: `drop-shadow(0 0 6px ${r.color})` }}
          />
        );
      })}

      {/* 徽章：第 1 名 / 第 40 名 */}
      {badges.map((bd, k) => {
        if (bd.p <= 0) return null;
        const it = items[bd.song];
        const p = clamp(bd.p);
        const pop = 0.7 + 0.3 * (1 - Math.pow(1 - p, 3));
        const bw = 24 + bd.text.length * 17;
        const bx = Math.min(x + w - bw / 2 - 8, Math.max(x + bw / 2 + 8, it.cx));
        const by = it.top - 30;
        return (
          <g key={`b${k}`} opacity={p} transform={`translate(${bx} ${by}) scale(${pop})`}>
            <line x1={it.cx - bx} y1={14} x2={it.cx - bx} y2={28} stroke={bd.color} strokeWidth={1.5} opacity={0.8} />
            <rect x={-bw / 2} y={-16} width={bw} height={30} rx={15} fill={bd.fake ? "rgba(6,7,13,0.9)" : bd.color} stroke={bd.color} strokeWidth={bd.fake ? 1.5 : 0} strokeDasharray={bd.fake ? "4 3" : undefined} />
            <text x={0} y={5} textAnchor="middle" fontFamily={FONT} fontSize={17} fontWeight={700} letterSpacing={1} fill={bd.fake ? bd.color : "#06070d"}>
              {bd.text}
            </text>
          </g>
        );
      })}
    </g>
  );
};

/** 右下角的小字（出处、简化说明）。横屏字幕在 y≈980，它放在字幕条右侧上方一点 */
export const Note: React.FC<{ text?: string; p?: number }> = ({ text, p = 1 }) =>
  text ? (
    <div
      style={{
        position: "absolute",
        right: 96,
        top: 884,
        fontFamily: FONT,
        fontSize: 20,
        letterSpacing: 2,
        color: "rgba(160,168,188,0.82)",
        opacity: clamp(p),
        textShadow: "0 1px 12px rgba(0,0,0,0.8)",
      }}
    >
      {text}
    </div>
  ) : null;

/** 顶光：只照板子那一片，别处压暗 */
export const TopLight: React.FC<{ cx?: number; cy?: number; strength?: number }> = ({ cx = 960, cy = 120, strength = 1 }) => (
  <>
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: `radial-gradient(900px 620px at ${cx}px ${cy}px, rgba(255,232,180,${0.15 * strength}) 0%, rgba(255,232,180,${0.04 * strength}) 42%, rgba(0,0,0,0) 72%)`,
      }}
    />
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "radial-gradient(1200px 820px at 50% 54%, rgba(0,0,0,0) 46%, rgba(0,0,0,0.58) 100%)",
      }}
    />
  </>
);

export const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);
export const span = (p: number, a: number, b: number) => clamp((p - a) / Math.max(1e-6, b - a));
