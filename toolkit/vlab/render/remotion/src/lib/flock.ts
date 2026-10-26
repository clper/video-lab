// 鸟群模拟：确定性的 boids，实时算好整条轨迹，帧只做取数。
// 同一 seed + 同一批参数 → 每一帧都一样，Remotion 才能并发渲染。
import { mulberry32 } from "../common/random";

export const WORLD_W = 1080;
export const WORLD_H = 1920;

export type Bird = { x: number; y: number; vx: number; vy: number };

export type FlockOpts = {
  n?: number;
  steps?: number;
  seed?: number;
  /** 逐只出生（按几何级数加速），否则一开始就全部在场 */
  birth?: boolean;
  /** 威胁物：从 from 匀速走到 to，只在 [t0, t1] 这段存在 */
  threat?: { from: [number, number]; to: [number, number]; t0: number; t1: number } | null;
  /** 第几步开始崩散 */
  collapseAt?: number | null;
  start?: [number, number];
  spread?: number;
};

const PERCEPTION = 92;
const SEPARATION = 40;
const MAX_SPEED = 6.6;
const MAX_FORCE = 0.42;

/** 出生时刻表：前慢后快，按几何级数逼近总数 —— 观感是"越生越快，忽然成团" */
export function birthSchedule(n: number, steps: number): number[] {
  const out: number[] = [];
  let total = 0;
  let k = 0;
  while (total < n) {
    const count = Math.max(1, Math.round(Math.pow(1.22, k)));
    for (let i = 0; i < count && total < n; i++) {
      out.push(Math.min(steps - 1, Math.round((k / 34) * steps)));
      total++;
    }
    k++;
  }
  return out;
}

export function simulate(opts: FlockOpts = {}): Bird[][] {
  const n = opts.n ?? 640;
  const steps = opts.steps ?? 150;
  const seed = opts.seed ?? 1987;
  const rnd = mulberry32(seed);
  const start = opts.start ?? [WORLD_W / 2, WORLD_H / 2];
  const spread = opts.spread ?? 26;

  const born = opts.birth ? birthSchedule(n, steps) : new Array(n).fill(0);
  const birds: Bird[] = Array.from({ length: n }, () => {
    const a = rnd() * Math.PI * 2;
    const r = rnd() * spread;
    return {
      x: start[0] + Math.cos(a) * r,
      y: start[1] + Math.sin(a) * r,
      vx: Math.cos(a) * (1 + rnd() * 2),
      vy: Math.sin(a) * (1 + rnd() * 2),
    };
  });
  const active = new Array(n).fill(!opts.birth);

  const frames: Bird[][] = [];
  for (let s = 0; s < steps; s++) {
    for (let i = 0; i < n; i++) if (!active[i] && s >= born[i]) active[i] = true;
    frames.push(birds.map((b, i) => ({ ...b, vx: active[i] ? b.vx : 0 })));

    const collapsing = opts.collapseAt != null && s >= opts.collapseAt;
    const threat = opts.threat && s >= opts.threat.t0 && s <= opts.threat.t1 ? opts.threat : null;
    const tp = threat
      ? [
          threat.from[0] + ((threat.to[0] - threat.from[0]) * (s - threat.t0)) / Math.max(1, threat.t1 - threat.t0),
          threat.from[1] + ((threat.to[1] - threat.from[1]) * (s - threat.t0)) / Math.max(1, threat.t1 - threat.t0),
        ]
      : null;

    // 群体中心（崩散时从它向外炸开）
    let gx = 0;
    let gy = 0;
    let gc = 0;
    for (let i = 0; i < n; i++) if (active[i]) (gx += birds[i].x), (gy += birds[i].y), gc++;
    gx /= Math.max(1, gc);
    gy /= Math.max(1, gc);

    for (let i = 0; i < n; i++) {
      if (!active[i]) continue;
      const b = birds[i];
      let sepx = 0;
      let sepy = 0;
      let alx = 0;
      let aly = 0;
      let cohx = 0;
      let cohy = 0;
      let cnt = 0;

      for (let j = 0; j < n; j++) {
        if (j === i || !active[j]) continue;
        const o = birds[j];
        const dx = o.x - b.x;
        const dy = o.y - b.y;
        const d2 = dx * dx + dy * dy;
        if (d2 > PERCEPTION * PERCEPTION) continue;
        cnt++;
        cohx += o.x;
        cohy += o.y;
        alx += o.vx;
        aly += o.vy;
        if (d2 < SEPARATION * SEPARATION) {
          const d = Math.sqrt(d2) || 1;
          sepx -= dx / d;
          sepy -= dy / d;
        }
      }

      let ax = 0;
      let ay = 0;
      if (cnt > 0) {
        // 对齐
        const alLen = Math.hypot(alx, aly) || 1;
        ax += ((alx / alLen) * MAX_SPEED - b.vx) * 0.9;
        ay += ((aly / alLen) * MAX_SPEED - b.vy) * 0.9;
        // 聚合
        const cx = cohx / cnt - b.x;
        const cy = cohy / cnt - b.y;
        const cLen = Math.hypot(cx, cy) || 1;
        ax += (cx / cLen) * 0.55;
        ay += (cy / cLen) * 0.55;
      }
      // 分离
      const sLen = Math.hypot(sepx, sepy);
      if (sLen > 0) {
        ax += (sepx / sLen) * 1.9;
        ay += (sepy / sLen) * 1.9;
      }
      // 边界：软回弹
      const margin = 120;
      if (b.x < margin) ax += (margin - b.x) / margin;
      if (b.x > WORLD_W - margin) ax -= (b.x - (WORLD_W - margin)) / margin;
      if (b.y < margin) ay += (margin - b.y) / margin;
      if (b.y > WORLD_H - margin) ay -= (b.y - (WORLD_H - margin)) / margin;

      if (collapsing) {
        const dx = b.x - gx;
        const dy = b.y - gy;
        const d = Math.hypot(dx, dy) || 1;
        ax += (dx / d) * 3.4;
        ay += (dy / d) * 3.4;
      }
      if (tp) {
        const dx = b.x - tp[0];
        const dy = b.y - tp[1];
        const d = Math.hypot(dx, dy) || 1;
        if (d < 340) {
          const push = (340 - d) / 340;
          ax += (dx / d) * push * 4.2;
          ay += (dy / d) * push * 4.2;
        }
      }

      const aLen = Math.hypot(ax, ay) || 1;
      const lim = Math.min(MAX_FORCE, aLen);
      b.vx += (ax / aLen) * lim;
      b.vy += (ay / aLen) * lim;

      const vLen = Math.hypot(b.vx, b.vy) || 1;
      const sp = Math.min(MAX_SPEED * (collapsing ? 1.5 : 1), vLen);
      b.vx = (b.vx / vLen) * sp;
      b.vy = (b.vy / vLen) * sp;
      b.x += b.vx;
      b.y += b.vy;
    }
  }
  return frames;
}

/** 威胁物在某一帧的位置（渲染用），不在时段内返回 null */
export function threatAt(opts: FlockOpts, step: number): [number, number] | null {
  const t = opts.threat;
  if (!t || step < t.t0 || step > t.t1) return null;
  const k = (step - t.t0) / Math.max(1, t.t1 - t.t0);
  return [t.from[0] + (t.to[0] - t.from[0]) * k, t.from[1] + (t.to[1] - t.from[1]) * k];
}
