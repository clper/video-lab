import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";

type Props = {
  text?: string;
  stamp?: string;
  sub?: string;
};

// 印章划掉：文字先立住，红章从上方砸下来（带过冲），再画一道划掉的横线。
// 反例镜头要的就是"被否决"的那一下，所以章子的落点比文字略偏、略歪。
export const StampStrike: React.FC<Props> = ({
  text = "它们只是各自在飞",
  stamp = "反例",
  sub = "WRONG INTUITION",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const textP = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const slam = spring({ frame: frame - 16, fps, config: { damping: 9, stiffness: 190, mass: 0.6 } });
  const strikeP = interpolate(frame, [34, 48], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const shake = slam > 0 && slam < 1 ? (1 - slam) * 6 : 0;

  // 字的多少决定了字号：字少就放大，字多就收小，但章子永远不许压到字上
  const stampSize = stamp.length <= 1 ? 96 : stamp.length <= 2 ? 64 : 46;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 64,
          padding: "0 90px",
          transform: `translate(${Math.sin(frame * 2.3) * shake}px, ${Math.cos(frame * 1.7) * shake}px)`,
        }}
      >
        {/* 文字 + 划掉的红线：线只盖住文字，不伸到章子那边 */}
        <div style={{ position: "relative" }}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 70,
              fontWeight: 700,
              color: C.ink,
              opacity: textP,
              letterSpacing: 2,
              lineHeight: 1.45,
              whiteSpace: "nowrap",
            }}
          >
            {text}
          </div>
          <div
            style={{
              position: "absolute",
              left: 0,
              top: "52%",
              height: 8,
              width: `${strikeP * 100}%`,
              background: C.red,
              borderRadius: 4,
              boxShadow: `0 0 26px ${C.red}`,
              transform: "rotate(-2.4deg)",
              opacity: 0.92,
            }}
          />
        </div>

        {/* 印章：站在文字右侧，不再压字；从上方带过冲砸下来 */}
        <div
          style={{
            position: "relative",
            width: 200,
            height: 200,
            flex: "0 0 auto",
            borderRadius: 18,
            border: `7px solid ${C.red}`,
            transform: `rotate(${interpolate(slam, [0, 1], [-34, -11])}deg) scale(${interpolate(
              slam,
              [0, 1],
              [2.1, 1],
            )})`,
            opacity: Math.min(1, slam * 2.2),
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: C.red,
            fontFamily: FONT,
            fontSize: stampSize,
            fontWeight: 700,
            letterSpacing: 4,
            whiteSpace: "nowrap",
            boxShadow: `0 0 50px rgba(255,91,91,0.35)`,
            background: "rgba(255,91,91,0.04)",
          }}
        >
          {stamp}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: 738,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: FONT,
          fontSize: 24,
          letterSpacing: 12,
          color: C.dim,
          opacity: interpolate(frame, [44, 62], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {sub}
      </div>
    </AbsoluteFill>
  );
};
