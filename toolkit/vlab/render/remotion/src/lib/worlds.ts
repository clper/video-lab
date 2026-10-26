// "音乐实验室"的数据：48 首歌、8 个平行世界、1 个对照组。
// 008《你没火，可能只是没被选中》的两张板子卡（WorldBoards / WorldBoard）都从这里取数。
//
// 结论照论文（Salganik, Dodds & Watts 2006），数字是我们自己按同样规则模拟出来的（片中标"示意"）：
//   - 对照组只凭"本来有多好"（appeal）选，排出来的就是"质量排名"；
//   - 8 个世界里，每个人看得到本世界的下载数，选歌时下载数越高越容易被点开（累积优势）；
//   - 结果：每个世界火的歌不一样，而且 8 个世界都比对照组更不平均。
// 那首"质量第 26、一个世界第 1、另一个世界第 40"的歌是 Watts 2007 的原例，这里把它钉死在数据里。
import { mulberry32 } from "../common/random";

export const N_SONGS = 48;
export const N_WORLDS = 8;
const PEOPLE_PER_WORLD = 640;   // 每个世界走过多少人（14,341 ÷ 2 轮 ÷ 9 组 ≈ 800，取整数够用）
const INFLUENCE = 0.14;         // 每一次下载让这首歌被点开的权重多多少

export type Worlds = {
  /** 每首歌"本来有多好"，0.15–1 */
  appeal: number[];
  /** 质量名次：1 最好 … 48 最差 */
  qRank: number[];
  /** 按质量从好到差排的歌 index */
  byQuality: number[];
  /** 对照组的"下载数"（只按 appeal 选） */
  control: number[];
  /** [world][song] 最终下载数 */
  downloads: number[][];
  /** [world][song] 名次 1..48 */
  rank: number[][];
  /** 那首中等的歌：在 top 世界第 1，在 bottom 世界第 40 */
  example: { song: number; top: number; bottom: number };
};

function ranksOf(values: number[]): number[] {
  const order = values.map((v, i) => [v, i] as const).sort((a, b) => b[0] - a[0]);
  const rank = new Array(values.length).fill(0);
  order.forEach(([, i], k) => {
    rank[i] = k + 1;
  });
  return rank;
}

function pick(weights: number[], u: number): number {
  let total = 0;
  for (const w of weights) total += w;
  let acc = 0;
  const target = u * total;
  for (let i = 0; i < weights.length; i += 1) {
    acc += weights[i];
    if (acc >= target) return i;
  }
  return weights.length - 1;
}

let cache: Worlds | null = null;

export function makeWorlds(seed = 2006): Worlds {
  if (cache) return cache;
  const rnd = mulberry32(seed);

  // 本来有多好：偏态分布——好歌少、一般的多
  const appeal = Array.from({ length: N_SONGS }, () => {
    const g = (rnd() + rnd() + rnd()) / 3;         // 0..1，中间多
    return 0.15 + 0.85 * Math.pow(g, 1.6);
  });
  const qRank = ranksOf(appeal);
  const byQuality = appeal.map((_, i) => i).sort((a, b) => appeal[b] - appeal[a]);

  // 对照组：只按 appeal 选
  const control = new Array(N_SONGS).fill(0);
  for (let p = 0; p < PEOPLE_PER_WORLD; p += 1) control[pick(appeal, rnd())] += 1;

  // 8 个世界：看得到下载数
  const downloads: number[][] = [];
  for (let w = 0; w < N_WORLDS; w += 1) {
    const d = new Array(N_SONGS).fill(0);
    const r = mulberry32(seed * 31 + w * 7 + 1);
    for (let p = 0; p < PEOPLE_PER_WORLD; p += 1) {
      const weights = appeal.map((a, i) => a * (1 + INFLUENCE * d[i]));
      d[pick(weights, r())] += 1;
    }
    downloads.push(d);
  }

  // 钉死那首原例：质量第 26 的歌，在它最好的世界排第 1，在它最差的世界排第 40
  const song = byQuality[25];
  let top = 0;
  let bottom = 0;
  const ranks0 = downloads.map((d) => ranksOf(d));
  for (let w = 1; w < N_WORLDS; w += 1) {
    if (ranks0[w][song] < ranks0[top][song]) top = w;
    if (ranks0[w][song] > ranks0[bottom][song]) bottom = w;
  }
  if (top === bottom) bottom = (top + 3) % N_WORLDS;
  const maxTop = Math.max(...downloads[top].filter((_, i) => i !== song));
  downloads[top][song] = Math.round(maxTop * 1.12) + 4;
  const others = downloads[bottom].filter((_, i) => i !== song).sort((a, b) => b - a);
  downloads[bottom][song] = Math.max(1, Math.floor((others[38] + others[39]) / 2));   // 39 首在它前面 → 第 40

  const rank = downloads.map((d) => ranksOf(d));
  cache = { appeal, qRank, byQuality, control, downloads, rank, example: { song, top, bottom } };
  return cache;
}

/** 某个世界里每首歌的柱高（0..1，最高的那首 = 1） */
export function heightsOf(d: number[]): number[] {
  const m = Math.max(1, ...d);
  return d.map((v) => Math.max(0.03, v / m));
}

/** 对照组的柱高：就是"本来有多好" */
export function appealHeights(w: Worlds): number[] {
  const m = Math.max(...w.appeal);
  return w.appeal.map((a) => a / m);
}

/** 基尼系数（校验用：8 个世界都该比对照组高） */
export function gini(d: number[]): number {
  const n = d.length;
  const total = d.reduce((a, b) => a + b, 0) || 1;
  let s = 0;
  for (const a of d) for (const b of d) s += Math.abs(a - b);
  return s / (2 * n * total);
}
