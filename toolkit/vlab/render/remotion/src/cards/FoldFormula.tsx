import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 章三开场：把章二那根纸柱压成一条金线。
// 这根线一直在长，可它从来没被折过——所以这一镜只放两样东西：
// 一条线，和一个算式。第二个镜头再让线横过来，问"那纸得多长"。
// （线横过来的那一下，是全片唯一的机械动作，不要加别的东西抢它。）

type Props = {
  kicker?: string;
  note?: string;
  /** 线横过来，问长度 */
  turn?: boolean;
  /** 算式里那个答案 */
  answer?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

// 线站在桌上：底端固定，长度往上长
const FX = 700;
const BASE_Y = 796;
const LINE_H = 600;

export const FoldFormula: React.FC<Props> = ({
  kicker = "03 · 墙　THE WALL",
  note = "439,805 公里是算出来的 —— 没有任何一只手折到过这里。",
  turn = false,
  answer = "439,805 公里",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const lineP = ease((frame - 2) / (fps * 0.9));
  const formP = ease((frame - Math.round(fps * 0.75)) / (fps * 0.8));
  // 横过来：绕底端转 -90°，转完线就躺在桌面上
  const turnP = turn ? ease((frame - Math.round(fps * 1.1)) / (fps * 0.85)) : 0;
  const askP = turn ? ease((frame - Math.round(fps * 1.65)) / (fps * 0.6)) : 0;

  // 算式逐字（按分量拆开写，是为了让 × 和 2ⁿ 各自有一点分量）
  const parts = [
    { t: "0.1", unit: "mm" },
    { t: "×", unit: "" },
    { t: "2", unit: "ⁿ" },
  ];

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
        {/* 章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(lineP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>{kicker}</div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 桌面线 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: BASE_Y,
            width: 1680,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.16) 40%, rgba(255,255,255,0.16) 60%, rgba(255,255,255,0) 100%)",
            opacity: lineP,
          }}
        />

        {/* 那条线：从桌上长起来；转一下，就躺在桌面上了 */}
        <div
          style={{
            position: "absolute",
            left: FX,
            top: BASE_Y,
            width: LINE_H,
            height: 1,
            transformOrigin: "0 0",
            transform: `rotate(${-90 * turnP}deg)`,
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 0,
              bottom: 0,
              width: 2,
              height: LINE_H * lineP,
              background:
                "linear-gradient(0deg, rgba(255,226,150,0.95) 0%, rgba(243,193,75,0.95) 55%, rgba(255,240,200,0.05) 100%)",
              boxShadow: "0 0 26px rgba(243,193,75,0.65)",
            }}
          />
          {/* 线头：一个小亮点，说明这根线一直在长 */}
          <div
            style={{
              position: "absolute",
              left: -5,
              bottom: LINE_H * lineP - 5,
              width: 12,
              height: 12,
              borderRadius: 6,
              background: "#fff3d0",
              boxShadow: "0 0 26px rgba(255,226,150,0.95)",
              opacity: lineP,
            }}
          />
        </div>

        {/* 算式：从灰里浮出来；线一转过来，算式就退到后面去 */}
        <div
          style={{
            position: "absolute",
            left: 990,
            top: 300,
            opacity: formP * (1 - 0.55 * turnP),
            transform: `translateY(${(1 - formP) * 18 - 70 * turnP}px)`,
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: "rgba(139,147,167,0.85)" }}>
            厚度
          </div>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 18, marginTop: 14 }}>
            {parts.map((p, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 8,
                  opacity: clamp((formP - i * 0.16) / 0.5),
                  transform: `translateY(${(1 - clamp((formP - i * 0.16) / 0.5)) * 12}px)`,
                }}
              >
                <span
                  style={{
                    fontFamily: FONT,
                    fontWeight: 700,
                    fontSize: 92,
                    lineHeight: 1,
                    color: C.ink,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {p.t}
                </span>
                <span
                  style={{
                    fontFamily: FONT,
                    fontSize: 34,
                    color: "rgba(139,147,167,0.9)",
                    marginBottom: 10,
                  }}
                >
                  {p.unit}
                </span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 26, height: 1, width: 420, background: "rgba(255,255,255,0.12)" }} />
          <div
            style={{
              marginTop: 22,
              fontFamily: FONT,
              fontSize: 40,
              letterSpacing: 2,
              color: C.gold,
              fontVariantNumeric: "tabular-nums",
              textShadow: "0 0 40px rgba(243,193,75,0.3)",
            }}
          >
            {answer}
          </div>
          <div
            style={{
              marginTop: 34,
              width: 560,
              fontFamily: FONT,
              fontSize: 21,
              lineHeight: 1.8,
              letterSpacing: 1,
              color: "rgba(139,147,167,0.72)",
            }}
          >
            {note}
          </div>
        </div>

        {/* 横过来之后：问一句长度（放在线上方，别和算式叠） */}
        <div
          style={{
            position: "absolute",
            left: 300,
            top: 596,
            opacity: askP,
            transform: `translateY(${(1 - askP) * 14}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: 76,
              fontWeight: 700,
              color: C.ink,
              letterSpacing: 4,
            }}
          >
            长度 = <span style={{ color: C.gold }}>?</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
