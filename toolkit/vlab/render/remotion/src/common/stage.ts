// 画幅无关的设计舞台。
// 新的镜头卡都在 1920×1080 的设计坐标系里画，再整体缩放到实际画幅：
// 横屏 1920×1080 时缩放 1，竖屏 1080×1920 时缩到 0.5625 居中（仍能出片，只是上下留黑给它自己补）。
import { useVideoConfig } from "remotion";

export const DESIGN = { w: 1920, h: 1080 } as const;

export const useStage = () => {
  const { width, height } = useVideoConfig();
  const s = Math.min(width / DESIGN.w, height / DESIGN.h);
  return { w: width, h: height, s, wide: width > height };
};

/** 一条字幕安全线：横屏时字幕贴在 y≈980，内容别压过去 */
export const SAFE_BOTTOM = 860;
