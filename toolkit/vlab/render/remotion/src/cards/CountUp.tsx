import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";

type Props = {
  to?: number;
  label?: string;
  note?: string;
  kicker?: string;
  /** 数字下面那句话的前半句，默认是鸟群场景的写法 */
  caption?: string;
};

// 数字滚动：大数字 + 单位 + 补充句。数字用等宽数字（tabular-nums），滚动时不左右跳。
export const CountUp: React.FC<Props> = ({
  to = 640,
  label = "只鸟",
  note = "0 个指挥",
  kicker = "ONE FLOCK",
  caption = "而它们没有一只知道全局 ——",
}) => {
  const frame = useCurrentFrame();
  const v = interpolate(frame, [4, 56], [0, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const shown = Math.round(v).toLocaleString("en-US");
  const subP = interpolate(frame, [30, 52], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const barW = interpolate(frame, [10, 62], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 26,
          letterSpacing: 10,
          color: C.cyan,
          marginBottom: 18,
        }}
      >
        {kicker}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 700,
            fontSize: 230,
            lineHeight: 1,
            color: C.gold,
            fontVariantNumeric: "tabular-nums",
            textShadow: "0 0 60px rgba(243,193,75,0.30)",
          }}
        >
          {shown}
        </div>
        <div style={{ fontFamily: FONT, fontSize: 52, color: C.ink }}>{label}</div>
      </div>
      <div
        style={{
          width: 620,
          height: 2,
          background: "rgba(255,255,255,0.12)",
          marginTop: 42,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${barW * 100}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${C.gold}, ${C.cyan})`,
          }}
        />
      </div>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 34,
          color: C.dim,
          marginTop: 36,
          opacity: subP,
        }}
      >
        {caption} <span style={{ color: C.ink }}>{note}</span>
      </div>
    </AbsoluteFill>
  );
};
