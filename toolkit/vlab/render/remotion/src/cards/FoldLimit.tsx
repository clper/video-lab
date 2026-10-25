import React from "react";
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { AbsoluteFill } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// "八次就是极限"——不画手，画一条容量条。
// 九格：前八格一格一格点亮，每格底下挂它折完的层数（2…256）；
// 第九格永远是空的，红叉从中间压下去。看得见"满"，才看得懂"停"。

type Props = {
  /** 一共画几格（含那个空的） */
  slots?: number;
  /** 点亮到第几格 */
  lit?: number;
  kicker?: string;
  note?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));

const N = 9;
const CELL_W = 150;
const CELL_H = 236;
const GAP = 18;
const ROW_W = N * CELL_W + (N - 1) * GAP;
const X0 = 960 - ROW_W / 2;
const ROW_Y = 316;

export const FoldLimit: React.FC<Props> = ({
  slots = N,
  lit = 8,
  kicker = "传说 · 手折上限",
  note = "每折一次，层数翻一倍",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const total = slots;
  const shown = Math.min(lit, total);
  const cells = Array.from({ length: total }, (_, i) => i + 1);

  // 一格一格亮：起手 0.2s，每格 0.22s
  const cellP = (i: number) => clamp((frame / fps - 0.2 - (i - 1) * 0.22) / 0.26);
  const crossP = clamp((frame / fps - 0.2 - shown * 0.22 - 0.18) / 0.4);
  const capsP = interpolate(frame, [Math.round(fps * 0.1), Math.round(fps * 0.5)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const ROW_W2 = total * CELL_W + (total - 1) * GAP;
  const x0 = 960 - ROW_W2 / 2;

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
        {/* 章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 118,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 8,
            color: C.cyan,
            opacity: capsP,
          }}
        >
          {kicker}
        </div>

        {/* 一行九格 */}
        {cells.map((i) => {
          const p = cellP(i);
          const x = x0 + (i - 1) * (CELL_W + GAP);
          const isLast = i === total;
          const empty = i > shown;
          if (p <= 0 && !empty) return null;
          return (
            <React.Fragment key={i}>
              <div
                style={{
                  position: "absolute",
                  left: x,
                  top: ROW_Y,
                  width: CELL_W,
                  height: CELL_H,
                  border: empty ? "1px dashed rgba(139,147,167,0.34)" : "1px solid rgba(248,242,228,0.22)",
                  background: empty
                    ? "transparent"
                    : "linear-gradient(180deg, rgba(248,242,228,0.96), rgba(232,222,199,0.9))",
                  boxShadow: empty ? "none" : "0 0 34px rgba(255,232,180,0.16)",
                  opacity: empty ? capsP * (isLast ? 1 : 0) : p,
                  transform: `translateY(${(1 - p) * 14}px)`,
                }}
              >
                {!empty ? (
                  <>
                    {/* 层：一格就是 2 层、4 层……用横纹表现出来，不写"厚" */}
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        right: 0,
                        bottom: 0,
                        height: `${18 + i * 8}%`,
                        background:
                          "repeating-linear-gradient(180deg, #fffdf6 0px, #fffdf6 2px, #cdbf9f 2px, #cdbf9f 3.4px)",
                        opacity: 0.85,
                      }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        right: 0,
                        top: 12,
                        textAlign: "center",
                        fontFamily: FONT,
                        fontWeight: 700,
                        fontSize: 46,
                        color: "#171410",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {i}
                    </div>
                  </>
                ) : null}
              </div>

              {/* 格下：层数 */}
              <div
                style={{
                  position: "absolute",
                  left: x,
                  top: ROW_Y + CELL_H + 18,
                  width: CELL_W,
                  textAlign: "center",
                  fontFamily: FONT,
                  fontSize: 26,
                  letterSpacing: 1,
                  color: empty ? "rgba(139,147,167,0.7)" : "rgba(139,147,167,0.95)",
                  fontVariantNumeric: "tabular-nums",
                  opacity: empty ? capsP : p,
                }}
              >
                {empty ? "第 9 次" : `${Math.pow(2, i)} 层`}
              </div>
            </React.Fragment>
          );
        })}

        {/* 红叉：压在空的第九格上 */}
        {crossP > 0 ? (
          <svg
            style={{
              position: "absolute",
              left: x0 + (total - 1) * (CELL_W + GAP) - 10,
              top: ROW_Y - 10,
              overflow: "visible",
            }}
            width={CELL_W + 20}
            height={CELL_H + 20}
          >
            <g
              stroke={C.red}
              strokeWidth={4}
              strokeLinecap="round"
              opacity={crossP * 0.95}
              style={{ filter: "drop-shadow(0 0 12px rgba(255,91,91,0.7))" }}
            >
              <line
                x1={10}
                y1={10}
                x2={CELL_W + 10}
                y2={CELL_H + 10}
                pathLength={1}
                strokeDasharray={1}
                strokeDashoffset={1 - crossP}
              />
              <line
                x1={CELL_W + 10}
                y1={10}
                x2={10}
                y2={CELL_H + 10}
                pathLength={1}
                strokeDasharray={1}
                strokeDashoffset={1 - crossP}
              />
            </g>
          </svg>
        ) : null}

        {/* 底注 */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: ROW_Y + CELL_H + 84,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 26,
            letterSpacing: 4,
            color: "rgba(139,147,167,0.72)",
            opacity: capsP,
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
