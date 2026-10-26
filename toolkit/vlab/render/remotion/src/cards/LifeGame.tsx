import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { alive, findGlider, LIFE_H, LIFE_W, runLife } from "../lib/life";

type Props = {
  kicker?: string;
  title?: string;
  /** 整个镜头演到第几代 */
  gens?: number;
  /** 演化代数（默认算到恰好能看到滑翔机之后一段） */
  sim?: number;
};

const CELL = 16;
const OX = (1080 - LIFE_W * CELL) / 2;
const OY = 1080 - (LIFE_H * CELL) / 2;

// 缓存的演化结果：同一份数据给所有帧用，避免每帧重算 130 代
let CACHE: ReturnType<typeof runLife> | null = null;
function grids(sim: number) {
  if (!CACHE || CACHE.length < sim + 1) CACHE = runLife(sim);
  return CACHE;
}

// 生命游戏网格：从 5 个细胞开始真演化，逐帧推进代数，
// 滑翔机是在演化结果里搜出来的，不是画上去的。
export const LifeGame: React.FC<Props> = ({
  kicker = "5 CELLS → 130 GENERATIONS",
  title = "规则只有四条",
  gens = 130,
  sim = 200,
}) => {
  const frame = useCurrentFrame();
  const all = grids(sim);
  const gen = Math.min(gens, Math.floor((frame / 150) * gens) + 0);
  const grid = all[Math.min(gen, all.length - 1)];
  const cells = alive(grid);
  const hit = React.useMemo(() => findGlider(all), [all]);

  // 命中之后高亮那 3x3 窗口
  const showHit = hit && gen >= hit.gen;
  const hudP = interpolate(frame, [10, 26], [0, 1], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        {/* 网格底 */}
        {Array.from({ length: LIFE_W + 1 }, (_, i) => (
          <line
            key={`v${i}`}
            x1={OX + i * CELL}
            y1={OY}
            x2={OX + i * CELL}
            y2={OY + LIFE_H * CELL}
            stroke="rgba(255,255,255,0.045)"
            strokeWidth={1}
          />
        ))}
        {Array.from({ length: LIFE_H + 1 }, (_, i) => (
          <line
            key={`h${i}`}
            x1={OX}
            y1={OY + i * CELL}
            x2={OX + LIFE_W * CELL}
            y2={OY + i * CELL}
            stroke="rgba(255,255,255,0.045)"
            strokeWidth={1}
          />
        ))}
        {cells.map(([x, y], i) => (
          <rect
            key={`${x}-${y}-${i}`}
            x={OX + x * CELL + 1}
            y={OY + y * CELL + 1}
            width={CELL - 2}
            height={CELL - 2}
            rx={2}
            fill={C.gold}
            opacity={0.82}
          />
        ))}
        {showHit && (
          <>
            <rect
              x={OX + hit.x * CELL - 3}
              y={OY + hit.y * CELL - 3}
              width={CELL * 3 + 6}
              height={CELL * 3 + 6}
              fill="none"
              stroke={C.cyan}
              strokeWidth={2}
              opacity={0.9}
            />
            <circle cx={OX + (hit.x + 1.5) * CELL} cy={OY + (hit.y + 1.5) * CELL} r={CELL * 2.4} fill="none" stroke={C.cyan} strokeWidth={1} opacity={0.35} />
          </>
        )}
      </svg>

      <div style={{ position: "absolute", left: 96, top: 300, opacity: hudP }}>
        <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 8, color: C.cyan }}>{kicker}</div>
        <div style={{ fontFamily: FONT, fontSize: 48, fontWeight: 700, color: C.ink, marginTop: 14 }}>
          {title}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          right: 96,
          top: 300,
          textAlign: "right",
          opacity: hudP,
          fontFamily: FONT,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        <div style={{ fontSize: 18, letterSpacing: 6, color: C.dim }}>GENERATION</div>
        <div style={{ fontSize: 66, fontWeight: 700, color: C.gold, lineHeight: 1.1 }}>{gen}</div>
      </div>

      {showHit && (
        <div
          style={{
            position: "absolute",
            left: 96,
            bottom: 250,
            fontFamily: FONT,
            fontSize: 26,
            letterSpacing: 2,
            color: C.cyan,
            opacity: 0.85,
          }}
        >
          GLIDER FOUND · GEN {hit.gen} · ({hit.x}, {hit.y})
        </div>
      )}
    </AbsoluteFill>
  );
};
