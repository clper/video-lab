import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";

const ITEMS = [
  { n: "01", title: "分离", en: "SEPARATION", desc: "别撞上邻居" },
  { n: "02", title: "对齐", en: "ALIGNMENT", desc: "跟着邻居的方向" },
  { n: "03", title: "聚合", en: "COHESION", desc: "别掉队" },
];

// 科技卡：三张规则卡依次落位，然后轮流点亮。信息密度靠"序号 + 中英标题 + 一句话"叠出来。
export const TechCard: React.FC<{ heading?: string; kicker?: string }> = ({
  heading = "三条规则，零个指挥",
  kicker = "BOIDS / 1987",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ padding: "0 96px", justifyContent: "center" }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 24,
          letterSpacing: 10,
          color: C.cyan,
          marginBottom: 18,
          opacity: interpolate(frame, [0, 12], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        {kicker}
      </div>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 56,
          fontWeight: 700,
          color: C.ink,
          marginBottom: 52,
          opacity: interpolate(frame, [0, 16], [0, 1], {
            extrapolateRight: "clamp",
          }),
          transform: `translateY(${interpolate(frame, [0, 16], [18, 0], {
            extrapolateRight: "clamp",
          })}px)`,
        }}
      >
        {heading}
      </div>

      {ITEMS.map((it, i) => {
        const p = spring({
          frame: frame - 8 - i * 14,
          fps,
          config: { damping: 16, stiffness: 120 },
        });
        const active = frame >= 24 + i * 26 && frame < 52 + i * 26;
        return (
          <div
            key={it.n}
            style={{
              opacity: p,
              transform: `translateY(${(1 - p) * 46}px)`,
              display: "flex",
              alignItems: "center",
              gap: 26,
              padding: "30px 32px",
              marginBottom: 24,
              borderRadius: 18,
              background: active ? "rgba(243,193,75,0.10)" : "rgba(255,255,255,0.035)",
              border: `1px solid ${active ? C.gold : "rgba(255,255,255,0.10)"}`,
              boxShadow: active ? "0 0 40px rgba(243,193,75,0.18)" : "none",
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 62,
                fontWeight: 700,
                color: active ? C.gold : C.dim,
                width: 92,
              }}
            >
              {it.n}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: FONT, fontSize: 44, fontWeight: 700, color: C.ink }}>
                {it.title}
                <span
                  style={{
                    fontSize: 20,
                    letterSpacing: 4,
                    color: C.dim,
                    marginLeft: 12,
                    fontWeight: 400,
                  }}
                >
                  {it.en}
                </span>
              </div>
              <div style={{ fontFamily: FONT, fontSize: 28, color: C.dim, marginTop: 8 }}>
                {it.desc}
              </div>
            </div>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: active ? C.gold : "rgba(255,255,255,0.15)",
                boxShadow: active ? `0 0 16px ${C.gold}` : "none",
              }}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
