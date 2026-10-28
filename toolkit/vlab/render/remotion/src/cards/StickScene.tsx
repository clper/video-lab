import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { C, FONT } from "../design/tokens";
import { mulberry32 } from "../common/random";

// 火柴人场景播放器（动作数据由 toolkit/vlab/stick 算好传进来；样片见 research/visual/15-stickfigure，正片见 009）。
// 动作全在 Python 里算：每帧 11 个关节坐标（关键帧 + IK + 布偶物理）、相机、粒子和事件。
// 这张卡只负责画，画法是"光绘火柴人"：每根骨头是一根霓虹管——外晕 + 本色 + 白芯，
// 快速移动的手脚拖出光迹，冲刺时留残影，地面有倒影和人身上投下的光。
// 物理标注（力和动量的箭头、重心、支撑面、支点、气流线）、抛物线和频闪残影也从数据里来：画面上的每个点都是算出来的。
// 一条长片按镜头切成多段数据，每段多带几帧前情（offset），光迹和残影跨镜头也接得上。

type Fig = { name: string; color: string; core: string; width: number; headR: number; j: number[][] };
type Burst = {
  f: number;
  x: number;
  y: number;
  kind: "spark" | "dust" | "ring" | "flare";
  seed: number;
  n?: number;
  speed?: number;
  angle?: number;
  spread?: number;
  life?: number;
  size?: number;
  color?: string;
  g?: number;
  len?: number;
};
type Track = { f0: number; f1: number; age0?: number; pts: number[][] };
type Data = {
  fps: number;
  frames: number;
  offset?: number;
  /** 这段数据第 0 帧在全片的帧号（背景雾按它计时，切镜时不跳） */
  fabs0?: number;
  /** 从上往下打的主光：每帧 [x, 亮度 0~1]，跟着人走 */
  spot?: number[][];
  /** 背景里慢慢飘的雾光 */
  haze?: boolean;
  ground: number;
  grid?: boolean;
  trail?: number;
  reflect?: number;
  figures: Fig[];
  camera: number[][];
  freeze?: number[];
  /** 每帧的动作时间（单位：帧）：粒子按它算年龄，定格时悬在半空、慢镜头里飞得慢 */
  clock?: number[];
  bursts: Burst[];
  balls?: { color: string; r: number; p: (number[] | null)[] }[];
  ghosts?: { color: string; r: number; pts: number[][] }[];
  paths?: {
    color: string;
    f0: number;
    f1: number;
    end?: number;
    pts: number[][];
    dash?: number[];
    width?: number;
    opacity?: number;
  }[];
  labels?: {
    f0: number;
    f1?: number;
    x: number;
    y: number;
    text: string;
    size?: number;
    color?: string;
    anchor?: string;
    screen?: boolean;
  }[];
  arcs?: {
    f0: number;
    f1?: number;
    x: number;
    y: number;
    r: number;
    a0: number;
    a1: number;
    color?: string;
    head?: boolean;
    width?: number;
    grow?: number;
  }[];
  walls?: { x: number; y0: number; y1: number; color?: string }[];
  arrows?: (Track & { color: string; width: number; grow?: number })[];
  dots?: (Track & { color: string; r: number; label?: string; lsize?: number; lx?: number; ly?: number })[];
  bars?: (Track & { color: string; alt: string; falt: number; y: number })[];
  tris?: (Track & { color: string; size: number })[];
  flows?: (Track & { color: string; lines: number[][][] })[];
  feathers?: { color: string; size: number; p: (number[] | null)[] }[];
};

type Props = { data?: Data };

const PX_PER_M = 189.71;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const fade = (frame: number, f0: number, f1: number | undefined, len = 8) =>
  clamp01((frame - f0) / len) * (f1 === undefined ? 1 : clamp01((f1 - frame) / len));

const pt = (j: number[], i: number): [number, number] => [j[2 * i], j[2 * i + 1]];
const line = (j: number[], idx: number[]) => "M" + idx.map((i) => `${j[2 * i]} ${j[2 * i + 1]}`).join(" L");

/** 一个火柴人：远侧手脚先画、压暗；躯干和头；近侧手脚最后画 */
const Figure: React.FC<{ fig: Fig; j: number[]; alpha?: number; halo?: boolean }> = ({ fig, j, alpha = 1, halo = true }) => {
  const w = fig.width;
  const back = line(j, [1, 5, 6]) + " " + line(j, [0, 9, 10]);
  const front = line(j, [0, 1]) + " " + line(j, [1, 3, 4]) + " " + line(j, [0, 7, 8]);
  const [hx, hy] = pt(j, 2);
  const id = `hd-${fig.name}`;
  const tube = (d: string, k: number) => (
    <>
      <path d={d} stroke={fig.color} strokeWidth={w} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={k} />
      <path d={d} stroke={fig.core} strokeWidth={w * 0.36} fill="none" strokeLinecap="round" strokeLinejoin="round" opacity={0.85 * k} />
    </>
  );
  return (
    <g opacity={alpha}>
      <defs>
        <radialGradient id={id} cx="42%" cy="40%" r="62%">
          <stop offset="0%" stopColor={fig.core} />
          <stop offset="55%" stopColor={fig.color} />
          <stop offset="100%" stopColor={fig.color} />
        </radialGradient>
      </defs>
      {halo ? (
        <g filter="url(#st-glow-l)" opacity={0.42}>
          <path d={back + " " + front} stroke={fig.color} strokeWidth={w * 3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx={hx} cy={hy} r={fig.headR * 1.25} fill={fig.color} />
        </g>
      ) : null}
      {tube(back, 0.5)}
      {tube(front, 1)}
      <circle cx={hx} cy={hy} r={fig.headR} fill={`url(#${id})`} />
    </g>
  );
};

/** 手脚的光迹：最近几帧的位置连成一条渐隐的线，越快越亮 */
const Trails: React.FC<{ fig: Fig; frame: number; n: number }> = ({ fig, frame, n }) => {
  const segs: React.ReactNode[] = [];
  for (const i of [4, 6, 8, 10, 2]) {
    for (let k = 0; k < n; k++) {
      const fa = frame - k;
      const fb = fa - 1;
      if (fb < 0) break;
      const [ax, ay] = pt(fig.j[fa], i);
      const [bx, by] = pt(fig.j[fb], i);
      const sp = Math.hypot(ax - bx, ay - by);
      const vis = clamp01((sp - 9) / 22) * (1 - k / n);
      if (vis <= 0.02) continue;
      const far = i === 6 || i === 10;
      segs.push(
        <line
          key={`${i}-${k}`}
          x1={ax}
          y1={ay}
          x2={bx}
          y2={by}
          stroke={fig.color}
          strokeWidth={(i === 2 ? fig.headR * 1.2 : fig.width * 1.15) * (1 - k / (n + 1))}
          strokeLinecap="round"
          opacity={vis * (far ? 0.35 : 0.6) * (i === 2 ? 0.35 : 1)}
        />,
      );
    }
  }
  return <g filter="url(#st-glow-s)">{segs}</g>;
};

const Bursts: React.FC<{ bursts: Burst[]; frame: number; fps: number }> = ({ bursts, frame, fps }) => {
  const glow: React.ReactNode[] = [];
  const crisp: React.ReactNode[] = [];
  bursts.forEach((b, bi) => {
    const age = frame - b.f;
    const life = b.life ?? 18;
    if (age < 0 || age > life) return;
    const rng = mulberry32(b.seed);
    const n = b.kind === "ring" || b.kind === "flare" ? 1 : b.n ?? 12;
    const color = b.color ?? C.gold;
    for (let i = 0; i < n; i++) {
      const a = (((b.angle ?? -90) + (rng() - 0.5) * (b.spread ?? 360)) * Math.PI) / 180;
      const sp = (b.speed ?? 600) * (0.35 + 0.65 * rng());
      const lf = b.kind === "ring" || b.kind === "flare" ? life : life * (0.55 + 0.45 * rng());
      const sz = (b.size ?? 4) * (b.kind === "ring" || b.kind === "flare" ? 1 : 0.6 + 0.8 * rng());
      if (age > lf) continue;
      const u = age / lf;
      const tau = age / fps;
      const key = `${bi}-${i}`;
      if (b.kind === "spark") {
        const k = 2.6;
        const g = b.g ?? 1400;
        const disp = (sp * (1 - Math.exp(-k * tau))) / k;
        const x = b.x + Math.cos(a) * disp;
        const y = b.y + Math.sin(a) * disp + 0.5 * g * tau * tau;
        const vx = Math.cos(a) * sp * Math.exp(-k * tau);
        const vy = Math.sin(a) * sp * Math.exp(-k * tau) + g * tau;
        const vl = Math.hypot(vx, vy) || 1;
        const L = Math.min(b.len ?? 44, vl * 0.04) + 2;
        glow.push(
          <line key={key} x1={x} y1={y} x2={x - (vx / vl) * L} y2={y - (vy / vl) * L} stroke={color}
            strokeWidth={sz * (1 - 0.6 * u)} strokeLinecap="round" opacity={Math.pow(1 - u, 1.2)} />,
        );
        crisp.push(
          <line key={key + "c"} x1={x} y1={y} x2={x - (vx / vl) * L * 0.6} y2={y - (vy / vl) * L * 0.6}
            stroke="#fff8e8" strokeWidth={sz * 0.35} strokeLinecap="round" opacity={Math.pow(1 - u, 1.5)} />,
        );
      } else if (b.kind === "dust") {
        const k = 4;
        const g = b.g ?? -40;
        const disp = (sp * (1 - Math.exp(-k * tau))) / k;
        const x = b.x + Math.cos(a) * disp;
        const y = Math.min(b.y, b.y + Math.sin(a) * disp + 0.5 * g * tau * tau);
        crisp.push(<circle key={key} cx={x} cy={y} r={sz * (0.7 + 1.8 * u)} fill={color} opacity={0.3 * Math.pow(1 - u, 1.5)} />);
      } else if (b.kind === "ring") {
        const r = sz + ((b.speed ?? 160) - sz) * (1 - Math.pow(1 - u, 3));
        glow.push(<circle key={key} cx={b.x} cy={b.y} r={r} fill="none" stroke={color} strokeWidth={4 * (1 - u) + 0.6} opacity={Math.pow(1 - u, 1.4)} />);
        crisp.push(<circle key={key + "c"} cx={b.x} cy={b.y} r={r} fill="none" stroke="#fff8e8" strokeWidth={1.4 * (1 - u)} opacity={Math.pow(1 - u, 2)} />);
      } else {
        glow.push(<circle key={key} cx={b.x} cy={b.y} r={sz * (1 + 0.5 * u)} fill={color} opacity={0.75 * Math.pow(1 - u, 2)} />);
        crisp.push(<circle key={key + "c"} cx={b.x} cy={b.y} r={sz * 0.3 * (1 - u)} fill="#ffffff" opacity={Math.pow(1 - u, 2)} />);
      }
    }
  });
  return (
    <>
      <g filter="url(#st-glow-m)">{glow}</g>
      <g>{crisp}</g>
    </>
  );
};

const Ball: React.FC<{ x: number; y: number; r: number; rot: number; color: string; id: string }> = ({ x, y, r, rot, color, id }) => (
  <g>
    <defs>
      <radialGradient id={id} cx="38%" cy="36%" r="70%">
        <stop offset="0%" stopColor="#ffffff" />
        <stop offset="45%" stopColor={color} />
        <stop offset="100%" stopColor={color} stopOpacity={0.85} />
      </radialGradient>
    </defs>
    <circle cx={x} cy={y} r={r * 1.7} fill={color} opacity={0.35} filter="url(#st-glow-l)" />
    <circle cx={x} cy={y} r={r} fill={`url(#${id})`} />
    <path
      d={`M ${x - r * 0.92} ${y} Q ${x} ${y - r * 0.55} ${x + r * 0.92} ${y}`}
      transform={`rotate(${rot} ${x} ${y})`}
      stroke={C.bg}
      strokeWidth={2.2}
      fill="none"
      opacity={0.55}
    />
  </g>
);

/** 一根发光羽毛：羽轴 + 两侧羽片，跟着气流飘 */
const Feather: React.FC<{ x: number; y: number; rot: number; size: number; color: string }> = ({ x, y, rot, size, color }) => {
  const s = size;
  const vane = `M ${-s} 0 Q ${-s * 0.2} ${-s * 0.34} ${s * 0.8} ${-s * 0.06} L ${s} 0 Q ${-s * 0.1} ${s * 0.3} ${-s} 0 Z`;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`}>
      <path d={vane} fill={color} opacity={0.45} filter="url(#st-glow-m)" />
      <path d={vane} fill={color} opacity={0.55} />
      <line x1={-s * 1.15} y1={0} x2={s} y2={0} stroke="#fffaf0" strokeWidth={1.8} strokeLinecap="round" />
    </g>
  );
};

/** 当前帧在一条标注轨里的位置；不在区间里返回 null */
const at = (tr: Track, frame: number): number[] | null => {
  if (frame < tr.f0 || frame > tr.f1) return null;
  const i = Math.min(tr.pts.length - 1, frame - tr.f0);
  return i >= 0 ? tr.pts[i] : null;
};

const Arrow: React.FC<{ x: number; y: number; dx: number; dy: number; color: string; width: number; k: number }> = ({
  x,
  y,
  dx,
  dy,
  color,
  width,
  k,
}) => {
  const L = Math.hypot(dx, dy);
  if (L < 1) return null;
  const ux = dx / L;
  const uy = dy / L;
  const head = Math.min(L * 0.45, width * 4.2);
  const ex = x + dx;
  const ey = y + dy;
  const bx = ex - ux * head;
  const by = ey - uy * head;
  const px = -uy * head * 0.55;
  const py = ux * head * 0.55;
  const d = `M ${x} ${y} L ${bx} ${by}`;
  const tip = `M ${ex} ${ey} L ${bx + px} ${by + py} L ${bx - px} ${by - py} Z`;
  return (
    <g opacity={k}>
      <g filter="url(#st-glow-m)" opacity={0.7}>
        <path d={d} stroke={color} strokeWidth={width * 2.2} strokeLinecap="round" />
        <path d={tip} fill={color} />
      </g>
      <path d={d} stroke={color} strokeWidth={width} strokeLinecap="round" />
      <path d={tip} fill={color} />
      <path d={d} stroke="#ffffff" strokeWidth={width * 0.3} strokeLinecap="round" opacity={0.75} />
    </g>
  );
};

export const StickScene: React.FC<Props> = ({ data }) => {
  const frame0 = useCurrentFrame();
  if (!data) return null;
  const frame = Math.min(frame0 + (data.offset ?? 0), data.frames - 1);
  const [cx, cy, z] = data.camera[frame] ?? [960, 540, 1];
  const G = data.ground;
  const trail = data.trail ?? 7;
  const fz = data.freeze?.[frame] ?? 0;
  const world = `translate(960 540) scale(${z}) translate(${-cx} ${-cy})`;

  const figs = data.figures.map((fig) => {
    const j = fig.j[frame];
    // 冲刺残影：骨盆每帧走得比 12px 快就留两道
    const prev = fig.j[Math.max(0, frame - 2)];
    const sp = Math.hypot(j[0] - prev[0], j[1] - prev[1]) / 2;
    return { fig, j, dash: fz > 0 ? 0 : clamp01((sp - 12) / 14) };
  });

  const balls = (data.balls ?? []).map((b, i) => ({ b, p: b.p[frame], id: `ball-${i}` }));
  const feathers = (data.feathers ?? []).map((fe) => ({ fe, p: fe.p[frame] }));

  const scene = (mirror: boolean) => (
    <>
      {figs.map(({ fig, j, dash }) => (
        <g key={fig.name}>
          {!mirror && dash > 0
            ? [4, 2].map((k) => (
                <Figure key={k} fig={fig} j={fig.j[Math.max(0, frame - k)]} alpha={dash * (k === 2 ? 0.22 : 0.12)} halo={false} />
              ))
            : null}
          {!mirror && fz === 0 ? <Trails fig={fig} frame={frame} n={trail} /> : null}
          <Figure fig={fig} j={j} halo={!mirror} />
        </g>
      ))}
      {balls.map(({ b, p, id }) =>
        p ? <Ball key={id} x={p[0]} y={p[1]} r={b.r} rot={p[2] ?? 0} color={b.color} id={id + (mirror ? "m" : "")} /> : null,
      )}
      {feathers.map(({ fe, p }, i) => (p ? <Feather key={`fe${i}`} x={p[0]} y={p[1]} rot={p[2]} size={fe.size} color={fe.color} /> : null))}
    </>
  );

  const label = (l: NonNullable<Data["labels"]>[number], i: number) => {
    const k = fade(frame, l.f0, l.f1);
    if (k <= 0) return null;
    return (
      <text key={`l${i}`} x={l.x} y={l.y} fill={l.color ?? C.ink} fontFamily={FONT} fontSize={l.size ?? 34}
        textAnchor={(l.anchor as "start" | "middle" | "end") ?? "middle"} opacity={k}
        style={{ filter: `drop-shadow(0 0 8px ${l.color ?? C.ink})` }}>
        {l.text}
      </text>
    );
  };

  return (
    <AbsoluteFill>
      <svg width="100%" height="100%" viewBox="0 0 1920 1080" style={{ overflow: "visible" }}>
        <defs>
          <filter id="st-glow-l" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="11" />
          </filter>
          <filter id="st-glow-m" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" />
          </filter>
          <filter id="st-glow-s" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.2" />
          </filter>
          <filter id="st-blur-r" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" />
          </filter>
          <linearGradient id="st-floor" x1="0" y1={G} x2="0" y2={G + 260} gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1b2335" stopOpacity={0.9} />
            <stop offset="100%" stopColor={C.bg} stopOpacity={0} />
          </linearGradient>
          <linearGradient id="st-refl-g" x1="0" y1={G} x2="0" y2={G + 330} gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fff" stopOpacity={1} />
            <stop offset="100%" stopColor="#fff" stopOpacity={0} />
          </linearGradient>
          <mask id="st-refl" maskUnits="userSpaceOnUse" x={-6000} y={G} width={14000} height={400}>
            <rect x={-6000} y={G} width={14000} height={400} fill="url(#st-refl-g)" />
          </mask>
          <linearGradient id="st-wall" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#2b3550" />
            <stop offset="100%" stopColor="#0d111c" />
          </linearGradient>
          <linearGradient id="st-cone" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fff3d6" stopOpacity={0} />
            <stop offset="70%" stopColor="#fff3d6" stopOpacity={0.55} />
            <stop offset="100%" stopColor="#fff3d6" stopOpacity={1} />
          </linearGradient>
          <radialGradient id="st-haze-a" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#3a5a8c" stopOpacity={1} />
            <stop offset="100%" stopColor="#3a5a8c" stopOpacity={0} />
          </radialGradient>
          <radialGradient id="st-haze-b" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#8c6a3a" stopOpacity={1} />
            <stop offset="100%" stopColor="#8c6a3a" stopOpacity={0} />
          </radialGradient>
          <filter id="st-glow-xl" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="40" />
          </filter>
        </defs>

        {/* 背景雾光：两团冷暖的光在暗处慢慢飘，按全片帧号计时（切镜不跳） */}
        {data.haze
          ? (() => {
              const fa = (data.fabs0 ?? 0) + frame;
              return (
                <g opacity={1 - 0.5 * fz}>
                  <ellipse cx={960 + 560 * Math.sin(fa * 0.0042)} cy={430 + 110 * Math.cos(fa * 0.0031)} rx={620} ry={360}
                    fill="url(#st-haze-a)" opacity={0.16} />
                  <ellipse cx={960 - 520 * Math.sin(fa * 0.0035 + 1.7)} cy={520 + 90 * Math.sin(fa * 0.0027 + 0.6)} rx={540}
                    ry={320} fill="url(#st-haze-b)" opacity={0.1} />
                </g>
              );
            })()
          : null}

        <g transform={world}>
          {/* 定格时整个场景压暗去色，只有物理标注保持鲜亮 */}
          <g style={fz > 0 ? { filter: `saturate(${1 - 0.55 * fz}) brightness(${1 - 0.28 * fz})` } : undefined}>
            {/* 地面：一条冷光线 + 往下渐隐的反光面 */}
            <rect x={-6000} y={G} width={14000} height={300} fill="url(#st-floor)" />
            {data.grid
              ? Array.from({ length: 40 }, (_, i) => -1600 + i * PX_PER_M).map((x) => (
                  <line key={`gx${x}`} x1={x} y1={G - 760} x2={x} y2={G} stroke={C.dim} strokeWidth={1} opacity={0.07} />
                ))
              : null}
            {data.grid
              ? Array.from({ length: 5 }, (_, i) => G - (i + 1) * PX_PER_M).map((y) => (
                  <line key={`gy${y}`} x1={-2000} y1={y} x2={4200} y2={y} stroke={C.dim} strokeWidth={1} opacity={0.07} />
                ))
              : null}
            <line x1={-6000} y1={G} x2={8000} y2={G} stroke="#5d6a86" strokeWidth={2} opacity={0.75} />

            {/* 主光：一束从上往下打的光罩着两个人，地上一圈光斑 */}
            {data.spot?.[frame]
              ? (() => {
                  const [sx, sk] = data.spot![frame];
                  return (
                    <g opacity={sk}>
                      <path d={`M ${sx - 150} ${G - 1150} L ${sx + 150} ${G - 1150} L ${sx + 440} ${G} L ${sx - 440} ${G} Z`}
                        fill="url(#st-cone)" opacity={0.085} filter="url(#st-glow-xl)" />
                      <ellipse cx={sx} cy={G + 8} rx={440} ry={50} fill="#fff3d6" opacity={0.13} filter="url(#st-glow-l)" />
                    </g>
                  );
                })()
              : null}

            {/* 人和球在地上投下的光 */}
            {figs.map(({ fig, j }) => {
              const h = Math.max(0, G - Math.max(j[17], j[21]));
              return (
                <ellipse key={`pool-${fig.name}`} cx={j[0]} cy={G + 4} rx={110 * (fig.width / 11)} ry={14} fill={fig.color}
                  opacity={0.2 * clamp01(1 - h / 260)} filter="url(#st-glow-l)" />
              );
            })}
            {balls.map(({ b, p, id }) =>
              p ? (
                <ellipse key={`pool-${id}`} cx={p[0]} cy={G + 3} rx={b.r * 2.2} ry={7} fill={b.color}
                  opacity={0.28 * clamp01(1 - (G - p[1]) / 420)} filter="url(#st-glow-m)" />
              ) : null,
            )}

            {(data.walls ?? []).map((w, i) => (
              <g key={`w${i}`}>
                <rect x={w.x} y={w.y0} width={26} height={w.y1 - w.y0} fill="url(#st-wall)" />
                <line x1={w.x} y1={w.y0} x2={w.x} y2={w.y1} stroke={w.color ?? "#9aa6c4"} strokeWidth={3} filter="url(#st-glow-s)" />
                <line x1={w.x} y1={w.y0} x2={w.x} y2={w.y1} stroke="#dfe6f5" strokeWidth={1.2} />
              </g>
            ))}

            {/* 倒影 */}
            {data.reflect ? (
              <g mask="url(#st-refl)" opacity={data.reflect} filter="url(#st-blur-r)">
                <g transform={`translate(0 ${2 * G}) scale(1 -1)`}>{scene(true)}</g>
              </g>
            ) : null}

            {/* 预测的抛物线（先画出来，球再沿着它飞） */}
            {(data.paths ?? []).map((p, i) => {
              const k = clamp01((frame - p.f0) / Math.max(1, p.f1 - p.f0));
              const out = p.end === undefined ? 1 : clamp01((p.end - frame) / 8);
              if (k <= 0 || out <= 0) return null;
              const m = Math.max(2, Math.ceil(k * p.pts.length));
              const d = "M" + p.pts.slice(0, m).map((q) => `${q[0]} ${q[1]}`).join(" L");
              return (
                <path key={`p${i}`} d={d} stroke={p.color} strokeWidth={p.width ?? 2.4} fill="none"
                  strokeDasharray={(p.dash ?? [10, 12]).join(" ")}
                  opacity={(p.opacity ?? 0.55) * clamp01((frame - p.f0) / 6) * out} />
              );
            })}

            {/* 频闪残影：等时间间隔留下的球 */}
            {(data.ghosts ?? []).map((g, gi) => (
              <g key={`g${gi}`}>
                {g.pts.map(([fa, x, y], i) =>
                  frame >= fa ? (
                    <circle key={i} cx={x} cy={y} r={g.r * 0.9} fill={g.color} fillOpacity={0.1} stroke={g.color}
                      strokeWidth={1.6} opacity={0.3 + 0.45 * Math.exp(-(frame - fa) / 40)} />
                  ) : null,
                )}
              </g>
            ))}

            {scene(false)}

            {/* 粒子按动作时间算年龄（clock）：定格时悬在半空，慢镜头里飞得慢 */}
            <Bursts bursts={data.bursts} frame={data.clock?.[frame] ?? frame} fps={data.fps} />
          </g>

          {/* —— 物理标注：定格时也保持鲜亮 —— */}
          {(data.arcs ?? []).map((a, i) => {
            const k = fade(frame, a.f0, a.f1);
            if (k <= 0) return null;
            const grow = 1 - Math.pow(1 - clamp01((frame - a.f0) / (a.grow ?? 10)), 3);
            const a1 = a.a0 + (a.a1 - a.a0) * grow;
            const r0 = (a.a0 * Math.PI) / 180;
            const r1 = (a1 * Math.PI) / 180;
            const large = Math.abs(a1 - a.a0) > 180 ? 1 : 0;
            const sweep = a1 > a.a0 ? 1 : 0;
            const ex = a.x + a.r * Math.cos(r1);
            const ey = a.y + a.r * Math.sin(r1);
            const d = `M ${a.x + a.r * Math.cos(r0)} ${a.y + a.r * Math.sin(r0)} A ${a.r} ${a.r} 0 ${large} ${sweep} ${ex} ${ey}`;
            const w = a.width ?? 2.4;
            const col = a.color ?? C.ink;
            // 箭头：沿弧的切线方向（顺着生长的方向）
            const s = a.a1 > a.a0 ? 1 : -1;
            const tx = -Math.sin(r1) * s;
            const ty = Math.cos(r1) * s;
            const hl = w * 4.5;
            const head = a.head && grow > 0.05
              ? `M ${ex + tx * hl * 0.6} ${ey + ty * hl * 0.6} L ${ex - tx * hl * 0.5 - ty * hl * 0.5} ${ey - ty * hl * 0.5 + tx * hl * 0.5} L ${ex - tx * hl * 0.5 + ty * hl * 0.5} ${ey - ty * hl * 0.5 - tx * hl * 0.5} Z`
              : null;
            return (
              <g key={`a${i}`} opacity={0.9 * k}>
                {a.head ? <path d={d} stroke={col} strokeWidth={w * 2.2} fill="none" opacity={0.6} filter="url(#st-glow-m)" /> : null}
                <path d={d} stroke={col} strokeWidth={w} fill="none" strokeLinecap="round" />
                {head ? <path d={head} fill={col} /> : null}
              </g>
            );
          })}

          {(data.bars ?? []).map((b, i) => {
            const p = at(b, frame);
            if (!p) return null;
            const k = fade(frame, b.f0 - (b.age0 ?? 0), b.f1);
            const col = frame >= b.falt ? b.alt : b.color;
            return (
              <g key={`b${i}`} opacity={k}>
                <line x1={p[0]} y1={b.y} x2={p[1]} y2={b.y} stroke={col} strokeWidth={12} strokeLinecap="round" opacity={0.6} filter="url(#st-glow-m)" />
                <line x1={p[0]} y1={b.y} x2={p[1]} y2={b.y} stroke={col} strokeWidth={4} strokeLinecap="round" />
                <line x1={p[0]} y1={b.y - 14} x2={p[0]} y2={b.y + 14} stroke={col} strokeWidth={3} />
                <line x1={p[1]} y1={b.y - 14} x2={p[1]} y2={b.y + 14} stroke={col} strokeWidth={3} />
              </g>
            );
          })}

          {(data.flows ?? []).map((fl, i) => {
            const p = at(fl, frame);
            if (!p) return null;
            const k = fade(frame, fl.f0 - (fl.age0 ?? 0), fl.f1, 10);
            const dashOff = -((frame * 6) % 40);
            return (
              <g key={`fl${i}`} opacity={0.75 * k} transform={`translate(${p[0]} ${p[1]})`}>
                {fl.lines.map((ln, li) => (
                  <path key={li} d={"M" + ln.map((q) => `${q[0]} ${q[1]}`).join(" L")} stroke={fl.color} strokeWidth={2}
                    fill="none" strokeDasharray="14 26" strokeDashoffset={dashOff} strokeLinecap="round" />
                ))}
              </g>
            );
          })}

          {(data.arrows ?? []).map((a, i) => {
            const p = at(a, frame);
            if (!p) return null;
            const age = frame - a.f0 + (a.age0 ?? 0);
            const g = clamp01(age / Math.max(1, a.grow ?? 8));
            const ease = 1 - Math.pow(1 - g, 3);
            const k = clamp01((a.f1 - frame) / 8) * clamp01(age / 3);
            return <Arrow key={`ar${i}`} x={p[0]} y={p[1]} dx={p[2] * ease} dy={p[3] * ease} color={a.color} width={a.width} k={k} />;
          })}

          {(data.dots ?? []).map((d, i) => {
            const p = at(d, frame);
            if (!p) return null;
            const k = fade(frame, d.f0 - (d.age0 ?? 0), d.f1);
            const pulse = 1 + 0.18 * Math.sin(frame * 0.35);
            return (
              <g key={`d${i}`} opacity={k}>
                <circle cx={p[0]} cy={p[1]} r={d.r * 2.4 * pulse} fill={d.color} opacity={0.35} filter="url(#st-glow-m)" />
                <circle cx={p[0]} cy={p[1]} r={d.r} fill={d.color} />
                <circle cx={p[0]} cy={p[1]} r={d.r * 0.45} fill="#ffffff" />
                {/* 跟着点走的标签（比如"重心"） */}
                {d.label ? (
                  <text x={p[0] + (d.lx ?? 22)} y={p[1] + (d.ly ?? -22)} fill={d.color} fontFamily={FONT}
                    fontSize={d.lsize ?? 34} style={{ filter: `drop-shadow(0 0 8px ${d.color})` }}>
                    {d.label}
                  </text>
                ) : null}
              </g>
            );
          })}

          {(data.tris ?? []).map((t, i) => {
            const p = at(t, frame);
            if (!p) return null;
            const k = fade(frame, t.f0 - (t.age0 ?? 0), t.f1);
            const s = t.size;
            const d = `M ${p[0]} ${p[1]} L ${p[0] - s * 0.6} ${p[1] + s} L ${p[0] + s * 0.6} ${p[1] + s} Z`;
            return (
              <g key={`t${i}`} opacity={k}>
                <path d={d} fill={t.color} opacity={0.4} filter="url(#st-glow-m)" />
                <path d={d} fill="none" stroke={t.color} strokeWidth={3} strokeLinejoin="round" />
              </g>
            );
          })}

          {(data.labels ?? []).filter((l) => !l.screen).map(label)}
        </g>

        {/* 定格时一层淡淡的冷色 */}
        {fz > 0 ? <rect x={0} y={0} width={1920} height={1080} fill="#203a66" opacity={0.08 * fz} /> : null}
        {(data.labels ?? []).filter((l) => l.screen).map(label)}
      </svg>
    </AbsoluteFill>
  );
};
