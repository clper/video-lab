import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";

export type ScaleRow = { label: string; value: string; unit?: string; frac: number };

type Props = {
  kicker?: string;
  rows?: ScaleRow[];
  note?: string;
};

const DEFAULT_ROWS: ScaleRow[] = [
  { label: "一只鸟", value: "0.2", unit: "kg", frac: 0.06 },
  { label: "一群鸟", value: "640", unit: "只", frac: 0.22 },
  { label: "一种秩序", value: "10⁴", unit: "次互动/秒", frac: 0.52 },
  { label: "一次涌现", value: "∞", unit: "种可能", frac: 0.96 },
];

// 量级卡片：四行按数量级排开，各自从右侧滑入，杆长按对数量级给。
// "尺度跳变"靠两点：行距固定但杆长跨度极大、最后一行留白。
export const ScaleCard: React.FC<Props> = ({
  kicker = "ONE FLOCK, FOUR SCALES",
  rows = DEFAULT_ROWS,
  note = "同一个机制，撑住了四个尺度",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rulerP = interpolate(frame, [4, 34], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const noteP = interpolate(frame, [58, 78], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 96px" }}>
      <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 10, color: C.cyan, marginBottom: 40 }}>
        {kicker}
      </div>

      <div style={{ position: "relative" }}>
        {/* 左侧竖尺 */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: -12,
            width: 2,
            height: `${rulerP * 100}%`,
            background: `linear-gradient(180deg, ${C.gold}, ${C.cyan}, transparent)`,
          }}
        />
        {rows.map((r, i) => {
          const p = spring({
            frame: frame - 10 - i * 13,
            fps,
            config: { damping: 18, stiffness: 110 },
          });
          const bar = interpolate(frame, [16 + i * 13, 52 + i * 13], [0, r.frac], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          });
          const isLast = i === rows.length - 1;
          return (
            <div
              key={r.label}
              style={{
                opacity: p,
                transform: `translateX(${(1 - p) * 120}px)`,
                paddingLeft: 34,
                marginBottom: 54,
              }}
            >
              <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
                <div style={{ fontFamily: FONT, fontSize: 34, color: C.dim, width: 190 }}>{r.label}</div>
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: isLast ? 68 : 58,
                    fontWeight: 700,
                    color: isLast ? C.gold : C.ink,
                    fontVariantNumeric: "tabular-nums",
                    lineHeight: 1,
                  }}
                >
                  {r.value}
                </div>
                {r.unit && (
                  <div style={{ fontFamily: FONT, fontSize: 24, color: C.dim, letterSpacing: 2 }}>
                    {r.unit}
                  </div>
                )}
              </div>
              <div
                style={{
                  height: isLast ? 3 : 2,
                  marginTop: 16,
                  width: "100%",
                  background: "rgba(255,255,255,0.07)",
                }}
              >
                <div
                  style={{
                    width: `${bar * 100}%`,
                    height: "100%",
                    background: isLast
                      ? `linear-gradient(90deg, ${C.gold}, ${C.magenta})`
                      : `linear-gradient(90deg, ${C.gold}, ${C.cyan})`,
                    boxShadow: isLast ? `0 0 22px ${C.gold}` : "none",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ fontFamily: FONT, fontSize: 30, color: C.dim, opacity: noteP, marginTop: 10 }}>
        {note}
      </div>
    </AbsoluteFill>
  );
};
