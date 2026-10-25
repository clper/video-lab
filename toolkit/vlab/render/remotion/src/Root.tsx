import React from "react";
import { Composition } from "remotion";
import "./common/fonts";
import "./global.css";
import { Sample15s } from "./compositions/Sample15s";
import { Shot, ShotProps } from "./compositions/Shot";
import { ASPECT } from "./design/tokens";

const DEFAULT_SHOT: ShotProps = {
  card: "particleText",
  params: {},
  durationInFrames: 150,
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Sample15s"
        component={Sample15s}
        durationInFrames={450}
        fps={ASPECT.fps}
        width={ASPECT.width}
        height={ASPECT.height}
      />
      {/* 通用单镜头组合：Python 桥用 --props 指定 card / params / durationInFrames */}
      <Composition
        id="Shot"
        component={Shot}
        durationInFrames={DEFAULT_SHOT.durationInFrames}
        fps={ASPECT.fps}
        width={ASPECT.width}
        height={ASPECT.height}
        defaultProps={DEFAULT_SHOT}
        calculateMetadata={({ props }) => ({
          durationInFrames: Math.max(1, Math.round(props.durationInFrames ?? 150)),
          fps: Math.max(1, Math.round(props.fps ?? ASPECT.fps)),
          // 画幅由 Python 桥按工程传进来（竖屏 1080×1920 / 横屏 1920×1080）
          width: Math.max(2, Math.round(props.width ?? ASPECT.width)),
          height: Math.max(2, Math.round(props.height ?? ASPECT.height)),
        })}
      />
    </>
  );
};
