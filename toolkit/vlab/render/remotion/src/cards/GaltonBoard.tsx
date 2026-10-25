import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { mulberry32, clamp } from "../common/random";

// 高尔顿板：一块钉板 + 一堆珠子。
// 它是 007 的画面主力，也是补 006 那两个短板的地方：
//   1. motion —— 几千颗珠子在下落，画面天生就在动（006 全片基线只有 0.74）；
//   2. 光影   —— 一束顶光只照板子，钉子按离中心的远近做景深（越远越虚）。
// 同一块板贯穿全片：片名卡里它是空的（那颗金珠悬在顶端），定格时它已经堆好了。

export type BoardMode = "board" | "one" | "rain" | "pile" | "extremes" | "final";

type Props = {
  mode?: BoardMode;
  /** 钉板层数（= 抛硬币次数） */
  rows?: number;
  /** rain / pile 一共放多少颗 */
  pellets?: number;
  /** 每帧生成几颗（控制雨的密度） */
  rate?: number;
  /** one 模式走几层 */
  travel?: number;
  kicker?: string;
  note?: string;
  /** 屏上的字 */
  label?: string;
  seed?: number;
};

const CX = 960;
const DX = 34;
const ROW0_Y = 286;
const DY = 34;
const FP = 3; // 每层几帧
const Y_START = ROW0_Y - 74;
const BIN_BASE = 902;
const BAR_MAX = 196;
const TOTAL = 900; // extremes / final 用的总珠数

const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

/** 二项分布概率，用来给柱高定标（不然雨还没下完柱子就顶到天花板） */
function binomProbs(n: number): number[] {
  const out: number[] = [1];
  for (let i = 1; i <= n; i += 1) {
    const next = new Array(out.length + 1).fill(0);
    for (let k = 0; k < out.length; k += 1) {
      next[k] += out[k] * 0.5;
      next[k + 1] += out[k] * 0.5;
    }
    out.length = 0;
    out.push(...next);
  }
  return out;
}

export const GaltonBoard: React.FC<Props> = ({
  mode = "board",
  rows = 12,
  pellets = 900,
  rate = 9,
  travel = 5,
  kicker = "01 · 板　THE BOARD",
  note = "每一层都是一次抛硬币：左或右，各一半。",
  label = "",
  seed = 7,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();

  const n = rows;
  const flight = n * FP + 8;

  // 珠子表：确定性随机，同一帧永远同一画面（禁止 Math.random）
  const table = React.useMemo(() => {
    const rnd = mulberry32(seed * 7919 + 13);
    const list: { start: number; steps: number[]; bin: number }[] = [];
    for (let i = 0; i < pellets; i += 1) {
      const steps: number[] = [];
      for (let r = 0; r < n; r += 1) steps.push(rnd() < 0.5 ? 0 : 1);
      list.push({ start: 6 + Math.floor(i / rate), steps, bin: steps.reduce((a, b) => a + b, 0) });
    }
    return list;
  }, [pellets, rate, n, seed]);

  const probs = React.useMemo(() => binomProbs(n), [n]);
  const maxProb = Math.max(...probs);

  const binX = (k: number) => CX + (k - n / 2) * DX;
  const rowY = (r: number) => ROW0_Y + r * DY;
  const xAtRow = (steps: number[], r: number) => {
    const rights = steps.slice(0, r).reduce((a, b) => a + b, 0);
    return CX + (rights - r / 2) * DX;
  };

  // 已落袋的珠子数（按槽统计）
  const landed = React.useMemo(() => {
    const counts = new Array(n + 1).fill(0);
    if (mode === "rain" || mode === "pile") {
      for (const p of table) {
        if (frame >= p.start + flight) counts[p.bin] += 1;
      }
    }
    return counts;
  }, [table, frame, flight, n, mode]);

  const landedTotal = landed.reduce((a, b) => a + b, 0);
  const scale = Math.max(1, (pellets * maxProb) / 1.0);

  // extremes / final：用固定分布，按进度长出来
  const revealP =
    mode === "extremes" || mode === "final"
      ? ease(clamp((frame - fps * 0.1) / (fps * Math.max(0.6, durationInFrames / fps - 0.3))))
      : 0;

  const barH = (k: number) => {
    if (mode === "rain" || mode === "pile") return (BAR_MAX * landed[k]) / scale;
    if (mode === "extremes" || mode === "final") return BAR_MAX * (probs[k] / maxProb) * revealP;
    return 0;
  };

  // 曲线：只有堆到一定程度才出现
  const curveP =
    mode === "pile"
      ? clamp((frame - fps * 1.1) / (fps * 1.6))
      : mode === "extremes" || mode === "final"
        ? clamp((revealP - 0.35) / 0.4)
        : 0;

  // 钉板浮现
  const boardP = ease(clamp((frame - fps * 0.12) / (fps * 0.8)));
  const rowsShown = Math.round(n * boardP);

  // 在空中的珠子
  const flying =
    mode === "rain" || mode === "pile"
      ? table.filter((p) => frame >= p.start && frame < p.start + flight)
      : [];

  // one / final：那颗金珠
  const beadP = mode === "one" ? clamp((frame - fps * 0.15) / (fps * 0.5)) : 1;
  const oneT = (frame - Math.round(fps * 0.15)) / FP;
  const oneRow = clamp(Math.floor(oneT), 0, travel);
  const oneU = clamp(oneT - oneRow, 0, 1);
  const oneSteps = React.useMemo(() => {
    const rnd = mulberry32(seed * 104729 + 3);
    return Array.from({ length: n }, () => (rnd() < 0.5 ? 0 : 1));
  }, [n, seed]);
  const oneX =
    mode === "one"
      ? xAtRow(oneSteps, oneRow) * (1 - oneU) + xAtRow(oneSteps, oneRow + 1) * oneU
      : CX;
  const oneY = mode === "one" ? Y_START + clamp(oneT, 0, travel) * DY : Y_START;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: 1920,
          height: 1080,
          transform: `translate(-50%, -50%) scale(${s})`,
        }}
      >
        {/* 一束顶光：只照板子，别的地方压暗（007 的"单点光"） */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            background:
              "radial-gradient(720px 520px at 50% 12%, rgba(255,232,180,0.16) 0%, rgba(255,232,180,0.05) 42%, rgba(0,0,0,0) 72%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            background:
              "radial-gradient(1100px 780px at 50% 52%, rgba(0,0,0,0) 46%, rgba(0,0,0,0.62) 100%)",
            pointerEvents: "none",
          }}
        />

        {/* 玻璃罩 */}
        <div
          style={{
            position: "absolute",
            left: 560,
            top: 200,
            width: 800,
            height: 730,
            borderRadius: 10,
            border: "1px solid rgba(226,236,248,0.10)",
            background:
              "linear-gradient(180deg, rgba(226,236,248,0.045) 0%, rgba(226,236,248,0.012) 38%, rgba(226,236,248,0) 100%)",
            opacity: boardP,
          }}
        />
        {/* 玻璃反光：一道窄的斜光，扫过就算，不做常驻灰带 */}
        <div
          style={{
            position: "absolute",
            left: 560 + 120 + 320 * clamp((frame - fps * 0.4) / (fps * 2.2)),
            top: 200,
            width: 120,
            height: 730,
            background:
              "linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.055) 50%, rgba(255,255,255,0) 100%)",
            opacity: boardP * 0.9,
          }}
        />

        {/* 钉子：离中心越远越虚（景深）。要亮到能压住背景星尘，不然板上只剩珠子 */}
        {Array.from({ length: n }, (_, r) =>
          r < rowsShown
            ? Array.from({ length: r + 1 }, (_, j) => {
                const x = CX + (j - r / 2) * DX;
                const y = rowY(r);
                const d = Math.abs(j - r / 2) / Math.max(1, n / 2);
                const o = (0.92 - 0.38 * d) * boardP;
                const rr = 5.0 - 1.8 * d;
                return (
                  <div
                    key={`${r}-${j}`}
                    style={{
                      position: "absolute",
                      left: x - rr,
                      top: y - rr,
                      width: rr * 2,
                      height: rr * 2,
                      borderRadius: rr,
                      background: d < 0.35 ? "#ffedc4" : "#d7e1f2",
                      opacity: o,
                      filter: `blur(${d > 0.6 ? 1.2 : 0}px)`,
                      boxShadow: d < 0.3 ? "0 0 12px rgba(255,236,190,0.55)" : "0 0 6px rgba(200,214,240,0.22)",
                    }}
                  />
                );
              })
            : null,
        )}

        {/* 柱子 */}
        {Array.from({ length: n + 1 }, (_, k) => {
          const h = barH(k);
          if (h < 0.8) return null;
          const extreme = k <= 1 || k >= n - 1;
          const isRed = (mode === "extremes" || mode === "final") && extreme;
          return (
            <div
              key={`bar-${k}`}
              style={{
                position: "absolute",
                left: binX(k) - DX / 2 + 3,
                top: BIN_BASE - h,
                width: DX - 6,
                height: h,
                background: isRed
                  ? "linear-gradient(180deg, rgba(255,91,91,0.95), rgba(255,91,91,0.42))"
                  : "linear-gradient(180deg, rgba(243,193,75,0.95), rgba(243,193,75,0.30))",
                opacity: isRed ? 0.95 : mode === "extremes" || mode === "final" ? 0.42 : 0.9,
                boxShadow: isRed ? "0 0 22px rgba(255,91,91,0.30)" : "none",
              }}
            />
          );
        })}

        {/* 钟形曲线 */}
        {curveP > 0.02 ? (
          <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
            <polyline
              points={Array.from({ length: n + 1 }, (_, k) => `${binX(k)},${BIN_BASE - barH(k)}`).join(" ")}
              fill="none"
              stroke={C.gold}
              strokeWidth={2.4}
              strokeLinejoin="round"
              opacity={0.85 * curveP}
            />
          </svg>
        ) : null}

        {/* 槽底 */}
        <div
          style={{
            position: "absolute",
            left: binX(0) - DX / 2,
            top: BIN_BASE,
            width: (n + 1) * DX,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.30) 50%, rgba(255,255,255,0) 100%)",
            opacity: boardP,
          }}
        />

        {/* 珠雨 */}
        {flying.map((p, i) => {
          const t = frame - p.start;
          const r = clamp(Math.floor(t / FP), 0, n);
          const u = clamp((t % FP) / FP, 0, 1);
          const x = xAtRow(p.steps, r) * (1 - u) + xAtRow(p.steps, r + 1) * u;
          const y =
            t <= n * FP
              ? Y_START + t * (DY / FP)
              : Y_START + n * DY + (t - n * FP) * 17;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x - 5,
                top: Math.min(y, BIN_BASE - 6),
                width: 10,
                height: 10,
                borderRadius: 5,
                background: "radial-gradient(circle at 34% 30%, #fff6dc 0%, #e8c877 52%, #8a6a24 100%)",
                opacity: 0.95,
              }}
            />
          );
        })}

        {/* 那颗金珠：one 是落下的过程，final 是回场定格（悬在顶端） */}
        {mode === "one" || mode === "final" ? (
          <>
            <div
              style={{
                position: "absolute",
                left: oneX - 14,
                top: oneY - 14,
                width: 28,
                height: 28,
                borderRadius: 14,
                background: "radial-gradient(circle at 34% 30%, #fff8e2 0%, #f3c14b 54%, #7a5c1c 100%)",
                boxShadow: "0 0 34px rgba(243,193,75,0.75)",
                opacity: beadP,
              }}
            />
            {/* 撞钉闪光 */}
            {mode === "one" && oneRow > 0 && oneU < 0.34 ? (
              <div
                style={{
                  position: "absolute",
                  left: xAtRow(oneSteps, oneRow) - 9,
                  top: rowY(oneRow) - 9,
                  width: 18,
                  height: 18,
                  borderRadius: 9,
                  background: "rgba(255,246,220,0.9)",
                  opacity: (1 - oneU / 0.34) * 0.9,
                }}
              />
            ) : null}
          </>
        ) : null}

        {/* 左上章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(boardP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>
            {kicker}
          </div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 右上：落了多少颗（画面自带读数的动感） */}
        {mode === "rain" || mode === "pile" ? (
          <div
            style={{
              position: "absolute",
              right: 130,
              top: 118,
              textAlign: "right",
              fontFamily: FONT,
              opacity: 0.9,
            }}
          >
            <div style={{ fontSize: 21, letterSpacing: 6, color: C.dim }}>已落</div>
            <div
              style={{
                fontSize: 64,
                fontWeight: 700,
                color: C.gold,
                fontVariantNumeric: "tabular-nums",
                lineHeight: 1.1,
              }}
            >
              {landedTotal}
            </div>
            <div style={{ fontSize: 20, letterSpacing: 4, color: "rgba(139,147,167,0.9)" }}>颗</div>
          </div>
        ) : null}

        {/* 屏上的字 */}
        {label ? (
          <div
            style={{
              position: "absolute",
              left: 148,
              top: 470,
              width: 420,
              fontFamily: FONT,
              fontSize: 46,
              fontWeight: 700,
              lineHeight: 1.45,
              letterSpacing: 3,
              color: C.ink,
              opacity: clamp((frame - fps * 0.5) / (fps * 0.5)),
              textShadow: "0 0 40px rgba(0,0,0,0.6)",
            }}
          >
            {label}
          </div>
        ) : null}

        {/* 右下出处小字 */}
        <div
          style={{
            position: "absolute",
            right: 130,
            bottom: 96,
            width: 520,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 20,
            lineHeight: 1.8,
            letterSpacing: 1,
            color: "rgba(139,147,167,0.68)",
            opacity: clamp(boardP * 1.6),
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
