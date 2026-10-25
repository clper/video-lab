import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { AbstractScene } from "../common/scenes";

type Props = {
  kicker?: string;
  labelA?: string;
  labelB?: string;
  seed?: number;
};

// 蒙版擦除：一条斜向硬边从左扫到右，把"旧画面"换成"新画面"，
// 边缘跟一条亮线走过去。比交叉淡入更有"揭露"的物理感。
export const MaskWipe: React.FC<Props> = ({
  kicker = "SAME RULES",
  labelA = "个体",
  labelB = "群体",
  seed = 21,
}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [8, 62], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  // 斜边的 x 位置（%），留 18% 的余量让画面两端也能完全擦净
  const edge = -18 + p * 136;
  const edgeOpacity = interpolate(frame, [6, 12, 58, 64], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const labelP = interpolate(frame, [12, 34], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <AbstractScene seed={seed} hue="cyan" birds={12} />
      <div
        style={{
          position: "absolute",
          inset: 0,
          clipPath: `polygon(0 0, ${edge}% 0, ${edge - 14}% 100%, 0 100%)`,
        }}
      >
        <AbstractScene seed={seed} hue="gold" birds={44} />
      </div>
      {/* 擦除亮线 */}
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: `${edge}%`,
          width: 4,
          marginLeft: -2,
          opacity: edgeOpacity,
          background: `linear-gradient(180deg, transparent, ${C.ink}, transparent)`,
          boxShadow: `0 0 34px ${C.gold}`,
          transform: "rotate(1.6deg) scaleY(1.12)",
        }}
      />
      {/* 两端标签 */}
      <div
        style={{
          position: "absolute",
          left: 96,
          bottom: 300,
          fontFamily: FONT,
          fontSize: 44,
          fontWeight: 700,
          color: C.ink,
          opacity: labelP * (1 - p),
        }}
      >
        {labelA}
      </div>
      <div
        style={{
          position: "absolute",
          right: 96,
          bottom: 300,
          fontFamily: FONT,
          fontSize: 44,
          fontWeight: 700,
          color: C.gold,
          opacity: interpolate(p, [0.55, 1], [0, 1], { extrapolateLeft: "clamp" }),
        }}
      >
        {labelB}
      </div>
      <div
        style={{
          position: "absolute",
          top: 360,
          left: 96,
          fontFamily: FONT,
          fontSize: 24,
          letterSpacing: 10,
          color: C.cyan,
          opacity: labelP,
        }}
      >
        {kicker}
      </div>
    </AbsoluteFill>
  );
};
