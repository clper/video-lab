import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 章四第一镜：把银河摊在桌上，旁边放一把同宽的尺。
// 不画旋臂细节，只画两层：一层是雾（亮核 + 尘带），一层是星。
// 尺和银河等宽，所以"10 万光年"这句不是读出来的，是量出来的。

type Props = {
  kicker?: string;
  note?: string;
  /** 尺量到多宽：单位光年 */
  lightYears?: number;
  /** 折数 */
  folds?: number;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const CX = 960;
const CY = 428;
const RW = 700; // 银河长半径
const RH = 232; // 银河短半径
const ROT = -17;

// 稳定的伪随机：同一个 i 每次都一样，不要用 Math.random
const rnd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

export const FoldGalaxy: React.FC<Props> = ({
  kicker = "04 · 平　THE FLAT PART",
  note = "银河系直径约 10 万光年（估计）。42 折叠起来，和它一样宽。",
  lightYears = 100000,
  folds = 42,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const fogP = ease((frame - 2) / (fps * 1.1));
  const starP = ease((frame - Math.round(fps * 0.5)) / (fps * 1.2));
  const rulerP = ease((frame - Math.round(fps * 1.2)) / (fps * 0.9));
  const readP = ease((frame - Math.round(fps * 1.6)) / (fps * 0.7));

  const stars = Array.from({ length: 150 }, (_, i) => {
    const a = rnd(i) * Math.PI * 2;
    const r = Math.sqrt(rnd(i + 99)) ; // 往中心聚
    return {
      x: CX + Math.cos(a) * RW * r * (0.98 + rnd(i + 7) * 0.06),
      y: CY + Math.sin(a) * RH * r * (0.98 + rnd(i + 13) * 0.06),
      o: 0.16 + rnd(i + 21) * 0.55,
      d: 18 + rnd(i + 31) * 42,
    };
  });

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
        {/* 银河本体：先一团雾 */}
        <div
          style={{
            position: "absolute",
            left: CX - RW,
            top: CY - RH,
            width: RW * 2,
            height: RH * 2,
            transform: `rotate(${ROT}deg) scaleY(${0.96 + 0.04 * fogP})`,
            opacity: fogP,
          }}
        >
          {/* 外圈雾 */}
          <div
            style={{
              position: "absolute",
              inset: -80,
              background:
                "radial-gradient(ellipse at 50% 50%, rgba(150,180,235,0.20) 0%, rgba(120,150,215,0.10) 42%, rgba(90,120,190,0.03) 68%, rgba(0,0,0,0) 82%)",
              filter: "blur(14px)",
            }}
          />
          {/* 盘子 */}
          <div
            style={{
              position: "absolute",
              inset: 40,
              borderRadius: "50%",
              background:
                "radial-gradient(ellipse at 50% 50%, rgba(255,248,226,0.92) 0%, rgba(255,236,190,0.62) 8%, rgba(214,196,220,0.34) 22%, rgba(130,160,225,0.18) 48%, rgba(70,95,160,0.05) 72%, rgba(0,0,0,0) 88%)",
              filter: "blur(3px)",
            }}
          />
          {/* 两条旋臂：只给两道弧，够读出"螺旋"了 */}
          <svg width={RW * 2} height={RH * 2} style={{ position: "absolute", inset: 0 }}>
            <g fill="none" strokeLinecap="round">
              {[0, Math.PI].map((off, k) => (
                <path
                  key={k}
                  d={(() => {
                    const pts: string[] = [];
                    for (let i = 0; i <= 26; i += 1) {
                      const t = i / 26;
                      const a = off + t * 2.0;
                      const rr = 0.16 + t * 0.82;
                      const x = RW + Math.cos(a) * RW * rr;
                      const y = RH + Math.sin(a) * RH * rr * 0.98;
                      pts.push(`${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`);
                    }
                    return pts.join(" ");
                  })()}
                  stroke="rgba(190,210,255,0.26)"
                  strokeWidth={38 - k * 4}
                  opacity={0.5}
                  style={{ filter: "blur(16px)" }}
                />
              ))}
              {/* 尘带：中间那道暗 */}
              <ellipse
                cx={RW}
                cy={RH}
                rx={RW * 0.92}
                ry={RH * 0.5}
                fill="none"
                stroke="rgba(8,10,20,0.55)"
                strokeWidth={26}
                style={{ filter: "blur(12px)" }}
              />
            </g>
          </svg>
        </div>

        {/* 星 */}
        {stars.map((st, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: st.x,
              top: st.y,
              width: 2.4,
              height: 2.4,
              borderRadius: 2,
              background: i % 9 === 0 ? "#ffe6a8" : "#dce8ff",
              opacity: starP * st.o,
              boxShadow: "0 0 8px rgba(220,232,255,0.8)",
              transform: `translateY(${(1 - starP) * st.d}px)`,
            }}
          />
        ))}

        {/* 尺：和银河等宽 */}
        <div
          style={{
            position: "absolute",
            left: CX - RW,
            top: CY + RH + 34,
            width: RW * 2 * rulerP,
            height: 2,
            background: "linear-gradient(90deg, rgba(255,255,255,0.42), rgba(255,255,255,0.18))",
          }}
        />
        {Array.from({ length: 11 }, (_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: CX - RW + (RW * 2 * i) / 10,
              top: CY + RH + 34,
              width: 1,
              height: i % 5 === 0 ? 26 : 14,
              background: i % 5 === 0 ? "rgba(255,255,255,0.42)" : "rgba(255,255,255,0.2)",
              opacity: rulerP,
            }}
          />
        ))}
        <div
          style={{
            position: "absolute",
            left: CX - RW,
            top: CY + RH + 74,
            fontFamily: FONT,
            fontSize: 22,
            letterSpacing: 3,
            color: "rgba(139,147,167,0.8)",
            opacity: rulerP,
          }}
        >
          0
        </div>
        <div
          style={{
            position: "absolute",
            left: CX + RW - 40,
            top: CY + RH + 74,
            width: 160,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 22,
            letterSpacing: 3,
            color: "rgba(139,147,167,0.8)",
            opacity: rulerP,
          }}
        >
          光年
        </div>

        {/* 读数 */}
        <div
          style={{
            position: "absolute",
            left: CX - RW,
            top: CY + RH + 118,
            opacity: readP,
            transform: `translateY(${(1 - readP) * 14}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontWeight: 700,
              fontSize: 80,
              lineHeight: 1,
              color: C.gold,
              fontVariantNumeric: "tabular-nums",
              textShadow: "0 0 60px rgba(243,193,75,0.25)",
            }}
          >
            {lightYears.toLocaleString("en-US")}
            <span style={{ fontSize: 38, marginLeft: 12, color: C.ink, letterSpacing: 2 }}>光年</span>
            <span
              style={{
                fontSize: 24,
                marginLeft: 26,
                letterSpacing: 3,
                color: "rgba(139,147,167,0.9)",
              }}
            >
              第 {folds} 折 · 一张纸的宽度
            </span>
          </div>
          <div style={{ height: 0 }} />
        </div>

        {/* 章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(fogP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>{kicker}</div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 出处：右上，离开字幕区 */}
        <div
          style={{
            position: "absolute",
            right: 120,
            top: 150,
            width: 460,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 20,
            lineHeight: 1.7,
            letterSpacing: 1,
            color: "rgba(139,147,167,0.55)",
            opacity: fogP,
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
