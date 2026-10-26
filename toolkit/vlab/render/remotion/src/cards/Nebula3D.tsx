import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { mulberry32 } from "../common/random";

type Props = {
  kicker?: string;
  title?: string;
  note?: string;
  seed?: number;
  count?: number;
};

type Star = { x: number; y: number; z: number; s: number; g: number };

// 3D 星云：一段对数螺旋上的点云，绕 Y 轴慢转，按深度做透视投影和亮度。
// 用 SVG 而不是 canvas，是为了让每一帧都由 React 声明式算出来（不依赖命令式的绘制时机）。
const FOCAL = 1180;
// 倾角：-0.42 时 z 方向的深度几乎被压平，整团星云就成了一条横带（看不出 3D）。
// 约 54°（-0.95）让螺旋盘面展开成近圆的椭圆，透视才读得出来。
const TILT = -0.95;

export const Nebula3D: React.FC<Props> = ({
  kicker = "ONE RULE, ONE NETWORK",
  title = "没有中心，只有密度",
  note = "局部的密度，就是全局的形状",
  seed = 41,
  count = 920,
}) => {
  const frame = useCurrentFrame();
  const rot = frame * 0.011;

  const stars: Star[] = React.useMemo(() => {
    const rnd = mulberry32(seed);
    return Array.from({ length: count }, () => {
      const arm = Math.floor(rnd() * 3);
      const r = Math.pow(rnd(), 0.62) * 430;
      const a = (arm * Math.PI * 2) / 3 + r * 0.017 + (rnd() - 0.5) * 0.9;
      return {
        x: Math.cos(a) * r,
        y: (rnd() - 0.5) * (34 + r * 0.2),
        z: Math.sin(a) * r,
        s: 0.8 + rnd() * 2.2,
        g: rnd(),
      };
    });
  }, [seed, count]);

  const cos = Math.cos(rot);
  const sin = Math.sin(rot);
  const cosT = Math.cos(TILT);
  const sinT = Math.sin(TILT);

  const proj = stars.map((s) => {
    const x1 = s.x * cos - s.z * sin;
    const z1 = s.x * sin + s.z * cos;
    const y1 = s.y * cosT - z1 * sinT;
    const z2 = s.y * sinT + z1 * cosT;
    const k = FOCAL / (FOCAL + z2 + 520);
    return { px: 540 + x1 * k, py: 960 + y1 * k - 120, r: s.s * k, k, g: s.g };
  });
  proj.sort((a, b) => a.k - b.k);

  const enter = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, opacity: enter }}>
        <defs>
          {/* 核心辉光：只有散点的时候像“噪点”，有一层极淡的辉光才像星云 */}
          <radialGradient id="nebulaCore">
            <stop offset="0%" stopColor={C.gold} stopOpacity={0.22} />
            <stop offset="45%" stopColor={C.gold} stopOpacity={0.07} />
            <stop offset="100%" stopColor={C.gold} stopOpacity={0} />
          </radialGradient>
        </defs>
        <ellipse cx={540} cy={840} rx={560} ry={440} fill="url(#nebulaCore)" />
        {proj.map((p, i) => {
          const deep = Math.max(0, Math.min(1, (p.k - 0.55) / 0.9));
          const color = p.g > 0.93 ? C.cyan : p.g > 0.86 ? C.magenta : C.gold;
          return (
            <circle
              key={i}
              cx={p.px}
              cy={p.py}
              r={p.r}
              fill={color}
              opacity={0.16 + deep * 0.78}
            />
          );
        })}
      </svg>

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 250,
          textAlign: "center",
          opacity: interpolate(frame, [26, 46], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 24, letterSpacing: 12, color: C.cyan }}>{kicker}</div>
        <div style={{ fontFamily: FONT, fontSize: 54, fontWeight: 700, color: C.ink, marginTop: 20 }}>
          {title}
        </div>
        <div style={{ fontFamily: FONT, fontSize: 30, color: C.dim, marginTop: 16 }}>{note}</div>
      </div>
    </AbsoluteFill>
  );
};
