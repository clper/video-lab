import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 一条走廊，俯视。
// 一卷卫生纸从左边的卷轴上抽出来，一直铺到走廊尽头——1,200 米。
// 然后她开始折：纸带一路往回缩，缩到最后变成手上一块小方砖，上面 12 道折痕。
// 三镜用同一张卡：roll（铺开）→ fold（往回折）→ done（方砖 + 8 小时）。

type Props = {
  kicker?: string;
  note?: string;
  /** 这一镜停在哪个阶段 */
  stage?: "roll" | "fold" | "done";
  /** 字幕外的补充：镜末小字 */
  timer?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

// 走廊：左边近、右边远（所以上下两条墙向中间收）
const NEAR = { x: 60, top: 150, bot: 940 };
const FAR = { x: 1860, top: 372, bot: 714 };
const ROLL = { x: 300, y: 540 };
const BRICK = { x: 380, y: 540, w: 260, h: 120 };

const edgeY = (x: number, near: number, far: number) =>
  near + ((far - near) * (x - NEAR.x)) / (FAR.x - NEAR.x);

export const PaperRoll: React.FC<Props> = ({
  kicker = "03 · 墙　THE WALL",
  note = "1,200 米，12 折，8 小时。吉尼斯派人来看了全程。",
  stage = "roll",
  timer = "8:00:00",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();

  const t = frame / fps;
  const dur = durationInFrames / fps;

  // 三个阶段的节奏：先铺开，再折回去，最后落定
  let unroll = 0;
  let fold = 0;
  if (stage === "roll") {
    unroll = ease(t / (dur * 0.62));
  } else if (stage === "fold") {
    unroll = 1;
    fold = ease((t - dur * 0.14) / (dur * 0.66));
  } else {
    unroll = 1;
    fold = 1;
  }

  const corridorP = ease(t / (dur * 0.28));

  // 纸带：铺开时往右长，折叠时往左缩；折完了它就整个变成那块砖
  const tipX = ROLL.x + (FAR.x - ROLL.x - 60) * unroll * (1 - fold);
  // 方砖：折叠时从薄到厚（层数越多越厚）
  const brickP = clamp(fold * 1.15);
  const layers = Math.max(1, Math.round(12 * brickP));
  const foldLines = Math.round(12 * fold);

  const topNear = edgeY(0, NEAR.top, FAR.top);
  const botNear = edgeY(0, NEAR.bot, FAR.bot);

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
        {/* 地板：走廊里那一条 */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            clipPath: `polygon(${NEAR.x}px ${NEAR.top}px, ${FAR.x}px ${FAR.top}px, ${FAR.x}px ${FAR.bot}px, ${NEAR.x}px ${NEAR.bot}px)`,
            background: "linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 60%)",
            opacity: corridorP,
          }}
        />
        {/* 两条墙沿 */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: topNear,
            width: 1920,
            height: 2,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0.24), rgba(255,255,255,0.42) 40%, rgba(255,255,255,0.10))",
            transform: `rotate(${Math.atan2(FAR.top - NEAR.top, FAR.x - NEAR.x)}rad)`,
            transformOrigin: "0 0",
            opacity: corridorP,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 0,
            top: botNear,
            width: 1920,
            height: 2,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0.24), rgba(255,255,255,0.36) 40%, rgba(255,255,255,0.08))",
            transform: `rotate(${Math.atan2(FAR.bot - NEAR.bot, FAR.x - NEAR.x)}rad)`,
            transformOrigin: "0 0",
            opacity: corridorP,
          }}
        />
        {/* 尽头：一小块亮（不是门，就是远处的光） */}
        <div
          style={{
            position: "absolute",
            left: FAR.x - 40,
            top: FAR.top,
            width: 60,
            height: FAR.bot - FAR.top,
            background: "linear-gradient(90deg, rgba(200,220,255,0), rgba(200,220,255,0.16))",
            filter: "blur(6px)",
            opacity: corridorP * 0.9,
          }}
        />

        {/* 地板透视：几条向里收的线和横线，走廊才“深”起来 */}
        <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0, opacity: corridorP * 0.8 }}>
          <defs>
            <clipPath id="corridorClip">
              <polygon
                points={`${NEAR.x},${NEAR.top} ${FAR.x},${FAR.top} ${FAR.x},${FAR.bot} ${NEAR.x},${NEAR.bot}`}
              />
            </clipPath>
          </defs>
          <g clipPath="url(#corridorClip)" stroke="rgba(255,255,255,0.07)" strokeWidth={1}>
            {[-3, -2, -1, 0, 1, 2, 3].map((k) => (
              <line
                key={`v${k}`}
                x1={NEAR.x}
                y1={540 + k * 160}
                x2={FAR.x}
                y2={540 + k * 56}
              />
            ))}
            {[0.2, 0.36, 0.5, 0.62, 0.72].map((d) => {
              const x = NEAR.x + (FAR.x - NEAR.x) * d;
              const top = NEAR.top + (FAR.top - NEAR.top) * d;
              const bot = NEAR.bot + (FAR.bot - NEAR.bot) * d;
              return <line key={`h${d}`} x1={x} y1={top} x2={x} y2={bot} />;
            })}
          </g>
        </svg>

        {/* 纸带 */}
        <div
          style={{
            position: "absolute",
            left: ROLL.x,
            top: ROLL.y - 21,
            width: Math.max(0, tipX - ROLL.x),
            height: 42,
            overflow: "hidden",
            // 纸带也要跟着走廊收窄：宽度不变的话，它就像挂在走廊前面的一块布
            clipPath: "polygon(0 0, 100% 12px, 100% 30px, 0 42px)",
            background: "linear-gradient(180deg, #fffdf6 0%, #f8f2e4 50%, #e9dfc9 100%)",
            boxShadow: "0 8px 40px rgba(0,0,0,0.5), inset 0 -1px 0 rgba(150,135,105,0.45)",
            opacity: clamp(unroll * 2) * clamp(1 - fold * 1.6),
          }}
        >
          {/* 纸纹 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(90deg, rgba(160,140,100,0.14) 0 1px, rgba(160,140,100,0) 1px 9px)",
            }}
          />
          {/* 折出来的印子：每折一次，纸带上就多一道竖向的痕 */}
          {Array.from({ length: foldLines }, (_, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                left: 40 + i * 46,
                top: -2,
                bottom: -2,
                width: 2,
                background: "rgba(120,105,80,0.55)",
                boxShadow: "0 0 10px rgba(0,0,0,0.5)",
              }}
            />
          ))}
        </div>

        {/* 卷轴：折完了它就空了，淡出去 */}
        <div
          style={{
            position: "absolute",
            left: ROLL.x - 58,
            top: ROLL.y - 58,
            width: 116,
            height: 116,
            borderRadius: 58,
            background: "linear-gradient(150deg, #fffdf6 0%, #f2e9d5 55%, #cfc2a4 100%)",
            boxShadow: "0 0 60px rgba(255,232,180,0.16), inset 0 0 0 1px rgba(255,255,255,0.5)",
            // 折完就彻底空掉：留 0.1 会变成一个脏盘子
            opacity: corridorP * clamp(1 - fold * 1.25),
            transform: `scale(${1 - 0.35 * fold})`,
            transformOrigin: "50% 50%",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 44,
              top: 44,
              width: 28,
              height: 28,
              borderRadius: 14,
              background: "#0a0c14",
              boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.18)",
            }}
          />
        </div>

        {/* 方砖：折叠的结果。一层一层画，不要用重复渐变 —— 12 层是数得出来的 */}
        {brickP > 0.02 ? (
          <div
            style={{
              position: "absolute",
              left: BRICK.x,
              top: BRICK.y - (BRICK.h * brickP) / 2,
              width: BRICK.w,
              height: Math.max(6, BRICK.h * brickP),
              overflow: "hidden",
              boxShadow:
                "0 24px 70px rgba(0,0,0,0.7), inset 0 0 0 1px rgba(255,246,220,0.4), 0 0 60px rgba(243,193,75,0.14)",
              opacity: clamp(brickP * 1.6),
            }}
          >
            {Array.from({ length: 12 }, (_, i) => (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  top: `${(i * 100) / 12}%`,
                  height: `${100 / 12}%`,
                  background:
                    i % 2 === 0
                      ? "linear-gradient(180deg, #fffdf6, #f4ecd8)"
                      : "linear-gradient(180deg, #f6efdd, #d9ccab)",
                  opacity: clamp((foldLines - i) / 2),
                }}
              />
            ))}
            <div
              style={{
                position: "absolute",
                left: -2,
                right: -2,
                top: -2,
                height: 3,
                background: "#fff3d0",
                boxShadow: "0 0 26px rgba(255,226,150,0.9)",
              }}
            />
          </div>
        ) : null}

        {/* 章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(corridorP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>{kicker}</div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 右上：长度 / 折数 / 计时 */}
        <div style={{ position: "absolute", right: 120, top: 150, textAlign: "right" }}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 20,
              letterSpacing: 7,
              color: "rgba(139,147,167,0.8)",
              opacity: clamp(corridorP * 2),
            }}
          >
            一张纸的长度
          </div>
          <div
            style={{
              marginTop: 6,
              fontFamily: FONT,
              fontWeight: 700,
              fontSize: 78,
              lineHeight: 1,
              color: C.ink,
              fontVariantNumeric: "tabular-nums",
              opacity: clamp(corridorP * 2),
            }}
          >
            1,200<span style={{ fontSize: 34, marginLeft: 8, color: C.dim }}>米</span>
          </div>
          {stage !== "roll" ? (
            <div style={{ marginTop: 22, opacity: clamp(fold * 1.4) }}>
              <div style={{ height: 1, width: 220, background: "rgba(255,255,255,0.14)", marginLeft: "auto" }} />
              <div
                style={{
                  marginTop: 16,
                  fontFamily: FONT,
                  fontSize: 34,
                  letterSpacing: 2,
                  color: C.gold,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {Math.round(12 * fold)} 折
              </div>
              {stage === "done" ? (
                <div
                  style={{
                    marginTop: 10,
                    fontFamily: FONT,
                    fontSize: 30,
                    letterSpacing: 4,
                    color: "rgba(246,242,231,0.8)",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {timer}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* 左下的说明：抬高一点，别碰字幕 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            bottom: 186,
            width: 620,
            fontFamily: FONT,
            fontSize: 22,
            lineHeight: 1.8,
            letterSpacing: 1,
            color: "rgba(139,147,167,0.72)",
            opacity: clamp(corridorP * 1.6),
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
