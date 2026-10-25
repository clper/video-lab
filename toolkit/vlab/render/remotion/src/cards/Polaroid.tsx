import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { AbstractScene, SceneHue } from "../common/scenes";

type Props = {
  caption?: string;
  sub?: string;
  kicker?: string;
  seed?: number;
  hue?: SceneHue;
};

// 拍立得：白框照片从下方带旋转甩进来，落定后微微回弹；第二张叠在后面做层次。
// "手作感"来自三处：白框比画面大一圈、底边留白最宽、整张微微倾斜。
export const Polaroid: React.FC<Props> = ({
  caption = "鸟群 · 尚未命名的秩序",
  sub = "FLOCK, 2026",
  kicker = "EVIDENCE 01",
  seed = 11,
  hue = "gold",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const back = spring({ frame: frame - 2, fps, config: { damping: 22, stiffness: 90 } });
  const front = spring({ frame: frame - 14, fps, config: { damping: 14, stiffness: 110 } });
  const tilt = interpolate(front, [0, 1], [9, -3.2]);
  const capP = interpolate(frame, [30, 52], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      {/* 背后那张 */}
      <div
        style={{
          position: "absolute",
          left: 520,
          top: 940,
          width: 520,
          height: 640,
          transform: `translate(-50%, -50%) rotate(${interpolate(back, [0, 1], [16, 8])}deg) translateY(${(1 - back) * 150}px)`,
          opacity: back * 0.85,
          background: "#efece2",
          borderRadius: 6,
          padding: 20,
          boxShadow: "0 30px 70px rgba(0,0,0,0.5)",
        }}
      >
        <div style={{ position: "relative", width: "100%", height: 460, overflow: "hidden" }}>
          <AbstractScene seed={seed + 5} hue="cyan" birds={14} />
        </div>
      </div>

      {/* 前面那张 */}
      <div
        style={{
          position: "absolute",
          left: 540,
          top: 1000,
          width: 660,
          height: 820,
          transform: `translate(-50%, -50%) rotate(${tilt}deg) translateY(${(1 - front) * 260}px) scale(${0.92 + front * 0.08})`,
          opacity: Math.min(1, front * 1.6),
          background: "#f4f1e6",
          borderRadius: 8,
          padding: 26,
          paddingBottom: 30,
          boxShadow: "0 44px 90px rgba(0,0,0,0.62)",
        }}
      >
        <div style={{ position: "relative", width: "100%", height: 570, overflow: "hidden" }}>
          <AbstractScene seed={seed} hue={hue} birds={30} />
          {/* 相纸的极轻暗角，别让程序化画面太"干净" */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              boxShadow: "inset 0 0 90px rgba(0,0,0,0.55)",
            }}
          />
        </div>
        <div
          style={{
            marginTop: 22,
            fontFamily: FONT,
            fontSize: 34,
            color: "#1b1d24",
            letterSpacing: 1,
            opacity: capP,
            transform: `translateY(${(1 - capP) * 8}px)`,
          }}
        >
          {caption}
        </div>
        <div
          style={{
            marginTop: 6,
            fontFamily: FONT,
            fontSize: 20,
            letterSpacing: 5,
            color: "rgba(27,29,36,0.55)",
            opacity: capP,
          }}
        >
          {sub}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: 380,
          fontFamily: FONT,
          fontSize: 24,
          letterSpacing: 10,
          color: C.cyan,
          opacity: capP,
        }}
      >
        {kicker}
      </div>
    </AbsoluteFill>
  );
};
