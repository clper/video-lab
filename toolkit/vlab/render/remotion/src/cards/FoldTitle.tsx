import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 片名卡：字是"显影"出来的（模糊 → 实），不是飞进来的。
// 一条金线先拉开，标题逐字浮上来，副题和外文行各晚半拍。

type Props = {
  title?: string;
  sub?: string;
  latin?: string;
  /** 标题下面的分隔线最宽多少 */
  rule?: number;
  /** 片尾三行文献线索（片名卡留空） */
  refs?: string[];
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));

export const FoldTitle: React.FC<Props> = ({
  title = "对折",
  sub = "从 0.1 毫米到月球",
  latin = "BISECTIO",
  rule = 760,
  refs = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const t0 = Math.round(fps * 0.25);
  const per = Math.round(fps * 0.09);
  const lineP = clamp((frame - t0 + 4) / (fps * 0.45));
  const subP = clamp((frame - t0 - per * title.length - 6) / (fps * 0.5));
  const latinP = clamp((frame - t0 - per * title.length - fps * 0.45) / (fps * 0.5));
  const drift = 1 + 0.014 * clamp(1 - frame / (fps * 6));

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: 1920,
          height: 1080,
          transform: `translate(-50%, -50%) scale(${s})`,
        }}
      >
        {/* 金线：从中间往两边拉开。压在标题上方，别切字头 */}
        <div
          style={{
            position: "absolute",
            left: 960 - (rule * lineP) / 2,
            top: 238,
            width: rule * lineP,
            height: 1,
            background: `linear-gradient(90deg, rgba(243,193,75,0) 0%, ${C.gold} 50%, rgba(243,193,75,0) 100%)`,
            opacity: 0.85,
          }}
        />

        {/* 标题：逐字显影 */}
        <div
          style={{
            position: "absolute",
            top: 300,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            gap: 18,
            transform: `scale(${drift})`,
            transformOrigin: "50% 50%",
          }}
        >
          {Array.from(title).map((ch, i) => {
            const p = clamp((frame - t0 - i * per) / (fps * 0.36));
            return (
              <span
                key={i}
                style={{
                  fontFamily: FONT,
                  fontWeight: 700,
                  fontSize: 260,
                  lineHeight: 1.08,
                  letterSpacing: 8,
                  color: C.ink,
                  opacity: p,
                  filter: `blur(${(1 - p) * 10}px)`,
                  textShadow: "0 0 90px rgba(243,193,75,0.22)",
                }}
              >
                {ch}
              </span>
            );
          })}
        </div>

        {/* 副题 */}
        <div
          style={{
            position: "absolute",
            top: 690,
            left: 0,
            right: 0,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 52,
            letterSpacing: 10,
            color: C.ink,
            opacity: subP * 0.92,
            transform: `translateY(${(1 - subP) * 10}px)`,
          }}
        >
          {sub}
        </div>

        {/* 外文行：纯粹是气质 */}
        <div
          style={{
            position: "absolute",
            top: 782,
            left: 0,
            right: 0,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 22,
            letterSpacing: 18,
            color: C.dim,
            opacity: latinP * 0.8,
          }}
        >
          {latin}
        </div>

        {/* 文献线索：片尾才有，一行一行淡上来，字号很小，像论文脚注。
            小可以，糊不行 —— 19px/0.56 在 1080p 压完变成一条灰带，这里抬到 21px/0.78 */}
        {refs.length ? (
          <div style={{ position: "absolute", top: 838, left: 0, right: 0, textAlign: "center" }}>
            {refs.map((r, i) => {
              const p = clamp((frame - t0 - per * title.length - fps * 0.3 - i * fps * 0.18) / (fps * 0.6));
              return (
                <div
                  key={i}
                  style={{
                    fontFamily: FONT,
                    fontSize: 21,
                    lineHeight: 1.85,
                    letterSpacing: 2,
                    color: "rgba(160,168,188,0.78)",
                    opacity: p,
                    transform: `translateY(${(1 - p) * 8}px)`,
                  }}
                >
                  {r}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
