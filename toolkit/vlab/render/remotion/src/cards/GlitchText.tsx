import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { mulberry32 } from "../common/random";

type Props = {
  text?: string;
  sub?: string;
  seed?: number;
  size?: number;
};

// 故障字：正文左右各偏一份青/品红通道，再按帧切条挪位。
// 关键在"不连续"——每 3 帧才换一次抖动值，看上去才是数字信号出错，而不是抽风。
export const GlitchText: React.FC<Props> = ({
  text = "没有中心",
  sub = "NO CENTER",
  seed = 31,
  size = 132,
}) => {
  const frame = useCurrentFrame();
  const tick = Math.floor(frame / 3);
  const rnd = mulberry32(seed + tick * 977);
  const slices = Array.from({ length: 7 }, () => ({
    y: rnd() * 100,
    h: 4 + rnd() * 12,
    dx: (rnd() - 0.5) * 90,
  }));
  // 大动作只在 3 个时间点爆发，其余时间几乎没有抖动
  const burst = [10, 34, 58].some((b) => frame >= b && frame < b + 5);
  const amp = burst ? 1 : 0.12;
  const enter = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const shatter = interpolate(frame, [64, 78], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "relative", opacity: enter }}>
        {/* 青 / 品红通道 */}
        {[
          { c: C.cyan, dx: -6 * amp, dy: -2 * amp },
          { c: C.magenta, dx: 6 * amp, dy: 2 * amp },
        ].map((ch, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              inset: 0,
              fontFamily: FONT,
              fontWeight: 700,
              fontSize: size,
              letterSpacing: 8,
              color: ch.c,
              mixBlendMode: "screen",
              transform: `translate(${ch.dx}px, ${ch.dy}px)`,
              opacity: 0.55,
              whiteSpace: "nowrap",
            }}
          >
            {text}
          </div>
        ))}
        {/* 主字 */}
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 700,
            fontSize: size,
            letterSpacing: 8,
            color: C.ink,
            whiteSpace: "nowrap",
            filter: shatter > 0 ? `blur(${shatter * 2.5}px)` : undefined,
            transform: `scale(${1 + shatter * 0.02})`,
          }}
        >
          {text}
        </div>
        {/* 切条 */}
        {slices.map((s, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              inset: 0,
              clipPath: `inset(${s.y}% 0 ${Math.max(0, 100 - s.y - s.h)}% 0)`,
              transform: `translateX(${s.dx * amp}px)`,
              background: "rgba(6,7,13,0.0)",
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: size,
                letterSpacing: 8,
                color: i % 3 === 0 ? C.gold : C.ink,
                whiteSpace: "nowrap",
                opacity: 0.9,
              }}
            >
              {text}
            </div>
          </div>
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 560,
          fontFamily: FONT,
          fontSize: 26,
          letterSpacing: 12,
          color: C.dim,
          opacity: interpolate(frame, [22, 40], [0, 1], {
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
