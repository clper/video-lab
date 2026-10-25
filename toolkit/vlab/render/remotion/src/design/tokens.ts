// 一套设计 token，所有镜头卡只认这里的名字，不写死颜色/字号。
// 与 vlab 风格文件（style.yaml）的调色板保持同一家族：深底 + 金/青强调。

export const C = {
  bg: "#06070d",
  bg2: "#0e1424",
  ink: "#f6f2e7",
  dim: "#8b93a7",
  gold: "#f3c14b",
  goldDim: "#7a5c1c",
  cyan: "#49e3d1",
  magenta: "#e86bd4",
  red: "#ff5b5b",
} as const;

export const FONT = "SourceHanSansCN";

// 统一的缓动/间距，避免每个镜头各写一套
export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
export const SP = 8;

export const ASPECT = { width: 1080, height: 1920, fps: 30 } as const;
