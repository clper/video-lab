import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";

type Props = {
  text: string;
  highlight?: string;
  charsPerSecond?: number;
  footer?: string;
};

// 逐字字幕：按逗号强制断行（避免"群。"单独掉到第二行），逐字弹出，关键词金色。
export const KineticSubtitle: React.FC<Props> = ({
  text,
  highlight = "",
  charsPerSecond = 8,
  footer,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // "你无法从一只鸟，读出整个鸟群。" -> ["你无法从一只鸟，", "读出整个鸟群。"]
  const raw = text.split("，");
  const lines = raw.map((s, i) => (i < raw.length - 1 ? `${s}，` : s));

  const hiStart = highlight ? text.indexOf(highlight) : -1;
  const hiEnd = hiStart >= 0 ? hiStart + highlight.length : -1;

  const total = Array.from(text).length;
  const revealed = Math.min(total, Math.floor((frame / fps) * charsPerSecond) + 1);
  const footerOpacity = interpolate(frame, [42, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  let gi = 0;

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: "0 80px 200px" }}>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 22,
          letterSpacing: 10,
          color: C.cyan,
          marginBottom: 26,
          opacity: interpolate(frame, [0, 12], [0, 1], {
            extrapolateRight: "clamp",
          }),
        }}
      >
        CONCLUSION
      </div>

      <div style={{ fontFamily: FONT, fontSize: 64, fontWeight: 700, lineHeight: 1.4 }}>
        {lines.map((line, li) => (
          <div key={li} style={{ display: "flex", whiteSpace: "pre" }}>
            {Array.from(line).map((ch) => {
              const i = gi++;
              const p = spring({
                frame: frame - i * (fps / charsPerSecond) * 0.85,
                fps,
                config: { damping: 14, stiffness: 180 },
              });
              const on = i < revealed;
              const isHi = hiStart >= 0 && i >= hiStart && i < hiEnd;
              return (
                <span
                  key={i}
                  style={{
                    display: "inline-block",
                    color: isHi ? C.gold : C.ink,
                    opacity: on ? Math.min(1, p) : 0,
                    transform: `translateY(${(1 - p) * 24}px) scale(${0.92 + 0.08 * p})`,
                    textShadow: isHi
                      ? "0 0 30px rgba(243,193,75,0.45)"
                      : "0 2px 18px rgba(0,0,0,0.85)",
                  }}
                >
                  {ch}
                </span>
              );
            })}
          </div>
        ))}
      </div>

      {footer ? (
        <div
          style={{
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 6,
            color: C.dim,
            marginTop: 34,
            opacity: footerOpacity,
          }}
        >
          {footer}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
