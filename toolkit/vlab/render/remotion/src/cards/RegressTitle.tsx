import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp } from "../common/random";

// 片名 / 片尾卡：一颗金珠悬在板顶，下面那块板是空的。
// 定格那一镜（GaltonBoard mode=final）回到同一颗珠子、同一束光——回场就靠这个"同一"。
// 片尾（refs 有内容）不挂珠子：结尾要的是字，不是道具。

type Props = {
  title?: string;
  sub?: string;
  latin?: string;
  /** 标题下面的分隔线最宽多少 */
  rule?: number;
  /** 片尾三行文献线索（片名卡留空） */
  refs?: string[];
  /** 要不要那颗悬着的金珠（片名卡要，片尾不要） */
  bead?: boolean;
  /** 标题字号（默认 240 是两个字的片名；长片名用 110–130） */
  size?: number;
};

export const RegressTitle: React.FC<Props> = ({
  title = "回归",
  sub = "最好的一次之后，必然是更差的一次",
  latin = "REGRESSIO",
  rule = 760,
  refs = [],
  bead = true,
  size = 240,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const t0 = Math.round(fps * 0.25);
  const per = Math.round(fps * 0.09);
  const lineP = clamp((frame - t0 + 4) / (fps * 0.45));
  const subP = clamp((frame - t0 - per * title.length - 6) / (fps * 0.5));
  const latinP = clamp((frame - t0 - per * title.length - fps * 0.45) / (fps * 0.5));
  const drift = 1 + 0.014 * clamp(1 - frame / (fps * 6));

  // 珠子先被光照出来，标题再显影
  const beadP = clamp((frame - Math.round(fps * 0.1)) / (fps * 0.55));
  const bob = Math.sin(frame / 26) * 4;

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
        {/* 一束顶光：只照那颗珠子 */}
        {bead ? (
          <>
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                width: 1920,
                height: 640,
                background:
                  "radial-gradient(360px 420px at 50% 20%, rgba(255,232,180,0.20) 0%, rgba(255,232,180,0.05) 46%, rgba(0,0,0,0) 74%)",
                opacity: beadP,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 960 - 74,
                top: 0,
                width: 148,
                height: 300,
                background:
                  "linear-gradient(180deg, rgba(255,236,190,0.16) 0%, rgba(255,236,190,0.05) 62%, rgba(255,236,190,0) 100%)",
                opacity: beadP * 0.9,
                clipPath: "polygon(38% 0%, 62% 0%, 100% 100%, 0% 100%)",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 960 - 13,
                top: 196 + bob,
                width: 26,
                height: 26,
                borderRadius: 13,
                background:
                  "radial-gradient(circle at 34% 30%, #fff8e2 0%, #f3c14b 54%, #7a5c1c 100%)",
                boxShadow: "0 0 40px rgba(243,193,75,0.8)",
                opacity: beadP,
              }}
            />
            {/* 板顶那条边：观众知道它悬在什么上面 */}
            <div
              style={{
                position: "absolute",
                left: 960 - 300,
                top: 300,
                width: 600,
                height: 1,
                background:
                  "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.22) 50%, rgba(255,255,255,0) 100%)",
                opacity: beadP * 0.7,
              }}
            />
          </>
        ) : null}

        {/* 金线：从中间往两边拉开 */}
        <div
          style={{
            position: "absolute",
            left: 960 - (rule * lineP) / 2,
            top: 352,
            width: rule * lineP,
            height: 1,
            background: `linear-gradient(90deg, rgba(243,193,75,0) 0%, ${C.gold} 50%, rgba(243,193,75,0) 100%)`,
            opacity: 0.85,
          }}
        />

        {/* 标题：逐字显影 */}
        <div
          style={{
            position: "absolute",
            top: 404,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            gap: 18,
            transform: `scale(${drift})`,
            transformOrigin: "50% 50%",
          }}
        >
          {Array.from(title).map((ch, i) => {
            const p = clamp((frame - t0 - i * per) / (fps * 0.36));
            return (
              <span
                key={i}
                style={{
                  fontFamily: FONT,
                  fontWeight: 700,
                  fontSize: size,
                  lineHeight: 1.08,
                  letterSpacing: size >= 200 ? 8 : 4,
                  color: C.ink,
                  opacity: p,
                  filter: `blur(${(1 - p) * 10}px)`,
                  textShadow: "0 0 90px rgba(243,193,75,0.22)",
                }}
              >
                {ch}
              </span>
            );
          })}
        </div>

        {/* 副题 */}
        <div
          style={{
            position: "absolute",
            top: 726,
            left: 0,
            right: 0,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 46,
            letterSpacing: 8,
            color: C.ink,
            opacity: subP * 0.92,
            transform: `translateY(${(1 - subP) * 10}px)`,
          }}
        >
          {sub}
        </div>

        {/* 外文行 */}
        <div
          style={{
            position: "absolute",
            top: 806,
            left: 0,
            right: 0,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 22,
            letterSpacing: 18,
            color: C.dim,
            opacity: latinP * 0.8,
          }}
        >
          {latin}
        </div>

        {/* 文献线索 + 软肋自曝：片尾才有 */}
        {refs.length ? (
          <div style={{ position: "absolute", top: size >= 200 ? 852 : 700, left: 0, right: 0, textAlign: "center" }}>
            {refs.map((r, i) => {
              const p = clamp(
                (frame - t0 - per * title.length - fps * 0.3 - i * fps * 0.16) / (fps * 0.6),
              );
              return (
                <div
                  key={i}
                  style={{
                    fontFamily: FONT,
                    fontSize: 21,
                    lineHeight: 1.85,
                    letterSpacing: 2,
                    color: "rgba(160,168,188,0.78)",
                    opacity: p,
                    transform: `translateY(${(1 - p) * 8}px)`,
                  }}
                >
                  {r}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
