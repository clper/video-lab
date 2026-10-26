import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { FlockOpts, simulate, threatAt } from "../lib/flock";

type Props = {
  kicker?: string;
  title?: string;
  readout?: string;
  n?: number;
  seed?: number;
  birth?: boolean;
  threat?: FlockOpts["threat"];
  collapseAt?: number | null;
  /** 近景：相机跟着鸟群走 */
  closeup?: boolean;
  /** 崩散后整体转红 */
  red?: boolean;
};

// 鸟群镜头：S1 出生、S3 遇险、S4 近景、S11 崩散，全都是同一套 boids 换参数/换 uniform，
// 不重写第二套模拟 —— 这也是"同一批粒子演灾难"的做法。
export const Flock: React.FC<Props> = ({
  kicker,
  title,
  readout,
  n = 640,
  seed = 1987,
  birth = false,
  threat = null,
  collapseAt = null,
  closeup = false,
  red = false,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const steps = Math.max(2, durationInFrames);

  const frames = React.useMemo(() => {
    const opts: FlockOpts = {
      n,
      steps,
      seed,
      birth,
      threat,
      collapseAt,
      start: birth ? [540, 1080] : [540, 900],
    };
    return simulate(opts);
  }, [n, steps, seed, birth, threat, collapseAt]);

  const birds = frames[Math.min(frame, frames.length - 1)] ?? [];
  const tp = threatAt({ threat }, frame);

  // 相机：近景时放大并跟住群体中心
  let cx = 540;
  let cy = 960;
  if (birds.length) {
    cx = birds.reduce((s, b) => s + b.x, 0) / birds.length;
    cy = birds.reduce((s, b) => s + b.y, 0) / birds.length;
  }
  const camScale = closeup ? interpolate(frame, [0, 30], [1.35, 2.05], { extrapolateRight: "clamp" }) : 1;
  // 变换是 translate 再 scale（屏幕点 = camX + s*世界点），所以要把群体中心搬到画面中心：
  // camX = 540 - s*cx。少乘这个 s 会把鸟群推到画外，近景看起来像空镜。
  const camX = closeup ? 540 - camScale * cx : 0;
  const camY = closeup ? 960 - camScale * cy : 0;

  // 近景加少量"邻居连线"，密度感来自线而不是点
  const links: Array<[number, number]> = [];
  if (closeup) {
    const stride = Math.max(1, Math.floor(birds.length / 70));
    for (let i = 0; i < birds.length && links.length < 70; i += stride) {
      for (let j = i + stride; j < birds.length; j += stride) {
        const dx = birds[i].x - birds[j].x;
        const dy = birds[i].y - birds[j].y;
        if (dx * dx + dy * dy < 58 * 58) {
          links.push([i, j]);
          if (links.length >= 70) break;
        }
      }
    }
  }

  const boost = collapseAt != null ? Math.max(0, Math.min(1, (frame - collapseAt * 0.6) / 40)) : 0;
  const birdColor = red || boost > 0.5 ? C.red : C.ink;
  const hudP = interpolate(frame, [8, 24], [0, 1], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <g transform={`translate(${camX} ${camY}) scale(${camScale})`}>
          {links.map(([i, j], k) => (
            <line
              key={k}
              x1={birds[i].x}
              y1={birds[i].y}
              x2={birds[j].x}
              y2={birds[j].y}
              stroke={C.cyan}
              strokeWidth={1}
              opacity={0.18}
            />
          ))}
          {birds.map((b, i) => {
            const ang = (Math.atan2(b.vy, b.vx) * 180) / Math.PI;
            const speed = Math.hypot(b.vx, b.vy);
            if (speed < 0.05) return null;
            return (
              <path
                key={i}
                d="M -9 0 L 0 -4.4 L 9 0 L 0 4.4 Z"
                transform={`translate(${b.x} ${b.y}) rotate(${ang})`}
                fill={birdColor}
                opacity={0.72}
              />
            );
          })}
        </g>
        {tp && (
          <g>
            <circle cx={tp[0]} cy={tp[1]} r={30} fill="none" stroke={C.red} strokeWidth={2} opacity={0.85} />
            <circle cx={tp[0]} cy={tp[1]} r={13} fill={C.red} opacity={0.9} />
            <circle cx={tp[0]} cy={tp[1]} r={54} fill="none" stroke={C.red} strokeWidth={1} opacity={0.35} />
          </g>
        )}
      </svg>

      {(kicker || title) && (
        <div style={{ position: "absolute", left: 96, top: 320, opacity: hudP }}>
          {kicker && (
            <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 9, color: C.cyan }}>{kicker}</div>
          )}
          {title && (
            <div style={{ fontFamily: FONT, fontSize: 52, fontWeight: 700, color: C.ink, marginTop: 14 }}>
              {title}
            </div>
          )}
        </div>
      )}

      {readout && (
        <div
          style={{
            position: "absolute",
            left: 96,
            bottom: 300,
            fontFamily: FONT,
            fontSize: 26,
            letterSpacing: 3,
            color: C.gold,
            fontVariantNumeric: "tabular-nums",
            opacity: interpolate(frame, [18, 34], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {readout}
        </div>
      )}
    </AbsoluteFill>
  );
};
