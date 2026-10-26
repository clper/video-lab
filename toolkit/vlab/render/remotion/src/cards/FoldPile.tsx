import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 桌上八个位置：七块折废的纸，第八块空着。
// 这一镜不讲道理，只摆事实——折到第七次，桌上就堆满了，没有人再往下折。

type Props = {
  /** 摆了几块 */
  count?: number;
  kicker?: string;
  note?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));

const SLOT_W = 176;
const GAP = 30;
const SLOTS = 8;
const ROW_W = SLOTS * SLOT_W + (SLOTS - 1) * GAP;
const X0 = 1920 - (1920 - ROW_W) / 2 - ROW_W; // 居中
const TABLE_Y = 636;

// 七块各不相同：宽、高、歪多少都手动给死，别让它看起来是复制粘贴
const SCRAPS = [
  { w: 118, h: 96, tilt: -3.4, skew: -7 },
  { w: 104, h: 104, tilt: 2.2, skew: -6 },
  { w: 124, h: 88, tilt: -1.6, skew: -8 },
  { w: 96, h: 112, tilt: 3.1, skew: -5 },
  { w: 112, h: 100, tilt: -2.4, skew: -7 },
  { w: 88, h: 118, tilt: 1.4, skew: -6 },
  { w: 106, h: 108, tilt: -2, skew: -7 },
];

export const FoldPile: React.FC<Props> = ({
  count = 7,
  kicker = "章一 · 手",
  note = "七块折废的纸。第八个位置，空着。",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const inP = clamp(frame / (fps * 0.4));
  const emptyP = clamp((frame / fps - 0.3 - count * 0.16 - 0.25) / 0.45);

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
        {/* 桌面 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: TABLE_Y,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.14) 30%, rgba(255,255,255,0.14) 70%, rgba(255,255,255,0) 100%)",
            opacity: inP,
          }}
        />

        <div
          style={{
            position: "absolute",
            left: 120,
            top: 118,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 8,
            color: C.cyan,
            opacity: inP,
          }}
        >
          {kicker}
        </div>

        {Array.from({ length: SLOTS }, (_, i) => {
          const x = X0 + i * (SLOT_W + GAP);
          const isLast = i === SLOTS - 1;
          const scrap = SCRAPS[i % SCRAPS.length];

          if (isLast) {
            return (
              <React.Fragment key={i}>
                <div
                  style={{
                    position: "absolute",
                    left: x,
                    top: TABLE_Y - 124,
                    width: SLOT_W,
                    height: 124,
                    border: "1px dashed rgba(139,147,167,0.4)",
                    background: "transparent",
                    opacity: emptyP,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: x,
                    top: TABLE_Y - 90,
                    width: SLOT_W,
                    textAlign: "center",
                    fontFamily: FONT,
                    fontSize: 64,
                    fontWeight: 700,
                    color: "rgba(139,147,167,0.4)",
                    opacity: emptyP,
                  }}
                >
                  ?
                </div>
                <div
                  style={{
                    position: "absolute",
                    left: x - 10,
                    top: TABLE_Y + 16,
                    width: SLOT_W + 20,
                    textAlign: "center",
                    fontFamily: FONT,
                    fontSize: 22,
                    letterSpacing: 2,
                    color: "rgba(139,147,167,0.75)",
                    opacity: emptyP,
                  }}
                >
                  第 8 次
                </div>
              </React.Fragment>
            );
          }

          if (i >= count) return null;

          const drop = spring({
            frame: frame - Math.round(fps * 0.18) - i * Math.round(fps * 0.14),
            fps,
            config: { damping: 13, stiffness: 170, mass: 0.7 },
          });
          // 16:9 里桌子靠上，纸块也放大一号，不然下面大片空
          const sw = Math.round(scrap.w * 1.22);
          const sh = Math.round(scrap.h * 1.22);

          return (
            <React.Fragment key={i}>
              {/* 影子 */}
              <div
                style={{
                  position: "absolute",
                  left: x - 6,
                  top: TABLE_Y - 8,
                  width: SLOT_W + 12,
                  height: 40,
                  background:
                    "radial-gradient(ellipse at 50% 20%, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 70%)",
                  opacity: drop,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: x + (SLOT_W - sw) / 2,
                  top: TABLE_Y - sh - 8,
                  width: sw,
                  height: sh,
                  transform: `translateY(${(1 - drop) * -70}px) rotate(${scrap.tilt}deg) skewX(${scrap.skew}deg)`,
                  background:
                    "repeating-linear-gradient(180deg, #fffdf6 0px, #fffdf6 2.1px, #cdbf9f 2.1px, #cdbf9f 3.4px)",
                  boxShadow:
                    "inset 0 0 0 1px rgba(255,246,220,0.5), 0 18px 50px rgba(0,0,0,0.75), 0 0 40px rgba(255,232,180,0.10)",
                  opacity: drop,
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: -1,
                    right: -1,
                    top: -1,
                    height: 2,
                    background: "#fff6df",
                    boxShadow: "0 0 18px rgba(255,226,150,0.7)",
                  }}
                />
              </div>
              <div
                style={{
                  position: "absolute",
                  left: x,
                  top: TABLE_Y + 16,
                  width: SLOT_W,
                  textAlign: "center",
                  fontFamily: FONT,
                  fontSize: 22,
                  color: "rgba(139,147,167,0.6)",
                  opacity: drop,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {i + 1}
              </div>
            </React.Fragment>
          );
        })}

        <div
          style={{
            position: "absolute",
            left: 120,
            top: TABLE_Y + 104,
            fontFamily: FONT,
            fontSize: 26,
            letterSpacing: 2,
            color: "rgba(139,147,167,0.8)",
            opacity: emptyP,
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
