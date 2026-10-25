import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp, mulberry32 } from "../common/random";

// 海：落点那 30 秒的主画面。
//   每一个浪头都会落下（回归均值），但海不会变成平静的水面（分布不会消失）——
//   这句话是全片的落点，画面必须自己演出来，不能只靠字幕念。
// 浪吞掉的字：骄傲 / 松懈 / 努力 / 改正 —— 观众看完记住的是"那两个字被浪带走了"。

export type WaveMode = "crest" | "sea" | "fall" | "trough" | "calm" | "line";

type Props = {
  mode?: WaveMode;
  /** 被浪吞掉的字（可空） */
  word?: string;
  word2?: string;
  kicker?: string;
  note?: string;
  label?: string;
  /** calm 时那颗金珠要不要升起来（回场） */
  bead?: boolean;
};

const W = 1920;
const H = 1080;
const STEP = 24;

const wavePath = (
  baseY: number,
  amp: number,
  phase: number,
  bump: number,
  k: number,
) => {
  const pts: string[] = [];
  for (let x = 0; x <= W; x += STEP) {
    const y =
      baseY +
      amp * Math.sin((x / W) * k * Math.PI * 2 + phase) +
      bump * Math.exp(-Math.pow((x - 960) / 340, 2));
    pts.push(`${x},${y.toFixed(1)}`);
  }
  return `M0,${H} L${pts.join(" L")} L${W},${H} Z`;
};

export const WaveField: React.FC<Props> = ({
  mode = "sea",
  word = "",
  word2 = "",
  kicker = "04 · 海　THE SEA",
  note = "每一个浪头都会落下，但海不会变成平静的水面。",
  label = "",
  bead = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();
  const t = frame / fps;
  const dur = durationInFrames / fps;
  const p = clamp(t / Math.max(0.4, dur));

  // 浪的幅度 / 中央那个包：不同 mode 走不同的曲线
  let amp = 26;
  let bump = 0;
  if (mode === "crest") {
    const g = clamp(p / 0.7);
    bump = -190 * g;
    amp = 20 + 14 * g;
  } else if (mode === "sea") {
    bump = -40 * Math.sin(p * Math.PI);
    amp = 26;
  } else if (mode === "fall") {
    const g = clamp(p / 0.55);
    bump = -190 * (1 - g);
    amp = 26 + 22 * g;
  } else if (mode === "trough") {
    const g = clamp(p / 0.5);
    const h = clamp((p - 0.5) / 0.5);
    bump = 110 * g * (1 - h);
    amp = 24 + 18 * g;
  } else if (mode === "calm") {
    bump = 0;
    amp = 26 - 22 * clamp(p / 0.7);
  } else if (mode === "line") {
    bump = 0;
    amp = 24 - 23 * clamp(p / 0.8);
  }

  const LAYERS = [
    { base: 596, a: 1.0, k: 1.1, ph: t * 0.55, fill: "rgba(14,26,44,0.96)" },
    { base: 648, a: 0.82, k: 1.5, ph: t * 0.72 + 1.7, fill: "rgba(20,38,62,0.94)" },
    { base: 700, a: 0.62, k: 2.0, ph: t * 0.9 + 3.1, fill: "rgba(28,54,84,0.92)" },
    { base: 752, a: 0.44, k: 2.6, ph: t * 1.1 + 4.6, fill: "rgba(38,72,108,0.90)" },
  ];

  // 被吞掉的字：随浪头塌下一起沉
  const sink = mode === "fall" || mode === "trough" ? clamp((p - 0.35) / 0.5) : 0;
  const wordP = mode === "fall" || mode === "trough" ? clamp((p - 0.1) / 0.25) * (1 - sink) : 0;

  const beadP = bead ? clamp((p - 0.45) / 0.35) : 0;

  // 月光碎金：顶光在海面拉出一条闪烁的光路。
  // 夜海没有这个就只是一片渐变（体检边缘占比 0.002 就是这么被抓的）；
  // 有了它，海面有结构、有动感，也和全片的"单点光"语言接上。
  const glints = React.useMemo(() => {
    const rnd = mulberry32(20261026);
    return Array.from({ length: 150 }, () => {
      const spread = (rnd() + rnd() + rnd()) / 3 - 0.5; // 中心集中、两边稀疏
      return {
        x: 960 + spread * 2 * 310,
        y: 600 + rnd() * 336,
        w: 8 + rnd() * 26,
        ph: rnd() * Math.PI * 2,
        sp: 1.1 + rnd() * 2.3,
        warm: rnd() > 0.28,
      };
    });
  }, []);
  // 浪头大起大落时碎金让位（不然白沫和碎金糊在一起）
  const shimmerO = 1 - Math.min(0.6, Math.abs(bump) / 320);

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: W,
          height: H,
          transform: `translate(-50%, -50%) scale(${s})`,
        }}
      >
        {/* 天：只有上方一点点光，海自己是暗的 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(180deg, #070b12 0%, #0a1524 42%, #0d1e30 70%, #0a1726 100%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: W,
            height: 620,
            background:
              "radial-gradient(620px 380px at 50% 26%, rgba(255,232,190,0.10) 0%, rgba(255,232,190,0) 70%)",
          }}
        />

        <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0 }}>
          {LAYERS.map((L, i) => (
            <g key={i}>
              <path
                d={wavePath(L.base, amp * L.a, L.ph, bump * L.a, L.k)}
                fill={L.fill}
              />
              <path
                d={wavePath(L.base, amp * L.a, L.ph, bump * L.a, L.k)}
                fill="none"
                stroke={i === 0 ? "rgba(226,236,248,0.22)" : "rgba(226,236,248,0.08)"}
                strokeWidth={i === 0 ? 1.6 : 1}
              />
            </g>
          ))}
          {/* 浪尖的白沫：只在 crest / fall 的浪头上 */}
          {Math.abs(bump) > 60 ? (
            <ellipse
              cx={960}
              cy={596 + bump}
              rx={210}
              ry={16}
              fill="rgba(255,255,255,0.10)"
            />
          ) : null}
        </svg>

        {/* 碎金光路：躺在最前面那层浪上 */}
        {glints.map((g, i) => {
          const tw = 0.5 + 0.5 * Math.sin(t * g.sp + g.ph);
          const depth = (g.y - 600) / 336; // 越靠下（近）越宽越淡
          const o = (0.16 + 0.42 * tw) * (1 - depth * 0.45) * shimmerO;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: g.x - g.w / 2,
                top: g.y,
                width: g.w * (1 + depth * 0.9),
                height: 3,
                borderRadius: 1.5,
                background: g.warm ? "rgba(255,228,176,0.95)" : "rgba(205,226,246,0.85)",
                opacity: o,
                boxShadow: "0 0 8px rgba(255,226,170,0.40)",
              }}
            />
          );
        })}

        {/* 被浪吞掉的字 */}
        {word ? (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 470,
              textAlign: "center",
              fontFamily: FONT,
              fontSize: 64,
              fontWeight: 700,
              letterSpacing: 8,
              color: C.ink,
              opacity: wordP * 0.92,
              transform: `translateY(${sink * 120}px) scale(${1 - sink * 0.08})`,
              filter: `blur(${sink * 4}px)`,
              textShadow: "0 0 40px rgba(0,0,0,0.6)",
            }}
          >
            {word}
            {word2 ? (
              <span style={{ color: "rgba(139,147,167,0.9)" }}>　{word2}</span>
            ) : null}
          </div>
        ) : null}

        {/* 回场：金珠从海里升起来 */}
        {bead ? (
          <div
            style={{
              position: "absolute",
              left: 960 - 13,
              top: 620 - 150 * beadP,
              width: 26,
              height: 26,
              borderRadius: 13,
              background: "radial-gradient(circle at 34% 30%, #fff8e2 0%, #f3c14b 54%, #7a5c1c 100%)",
              boxShadow: "0 0 40px rgba(243,193,75,0.8)",
              opacity: beadP,
            }}
          />
        ) : null}

        {/* 那条线：海退掉之后，剩下的就是它（全片的"尺子"）。
            calm 是青灰海平线；line 时它收成金色 —— 和章二的回归金线是同一把尺子 */}
        {mode === "line" || mode === "calm" ? (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 700,
              height: mode === "line" ? 2 : 1,
              background:
                mode === "line"
                  ? "linear-gradient(90deg, rgba(243,193,75,0) 0%, rgba(243,193,75,0.85) 50%, rgba(243,193,75,0) 100%)"
                  : "linear-gradient(90deg, rgba(73,227,209,0) 0%, rgba(73,227,209,0.42) 50%, rgba(73,227,209,0) 100%)",
              boxShadow: mode === "line" ? "0 0 22px rgba(243,193,75,0.5)" : "none",
              opacity: clamp((p - 0.3) / 0.4),
            }}
          />
        ) : null}

        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>
            {kicker}
          </div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {label ? (
          <div
            style={{
              position: "absolute",
              left: 148,
              top: 268,
              width: 700,
              fontFamily: FONT,
              fontSize: 48,
              fontWeight: 700,
              lineHeight: 1.45,
              letterSpacing: 3,
              color: C.ink,
              opacity: clamp((frame - fps * 0.25) / (fps * 0.5)),
              textShadow: "0 0 40px rgba(0,0,0,0.6)",
            }}
          >
            {label}
          </div>
        ) : null}

        <div
          style={{
            position: "absolute",
            right: 130,
            bottom: 96,
            width: 560,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 19,
            lineHeight: 1.8,
            letterSpacing: 1,
            color: "rgba(160,168,188,0.66)",
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
