import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";

type Props = {
  kicker?: string;
  title?: string;
  /** 曲线上的关键点（t 0-1，v 0-1），默认是一条冲高再断崖的崩盘曲线 */
  points?: Array<[number, number]>;
  dropLabel?: string;
  note?: string;
};

const BOX = { x: 130, y: 620, w: 830, h: 700 };

// 崩盘曲线：先画崖前的爬升，再让断崖自己"掉"下去。
// 图表类镜头的可信度全在细节：刻度、虚线投影、落点标注，缺一个就像示意图。
export const ChartCard: React.FC<Props> = ({
  kicker = "PHASE TRANSITION",
  title = "崩溃不是变慢，是一步跨过",
  points = [
    [0, 0.18],
    [0.2, 0.34],
    [0.4, 0.5],
    [0.55, 0.66],
    [0.68, 0.82],
    [0.74, 0.95],
    [0.78, 0.12],
    [0.86, 0.09],
    [1, 0.06],
  ],
  dropLabel = "-92%",
  note = "系统越过临界点后，恢复力小于扰动力",
}) => {
  const frame = useCurrentFrame();

  const px = (t: number) => BOX.x + t * BOX.w;
  const py = (v: number) => BOX.y + BOX.h - v * BOX.h;

  const d = points.map(([t, v], i) => `${i === 0 ? "M" : "L"} ${px(t)} ${py(v)}`).join(" ");
  const area = `${d} L ${px(1)} ${py(0)} L ${px(0)} ${py(0)} Z`;

  const draw = interpolate(frame, [6, 54], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const dropP = interpolate(frame, [40, 62], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const dropIdx = points.findIndex(([t], i) => i > 0 && points[i - 1][1] - points[i][1] > 0.4);
  const dropPoint = dropIdx > 0 ? points[dropIdx - 1] : points[Math.floor(points.length * 0.75)];
  const afterPoint = dropIdx > 0 ? points[dropIdx] : points[points.length - 1];
  const headP = interpolate(frame, [56, 76], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 96,
          top: 320,
          opacity: interpolate(frame, [0, 16], [0, 1], { extrapolateRight: "clamp" }),
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 9, color: C.cyan }}>{kicker}</div>
        <div style={{ fontFamily: FONT, fontSize: 48, fontWeight: 700, color: C.ink, marginTop: 14 }}>
          {title}
        </div>
      </div>

      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <linearGradient id="crashFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={C.red} stopOpacity={0.35} />
            <stop offset="100%" stopColor={C.red} stopOpacity={0} />
          </linearGradient>
        </defs>

        {/* 网格 + 刻度 */}
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <line
            key={v}
            x1={BOX.x}
            y1={py(v)}
            x2={BOX.x + BOX.w}
            y2={py(v)}
            stroke="rgba(255,255,255,0.07)"
            strokeWidth={1}
          />
        ))}
        <line x1={BOX.x} y1={BOX.y} x2={BOX.x} y2={BOX.y + BOX.h} stroke="rgba(255,255,255,0.22)" strokeWidth={1.5} />
        <line
          x1={BOX.x}
          y1={BOX.y + BOX.h}
          x2={BOX.x + BOX.w}
          y2={BOX.y + BOX.h}
          stroke="rgba(255,255,255,0.22)"
          strokeWidth={1.5}
        />

        <path d={area} fill="url(#crashFill)" opacity={draw} />
        <path
          d={d}
          fill="none"
          stroke={C.gold}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={2600}
          strokeDashoffset={2600 * (1 - draw)}
        />

        {/* 断崖：竖直虚线 + 标注 */}
        <line
          x1={px(dropPoint[0])}
          y1={py(dropPoint[1])}
          x2={px(dropPoint[0])}
          y2={py(afterPoint[1])}
          stroke={C.red}
          strokeWidth={2}
          strokeDasharray="8 8"
          opacity={dropP * 0.9}
        />
        <circle cx={px(afterPoint[0])} cy={py(afterPoint[1])} r={9} fill={C.red} opacity={dropP} />
        <text
          x={px(dropPoint[0]) + 24}
          y={py((dropPoint[1] + afterPoint[1]) / 2)}
          fill={C.red}
          fontFamily={FONT}
          fontSize={44}
          fontWeight={700}
          opacity={dropP}
        >
          {dropLabel}
        </text>
      </svg>

      <div
        style={{
          position: "absolute",
          left: BOX.x,
          bottom: 330,
          fontFamily: FONT,
          fontSize: 28,
          color: C.dim,
          opacity: headP,
        }}
      >
        {note}
      </div>
    </AbsoluteFill>
  );
};
