// 生命游戏：真实演化 + 真实搜索。
// 卡片和取数脚本共用这一份，保证"第几代、什么坐标"不是编的。

export type Grid = Uint8Array;

export const LIFE_W = 58;
export const LIFE_H = 58;

export function idx(x: number, y: number): number {
  return y * LIFE_W + x;
}

/** R-pentomino：5 个细胞，是"最少输入长出最多结构"的经典例子，会自己甩出滑翔机。 */
export function seedRPentomino(): Grid {
  const g = new Uint8Array(LIFE_W * LIFE_H);
  const cx = Math.floor(LIFE_W / 2);
  const cy = Math.floor(LIFE_H / 2);
  for (const [dx, dy] of [
    [1, 0],
    [2, 0],
    [0, 1],
    [1, 1],
    [1, 2],
  ]) {
    g[idx(cx + dx, cy + dy)] = 1;
  }
  return g;
}

export function step(g: Grid): Grid {
  const out = new Uint8Array(LIFE_W * LIFE_H);
  for (let y = 0; y < LIFE_H; y++) {
    for (let x = 0; x < LIFE_W; x++) {
      let n = 0;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = x + dx;
          const ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= LIFE_W || ny >= LIFE_H) continue;
          n += g[idx(nx, ny)];
        }
      }
      const alive = g[idx(x, y)];
      out[idx(x, y)] = alive ? (n === 2 || n === 3 ? 1 : 0) : n === 3 ? 1 : 0;
    }
  }
  return out;
}

/** 演化 n 代，返回每一代（含第 0 代）。 */
export function runLife(gens: number, seed: Grid = seedRPentomino()): Grid[] {
  const out: Grid[] = [seed];
  let g = seed;
  for (let i = 1; i <= gens; i++) {
    g = step(g);
    out.push(g);
  }
  return out;
}

// 滑翔机的两个相位（3x3 窗口内的活细胞）
const PHASES: Array<Array<[number, number]>> = [
  [
    [1, 0],
    [2, 1],
    [0, 2],
    [1, 2],
    [2, 2],
  ],
  [
    [0, 0],
    [2, 0],
    [1, 1],
    [2, 1],
    [1, 2],
  ],
];

export type GliderHit = { gen: number; x: number; y: number; phase: number };

/**
 * 在真实演化结果里找滑翔机：某个 3x3 窗口内恰好是 5 个活细胞且形状匹配。
 * 因为窗口要求"恰好"，静止的方块或噪声不会误判。
 */
export function findGlider(grids: Grid[]): GliderHit | null {
  for (let gen = 0; gen < grids.length; gen++) {
    const g = grids[gen];
    for (let y = 0; y + 2 < LIFE_H; y++) {
      for (let x = 0; x + 2 < LIFE_W; x++) {
        let live = 0;
        const cells = new Set<number>();
        for (let dy = 0; dy < 3; dy++) {
          for (let dx = 0; dx < 3; dx++) {
            if (g[idx(x + dx, y + dy)]) {
              live++;
              cells.add(dy * 3 + dx);
            }
          }
        }
        if (live !== 5) continue;
        for (let p = 0; p < PHASES.length; p++) {
          const match = PHASES[p].every(([dx, dy]) => cells.has(dy * 3 + dx));
          if (match) return { gen, x, y, phase: p };
        }
      }
    }
  }
  return null;
}

/** 某一代里所有活细胞的坐标 */
export function alive(g: Grid): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (let y = 0; y < LIFE_H; y++) {
    for (let x = 0; x < LIFE_W; x++) if (g[idx(x, y)]) out.push([x, y]);
  }
  return out;
}
