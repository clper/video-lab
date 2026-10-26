import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { mulberry32 } from "../common/random";

type Props = {
  kicker?: string;
  title?: string;
  /** 漩涡强度：0 是规整网格，越大越卷 */
  swirl?: number;
  cols?: number;
  seed?: number;
};

// 涡旋方块：规则的方格阵被一个速度场拧成螺旋。
// "规则 → 混沌"的观感来自同一个网格只改一个参数，不换素材。
export const VortexBlocks: React.FC<Props> = ({
  kicker = "LOCAL RULES",
  title = "规则不变，形状全变",
  swirl = 1,
  cols = 15,
  seed = 51,
}) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const rnd = React.useMemo(() => mulberry32(seed), [seed]);
  const jitter = React.useMemo(
    () => Array.from({ length: cols * cols }, () => rnd()),
    [rnd, cols],
  );

  const cell = 960 / cols;
  const cx = 540;
  const cy = 1080;
  const amount = interpolate(frame, [0, 28], [0, swirl], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const blocks = jitter.map((j, i) => {
    const gx = i % cols;
    const gy = Math.floor(i / cols);
    const bx = 540 - 480 + gx * cell + cell / 2;
    const by = 1080 - 480 + gy * cell + cell / 2;
    const dx = bx - cx;
    const dy = by - cy;
    const r = Math.hypot(dx, dy);
    const ang0 = Math.atan2(dy, dx);
    // 越靠外转得越多，再叠一点随时间推进的相位，看上去才像流体
    const ang = ang0 + amount * (1.6 - r / 700) * 1.5 + t * 0.5 * amount;
    const rr = r * (1 - 0.12 * amount * Math.sin(t * 1.1 + r / 260));
    const px = cx + Math.cos(ang) * rr;
    const py = cy + Math.sin(ang) * rr * 0.72;
    const size = cell * (0.62 + j * 0.3) * (1 - 0.18 * amount);
    const glow = 0.25 + 0.75 * Math.abs(Math.sin(t * 1.6 + i * 0.35));
    return { px, py, size, glow, ang };
  });

  return (
    <AbsoluteFill>
      {blocks.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: b.px - b.size / 2,
            top: b.py - b.size / 2,
            width: b.size,
            height: b.size,
            borderRadius: 3 + (b.size % 5),
            background: i % 17 === 0 ? C.cyan : i % 11 === 0 ? C.magenta : C.gold,
            opacity: 0.14 + b.glow * 0.5 * (0.5 + amount * 0.5),
            transform: `rotate(${(b.ang * 180) / Math.PI}deg)`,
            boxShadow: `0 0 ${b.size * 1.4}px rgba(243,193,75,0.28)`,
          }}
        />
      ))}

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 230,
          textAlign: "center",
          opacity: interpolate(frame, [24, 44], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 24, letterSpacing: 12, color: C.cyan }}>{kicker}</div>
        <div style={{ fontFamily: FONT, fontSize: 50, fontWeight: 700, color: C.ink, marginTop: 18 }}>
          {title}
        </div>
      </div>
    </AbsoluteFill>
  );
};
