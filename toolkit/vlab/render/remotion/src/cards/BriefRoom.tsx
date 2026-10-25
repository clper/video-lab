import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp } from "../common/random";

// 简报室：钩子那一幕 —— 两个人影，一束顶光，一句当众说出来的反驳。
// 不做脸（合规也省事）：剪影 + 轮廓光，情绪靠构图和光给。
// 整个片子的钩子就靠这 4 秒立住，所以这张卡只干一件事。

type Props = {
  kicker?: string;
  /** 屏上的字（大字） */
  line?: string;
  sub?: string;
};

export const BriefRoom: React.FC<Props> = ({
  kicker = "以色列空军 · 一堂飞行教官的课",
  line = "他站了起来",
  sub = "D. KAHNEMAN",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const p = clamp((frame - fps * 0.1) / (fps * 0.8));
  const textP = clamp((frame - fps * 0.6) / (fps * 0.5));

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: 1920,
          height: 1080,
          transform: `translate(-50%, -50%) scale(${s})`,
        }}
      >
        {/* 房间：几乎全黑，只有一束光打在桌子中间 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "linear-gradient(180deg, #04050a 0%, #070b14 60%, #05070d 100%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 960 - 220,
            top: 0,
            width: 440,
            height: 700,
            background:
              "linear-gradient(180deg, rgba(255,236,190,0.20) 0%, rgba(255,236,190,0.05) 58%, rgba(255,236,190,0) 100%)",
            clipPath: "polygon(42% 0%, 58% 0%, 100% 100%, 0% 100%)",
            opacity: p * 0.9,
          }}
        />
        {/* 桌面：光落在一条线上 */}
        <div
          style={{
            position: "absolute",
            left: 960 - 340,
            top: 690,
            width: 680,
            height: 2,
            background:
              "linear-gradient(90deg, rgba(255,232,180,0) 0%, rgba(255,232,180,0.55) 50%, rgba(255,232,180,0) 100%)",
            opacity: p,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 960 - 340,
            top: 692,
            width: 680,
            height: 200,
            background:
              "linear-gradient(180deg, rgba(255,232,180,0.07) 0%, rgba(255,232,180,0) 100%)",
            opacity: p,
          }}
        />

        {/* 坐着的那个人（卡尼曼）：桌子后面，正脸 */}
        <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, opacity: p }}>
          <g transform="translate(1150, 500)">
            <circle cx="0" cy="66" r="30" fill="#0a0e18" stroke="rgba(255,232,190,0.5)" strokeWidth={1.6} />
            <path d="M-52 190 L-40 118 Q0 96 40 118 L52 190 Z" fill="#0a0e18" stroke="rgba(255,232,190,0.5)" strokeWidth={1.6} />
          </g>
          {/* 站着的那个人（教官）：正要说话 */}
          <g transform="translate(720, 430)">
            <circle cx="0" cy="70" r="34" fill="#0a0e18" stroke="rgba(226,236,248,0.55)" strokeWidth={1.6} />
            <path d="M-60 262 L-46 128 Q0 102 46 128 L60 262 Z" fill="#0a0e18" stroke="rgba(226,236,248,0.55)" strokeWidth={1.6} />
            {/* 抬起来指向对方的那只手 */}
            <path d="M44 150 L96 118" stroke="rgba(226,236,248,0.55)" strokeWidth={9} strokeLinecap="round" fill="none" />
          </g>
        </svg>

        {/* 左上章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(p * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>
            {kicker}
          </div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 屏上的字 */}
        <div
          style={{
            position: "absolute",
            left: 148,
            top: 300,
            width: 480,
            fontFamily: FONT,
            fontSize: 58,
            fontWeight: 700,
            lineHeight: 1.5,
            letterSpacing: 3,
            color: C.ink,
            opacity: textP,
            transform: `translateY(${(1 - textP) * 14}px)`,
            textShadow: "0 0 40px rgba(0,0,0,0.7)",
          }}
        >
          {line}
        </div>

        <div
          style={{
            position: "absolute",
            left: 152,
            top: 300 + 190,
            fontFamily: FONT,
            fontSize: 21,
            letterSpacing: 8,
            color: C.dim,
            opacity: textP * 0.85,
          }}
        >
          {sub}
        </div>
      </div>
    </AbsoluteFill>
  );
};
