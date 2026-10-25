import React, { useMemo } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { mulberry32 } from "../common/random";

type Seg = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  depth: number;
  order: number;
};

type Pt = { x: number; y: number };

// 递归分叉出一张"网"：同一张图既能读成菌丝，也能读成地铁线路。
function buildTree(seed: number): Seg[] {
  const rnd = mulberry32(seed);
  const segs: Seg[] = [];
  let order = 0;

  const grow = (x: number, y: number, ang: number, len: number, depth: number): void => {
    if (depth <= 0) return;
    const nx = x + Math.cos(ang) * len;
    const ny = y + Math.sin(ang) * len;
    segs.push({ x1: x, y1: y, x2: nx, y2: ny, depth, order: order++ });
    const branches = depth > 2 ? 2 : rnd() > 0.3 ? 2 : 1;
    for (let i = 0; i < branches; i++) {
      const spread = (i === 0 ? -1 : 1) * (0.24 + rnd() * 0.42);
      grow(nx, ny, ang + spread, len * (0.7 + rnd() * 0.12), depth - 1);
    }
  };

  grow(540, 1620, -Math.PI / 2, 185, 6);
  return segs;
}

const NODES: Pt[] = [
  { x: 120, y: 1600 },
  { x: 330, y: 1600 },
  { x: 540, y: 1660 },
  { x: 760, y: 1660 },
  { x: 960, y: 1600 },
];

/** 按弧长在折线上取点：u∈[0,1] */
function polylineAt(nodes: Pt[], u: number): Pt {
  const parts = nodes.slice(1).map((b, i) => ({ a: nodes[i], b, l: Math.hypot(b.x - nodes[i].x, b.y - nodes[i].y) }));
  const total = parts.reduce((s, p) => s + p.l, 0);
  let left = u * total;
  for (const p of parts) {
    if (left <= p.l) {
      const k = p.l === 0 ? 0 : left / p.l;
      return { x: p.a.x + (p.b.x - p.a.x) * k, y: p.a.y + (p.b.y - p.a.y) * k };
    }
    left -= p.l;
  }
  return nodes[nodes.length - 1];
}

const key = (x: number, y: number) => `${x.toFixed(2)},${y.toFixed(2)}`;

// 线条生长：先长出一张金色分叉网，再把**同一张网**拉直成地铁线，最后点出站点。
// 关键在"同一张网"：拉直是逐段插值，不换素材，所以观众看到的是同一批线在走位。
export const LineGrow: React.FC<{
  kicker?: string;
  title?: string;
  note?: string;
  /** 是否演出"拉直成地铁图" */
  morph?: boolean;
  seed?: number;
}> = ({ kicker = "NO BLUEPRINT", title = "没有图纸的城市", note = "黏菌 → 地铁网", morph = true, seed = 44 }) => {
  const frame = useCurrentFrame();
  const { segs, target } = useMemo(() => {
    const s = buildTree(seed);
    // 每个点按"第一次出现"的顺序映射到折线上的位置，保证拉直后仍然是连着的
    const seen: string[] = [];
    const depthOf = new Map<string, number>();
    for (const g of s) {
      for (const [x, y] of [
        [g.x1, g.y1],
        [g.x2, g.y2],
      ] as Array<[number, number]>) {
        const k = key(x, y);
        if (!depthOf.has(k)) {
          depthOf.set(k, g.depth);
          seen.push(k);
        }
      }
    }
    const t = new Map<string, Pt>();
    seen.forEach((k, i) => {
      const u = 0.03 + (0.94 * i) / Math.max(1, seen.length - 1);
      const p = polylineAt(NODES, u);
      // 层级越浅抬得越高，做成分叉的平行轨道
      t.set(k, { x: p.x, y: p.y - (depthOf.get(k) ?? 1) * 5.5 });
    });
    return { segs: s, target: t };
  }, [seed]);

  const metro = morph
    ? interpolate(frame, [56, 92], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.cubic),
      })
    : 0;

  const headOpacity = interpolate(frame, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const noteOpacity = interpolate(frame, [56, 76], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id="vlab-line-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g filter="url(#vlab-line-glow)">
          {segs.map((s) => {
            const t = interpolate(frame, [s.order * 0.42, s.order * 0.42 + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const k1 = key(s.x1, s.y1);
            const k2 = key(s.x2, s.y2);
            const a = target.get(k1);
            const b = target.get(k2);
            const x1 = a ? s.x1 + (a.x - s.x1) * metro : s.x1;
            const y1 = a ? s.y1 + (a.y - s.y1) * metro : s.y1;
            const x2 = b ? s.x2 + (b.x - s.x2) * metro : s.x2;
            const y2 = b ? s.y2 + (b.y - s.y2) * metro : s.y2;
            const len = Math.hypot(x2 - x1, y2 - y1);
            const fade = interpolate(frame, [70, 96], [1, 0.32], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            // 拉直过程中线会变短，用"已生长比例"当画笔，避免长度变化导致画面闪烁
            return (
              <line
                key={s.order}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={metro > 0.4 ? C.cyan : C.gold}
                strokeWidth={s.depth > 4 ? 2.8 : s.depth > 3 ? 2.0 : s.depth > 2 ? 1.4 : 1.0}
                strokeLinecap="round"
                opacity={0.85 * fade * t}
              />
            );
          })}
        </g>

        {/* 地铁骨架：作为"拉直的目标轨道"很淡地先出现 */}
        <polyline
          points={NODES.map((n) => `${n.x},${n.y}`).join(" ")}
          fill="none"
          stroke={C.cyan}
          strokeWidth={2}
          strokeDasharray="10 12"
          opacity={0.28 * metro}
        />
        {NODES.map((n, i) => (
          <g key={i} opacity={metro}>
            <circle cx={n.x} cy={n.y} r={13} fill={C.bg} stroke={C.cyan} strokeWidth={4} />
            <circle cx={n.x} cy={n.y} r={4} fill={C.cyan} />
          </g>
        ))}
      </svg>

      <div
        style={{
          position: "absolute",
          left: 96,
          right: 96,
          top: 380,
          opacity: headOpacity,
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 24, letterSpacing: 10, color: C.cyan }}>{kicker}</div>
        <div style={{ fontFamily: FONT, fontSize: 62, fontWeight: 700, color: C.ink, marginTop: 20 }}>
          {title}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 150,
          textAlign: "center",
          fontFamily: FONT,
          fontSize: 36,
          letterSpacing: 6,
          color: C.ink,
          opacity: noteOpacity,
        }}
      >
        {note}
      </div>
    </AbsoluteFill>
  );
};
