import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 章四的主图：一张"厚度—折数"图，纵轴是线性的（0 → 439,805 公里）。
// 前 36 折在图上就是贴着底边的一条线——这不是画错了，这就是全部意思。
// 所以这张卡有三种说法：
//   fill="first30" 前 30 折只占 0.02%，一根头发丝
//   fill="last12"  最后 12 折吃掉剩下的 99.98%
//   fill="gap"     停在第 41 折（正好一半），上面还差 21.9 万
// inset 为真时，左下角浮一个小窗口：把那一段拉长 40 倍，每一格仍然 ×2。

type Props = {
  kicker?: string;
  note?: string;
  /** 画到第几折（曲线头部） */
  stop?: number;
  fill?: "none" | "first30" | "last12" | "gap";
  /** 左下角的放大窗口 */
  inset?: boolean;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const X0 = 250;
const X1 = 1690;
const Y0 = 832;   // 0
const Y1 = 214;   // 439,805 km
const TOTAL = 42;
const MAX = Math.pow(2, TOTAL) - 1;

const xOf = (n: number) => X0 + ((X1 - X0) * n) / TOTAL;
// 线性纵轴：2ⁿ−1 归一化。前 30 折在这里是 0.012% —— 真的就是贴着底边。
const yOf = (n: number) => Y0 + (Y1 - Y0) * ((Math.pow(2, n) - 1) / MAX);

const path = (from: number, to: number) => {
  const pts: string[] = [];
  for (let n = from; n <= to; n += 1) pts.push(`${n === from ? "M" : "L"}${xOf(n).toFixed(1)} ${yOf(n).toFixed(1)}`);
  return pts.join(" ");
};

export const FoldCurve: React.FC<Props> = ({
  kicker = "04 · 平　THE FLAT PART",
  note = "纵轴是线性的。前 36 折在图上贴着底边 —— 不是没长，是我们看不见。",
  stop = 42,
  fill = "none",
  inset = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();

  const axisP = ease((frame - 2) / (fps * 0.6));
  // 曲线从头画到尾：这条线本身要有"过程"，不能一上来就是结果
  const drawP = ease((frame - Math.round(fps * 0.35)) / (fps * 1.5));
  const head = Math.max(0, Math.round(drawP * stop));
  const fillP = ease((frame - Math.round(fps * 0.9)) / (fps * 0.9));
  const insetP = inset ? ease((frame - Math.round(fps * 1.1)) / (fps * 0.8)) : 0;

  const fillFrom = fill === "last12" ? 30 : 0;
  const fillTo = fill === "first30" ? 30 : 42;

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
        {/* 坐标轴 */}
        <div style={{ opacity: axisP }}>
          <div
            style={{
              position: "absolute",
              left: X0,
              top: Y1 - 14,
              width: 1,
              height: Y0 - Y1 + 14,
              background: "rgba(255,255,255,0.18)",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: X0,
              top: Y0,
              width: X1 - X0,
              height: 1,
              background: "rgba(255,255,255,0.22)",
            }}
          />
          {/* 横向网格：每 10% 一条，帮助看清"底边那条线"有多低 */}
          {[0.25, 0.5, 0.75].map((f) => (
            <div
              key={f}
              style={{
                position: "absolute",
                left: X0,
                top: Y0 - (Y0 - Y1) * f,
                width: X1 - X0,
                height: 1,
                background: "rgba(255,255,255,0.05)",
              }}
            />
          ))}
          {/* x 轴刻度 */}
          {[0, 10, 20, 30, 42].map((n) => (
            <div key={n}>
              <div
                style={{
                  position: "absolute",
                  left: xOf(n),
                  top: Y0,
                  width: 1,
                  height: 14,
                  background: "rgba(255,255,255,0.24)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: xOf(n) - 30,
                  top: Y0 + 22,
                  width: 60,
                  textAlign: "center",
                  fontFamily: FONT,
                  fontSize: 22,
                  letterSpacing: 1,
                  color: n === 42 ? C.gold : "rgba(139,147,167,0.8)",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {n}
              </div>
            </div>
          ))}
          <div
            style={{
              position: "absolute",
              left: X0,
              top: Y0 + 66,
              fontFamily: FONT,
              fontSize: 20,
              letterSpacing: 6,
              color: "rgba(139,147,167,0.55)",
            }}
          >
            折数
          </div>
          {/* y 轴标注 */}
          {/* y 轴标注：必须停在轴线左侧（原来 right 对齐到 X0-24+width，压到轴上去了） */}
          <div
            style={{
              position: "absolute",
              left: 0,
              top: Y0 - 16,
              width: X0 - 16,
              textAlign: "right",
              fontFamily: FONT,
              fontSize: 20,
              letterSpacing: 1,
              color: "rgba(139,147,167,0.7)",
            }}
          >
            0
          </div>
          <div
            style={{
              position: "absolute",
              left: 0,
              top: Y1 - 16,
              width: X0 - 16,
              textAlign: "right",
              fontFamily: FONT,
              fontSize: 20,
              letterSpacing: 1,
              color: "rgba(139,147,167,0.7)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            439,805 公里
          </div>
        </div>

        {/* 填充 */}
        {fill !== "none" ? (
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              width: 1920,
              height: 1080,
              opacity: fillP,
            }}
          >
            <svg width={1920} height={1080}>
              <defs>
                <linearGradient id="fillGold" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(243,193,75,0.55)" />
                  <stop offset="100%" stopColor="rgba(243,193,75,0.04)" />
                </linearGradient>
              </defs>
              <path
                d={`${path(fillFrom, fillTo)} L${xOf(fillTo).toFixed(1)} ${Y0} L${xOf(fillFrom).toFixed(
                  1,
                )} ${Y0} Z`}
                fill="url(#fillGold)"
                stroke="none"
              />
            </svg>
          </div>
        ) : null}

        {/* 曲线 */}
        <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
          <path
            d={path(0, stop)}
            fill="none"
            stroke={C.gold}
            strokeWidth={3}
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - drawP}
            style={{ filter: "drop-shadow(0 0 14px rgba(243,193,75,0.55))" }}
          />
        </svg>

        {/* 曲线头：一个小亮点 + 当前折数 */}
        {drawP < 1 ? (
          <div
            style={{
              position: "absolute",
              left: xOf(head) - 6,
              top: yOf(head) - 6,
              width: 12,
              height: 12,
              borderRadius: 6,
              background: "#fff3d0",
              boxShadow: "0 0 26px rgba(255,226,150,0.95)",
            }}
          />
        ) : null}

        {/* 停在第 41 折：上面那一截用虚线标出来 */}
        {fill === "gap" ? (
          <div style={{ opacity: fillP }}>
            <div
              style={{
                position: "absolute",
                left: xOf(41),
                top: Y1,
                width: 1,
                height: yOf(41) - Y1,
                background:
                  "repeating-linear-gradient(180deg, rgba(255,91,91,0.8) 0 6px, rgba(255,91,91,0) 6px 13px)",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: xOf(41) - 350,
                top: (Y1 + yOf(41)) / 2 - 16,
                width: 330,
                textAlign: "right",
                fontFamily: FONT,
                fontSize: 30,
                letterSpacing: 2,
                color: C.red,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              还差 219,902 公里
            </div>
          </div>
        ) : null}

        {/* 0.02% / 99.98% 的注脚 */}
        {fill === "first30" ? (
          <div
            style={{
              position: "absolute",
              left: X0 + 20,
              top: Y0 - 210,
              opacity: fillP,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: 84,
                lineHeight: 1,
                color: C.gold,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              0.02%
            </div>
            <div
              style={{
                marginTop: 10,
                fontFamily: FONT,
                fontSize: 24,
                letterSpacing: 2,
                color: "rgba(139,147,167,0.9)",
              }}
            >
              前 30 折，只走了全程的万分之二
            </div>
            {/* 指向底边那根"头发丝" */}
            <div
              style={{
                marginTop: 22,
                marginLeft: 4,
                width: 1,
                height: 138,
                background: "linear-gradient(180deg, rgba(243,193,75,0.7), rgba(243,193,75,0))",
              }}
            />
          </div>
        ) : null}

        {fill === "last12" ? (
          <div
            style={{
              position: "absolute",
              right: 200,
              top: Y1 + 46,
              textAlign: "right",
              opacity: fillP,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: 84,
                lineHeight: 1,
                color: C.gold,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              99.98%
            </div>
            <div
              style={{
                marginTop: 10,
                fontFamily: FONT,
                fontSize: 24,
                letterSpacing: 2,
                color: "rgba(139,147,167,0.9)",
              }}
            >
              最后 12 折，把图填满了
            </div>
          </div>
        ) : null}

        {/* 左下角放大窗口：把贴着底边那段拉长。
            在对数尺上，“每折 ×2”就是一条 45° 的直线 —— 这比一排柱子好读。 */}
        {inset ? (
          <>
            {/* 一根虚线从底边那段搭到窗口，说明“就是这一段” */}
            <svg
              width={1920}
              height={1080}
              style={{ position: "absolute", left: 0, top: 0, opacity: insetP * 0.65 }}
            >
              <path
                d={`M ${xOf(8)} ${Y0 - 4} L ${xOf(8)} ${Y0 - 26} L ${X0 + 40} ${Y0 - 26} L ${X0 + 40} 470`}
                fill="none"
                stroke="rgba(73,227,209,0.5)"
                strokeDasharray="5 6"
              />
            </svg>
            <div
              style={{
                position: "absolute",
                left: X0 + 10,
                top: 470,
                width: 620,
                height: 330,
                opacity: insetP,
                transform: `translateY(${(1 - insetP) * 16}px)`,
                border: "1px solid rgba(73,227,209,0.30)",
                background: "rgba(6,10,18,0.9)",
                boxShadow: "0 30px 80px rgba(0,0,0,0.6)",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: 20,
                  top: 16,
                  fontFamily: FONT,
                  fontSize: 20,
                  letterSpacing: 5,
                  color: C.cyan,
                }}
              >
                前 12 折 · 对数尺上
              </div>
              {/* 45° 直线 + 等距的 12 个点 */}
              <svg width={620} height={330} style={{ position: "absolute", inset: 0 }}>
                <line x1={60} y1={252} x2={560} y2={92} stroke="rgba(243,193,75,0.85)" strokeWidth={2} />
                {Array.from({ length: 12 }, (_, i) => (
                  <circle
                    key={i}
                    cx={60 + (500 * i) / 11}
                    cy={252 - (160 * i) / 11}
                    r={i === 11 ? 5 : 3}
                    fill={i === 11 ? C.gold : "rgba(246,242,231,0.9)"}
                  />
                ))}
                <line x1={60} y1={252} x2={560} y2={252} stroke="rgba(255,255,255,0.16)" strokeWidth={1} />
              </svg>
              <div
                style={{
                  position: "absolute",
                  left: 60,
                  top: 268,
                  fontFamily: FONT,
                  fontSize: 21,
                  letterSpacing: 2,
                  color: "rgba(139,147,167,0.85)",
                }}
              >
                格子等距，因为纵轴取了对数 · 每格 ×2
              </div>
            </div>
          </>
        ) : null}

        {/* 章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(axisP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>{kicker}</div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 出处：放右上，别去挤字幕。宽度给够 —— 太窄会把最后三个字单独甩到第二行 */}
        <div
          style={{
            position: "absolute",
            right: 110,
            top: 150,
            width: 660,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 20,
            lineHeight: 1.7,
            letterSpacing: 1,
            color: "rgba(139,147,167,0.6)",
            opacity: axisP,
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
