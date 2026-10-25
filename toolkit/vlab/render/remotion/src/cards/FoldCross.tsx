import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 一张纸折一次的剖面：两条胳膊 + 一个半圆的弯。
// 外圈要绕更远的路，内圈挤在一起——不是手劲问题，是几何。
// 这一镜全片只出现一次，所以画得实一点：纸的填充、纤维环、红蓝两段弧都在说话。

type Props = {
  kicker?: string;
  /** 弯有多厚（像素） */
  thickness?: number;
  /** 底部小字 */
  note?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const CX = 560; // 弯的圆心 x
const CY = 500; // 弯的圆心 y
const R_OUT = 200;
const ARM_X = 170;

export const FoldCross: React.FC<Props> = ({
  kicker = "一次对折 · 剖面",
  thickness = 96,
  note = "层数越多，外圈要包的路越长；包不动的那一下，就是极限。",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const inP = ease((frame - 2) / (fps * 0.5));
  const redP = ease((frame - Math.round(fps * 0.45)) / (fps * 0.55));
  const cyanP = ease((frame - Math.round(fps * 0.7)) / (fps * 0.5));
  const textP = ease((frame - Math.round(fps * 0.8)) / (fps * 0.5));

  const rIn = R_OUT - thickness;
  const topY = CY - R_OUT;
  const botY = CY + R_OUT;
  const inTopY = CY - rIn;
  const inBotY = CY + rIn;

  // 一条胳膊 + 半圆弯 + 另一条胳膊，中间挖掉内圈
  const section = [
    `M ${ARM_X} ${topY}`,
    `L ${CX} ${topY}`,
    `A ${R_OUT} ${R_OUT} 0 0 1 ${CX} ${botY}`,
    `L ${ARM_X} ${botY}`,
    `L ${ARM_X} ${inBotY}`,
    `L ${CX} ${inBotY}`,
    `A ${rIn} ${rIn} 0 0 0 ${CX} ${inTopY}`,
    `L ${ARM_X} ${inTopY}`,
    `Z`,
  ].join(" ");

  // 弯里那几道纤维环
  const fibers = [0.2, 0.4, 0.6, 0.8].map((f) => {
    const r = rIn + thickness * f;
    return `M ${CX} ${CY - r} A ${r} ${r} 0 0 1 ${CX} ${CY + r}`;
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
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 118,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 8,
            color: C.cyan,
            opacity: inP,
          }}
        >
          {kicker}
        </div>

        <svg
          width={1920}
          height={1080}
          style={{ position: "absolute", left: 0, top: 0 }}
        >
          <defs>
            <linearGradient id="foldPaper" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fffdf6" />
              <stop offset="55%" stopColor="#f8f2e4" />
              <stop offset="100%" stopColor="#e6dcc4" />
            </linearGradient>
          </defs>

          {/* 剖面本体 */}
          <path
            d={section}
            fill="url(#foldPaper)"
            stroke="rgba(255,250,235,0.7)"
            strokeWidth={1}
            opacity={inP}
          />
          {/* 纤维环 */}
          <g opacity={inP * 0.5}>
            {fibers.map((d, i) => (
              <path key={i} d={d} fill="none" stroke="#c9b899" strokeWidth={1.2} />
            ))}
          </g>

          {/* 外圈：红 */}
          <path
            d={`M ${CX} ${CY - R_OUT - 26} A ${R_OUT + 26} ${R_OUT + 26} 0 0 1 ${CX} ${CY + R_OUT + 26}`}
            fill="none"
            stroke={C.red}
            strokeWidth={2}
            strokeDasharray="7 7"
            opacity={redP * 0.9}
          />
          {/* 内圈：冰蓝 */}
          <path
            d={`M ${CX} ${CY - rIn + 20} A ${rIn - 20} ${rIn - 20} 0 0 1 ${CX} ${CY + rIn - 20}`}
            fill="none"
            stroke={C.cyan}
            strokeWidth={2}
            strokeDasharray="5 6"
            opacity={cyanP * 0.9}
          />

          {/* 引线：外圈 */}
          <g opacity={redP}>
            <path
              d={`M ${CX + 120} ${CY - 196} L ${CX + 190} ${CY - 250} L ${CX + 246} ${CY - 250}`}
              fill="none"
              stroke={C.red}
              strokeWidth={1}
              opacity={0.6}
            />
            <text
              x={CX + 258}
              y={CY - 242}
              fill={C.red}
              fontFamily={FONT}
              fontSize={26}
              letterSpacing={3}
            >
              外圈
            </text>
            <text
              x={CX + 258}
              y={CY - 208}
              fill="rgba(255,91,91,0.72)"
              fontFamily={FONT}
              fontSize={20}
              letterSpacing={1}
            >
              绕的路更长
            </text>
          </g>

          {/* 引线：内圈 */}
          <g opacity={cyanP}>
            <path
              d={`M ${CX + 60} ${CY - 40} L ${CX + 190} ${CY + 30} L ${CX + 246} ${CY + 30}`}
              fill="none"
              stroke={C.cyan}
              strokeWidth={1}
              opacity={0.6}
            />
            <text
              x={CX + 258}
              y={CY + 38}
              fill={C.cyan}
              fontFamily={FONT}
              fontSize={26}
              letterSpacing={3}
            >
              内圈
            </text>
            <text
              x={CX + 258}
              y={CY + 72}
              fill="rgba(73,227,209,0.72)"
              fontFamily={FONT}
              fontSize={20}
              letterSpacing={1}
            >
              挤在一起，先起皱
            </text>
          </g>
        </svg>

        {/* 右下：三行结论，一镜只给一句话 */}
        <div
          style={{
            position: "absolute",
            left: 1180,
            top: 636,
            width: 600,
            opacity: textP,
          }}
        >
          <div style={{ height: 1, width: 300, background: "rgba(255,255,255,0.14)" }} />
          <div
            style={{
              marginTop: 22,
              fontFamily: FONT,
              fontSize: 30,
              lineHeight: 1.8,
              letterSpacing: 1,
              color: "rgba(248,242,228,0.92)",
            }}
          >
            外圈比内圈多走一截。
            <br />
            这一截，随层数一起翻倍。
          </div>
          <div
            style={{
              marginTop: 26,
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

        {/* 剖面下方：它不是一张，是一叠 */}
        <div
          style={{
            position: "absolute",
            left: ARM_X,
            top: botY + 54,
            fontFamily: FONT,
            fontSize: 21,
            letterSpacing: 3,
            color: "rgba(139,147,167,0.6)",
            opacity: textP,
          }}
        >
          剖面示意 · 实际弯面比这复杂
        </div>
      </div>
    </AbsoluteFill>
  );
};
