import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 章二的竖尺横过来了：量长度。
// 纸带从左边抽出来，尺跟着往前长；到 1,200 米的时候纸带直接冲出画框——
// 那一冲比任何数字都说明"这条走廊装不下"。
// 左下角是 Gallivan 那个公式，灰色，只当脚注，不当主角。

type Props = {
  kicker?: string;
  note?: string;
  /** 量到多少米 */
  meters?: number;
  /** 折几次要这么长（只用来标在尺头） */
  folds?: number;
  /** 公式浮出来 */
  formula?: boolean;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const X0 = 190;
const X1 = 1680;
const BASE_Y = 700;

export const PaperLength: React.FC<Props> = ({
  kicker = "03 · 墙　THE WALL",
  note = "算一次要多少纸，就把「折不折得动」换成了「买不买得起」。",
  meters = 1200,
  folds = 12,
  formula = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  // 先有尺，再有纸，最后读数
  const rulerP = ease((frame - 2) / (fps * 0.7));
  const paperP = ease((frame - Math.round(fps * 0.5)) / (fps * 1.1));
  const numP = ease((frame - Math.round(fps * 1.1)) / (fps * 0.7));
  const formP = ease((frame - Math.round(fps * 0.9)) / (fps * 0.9));

  const tipX = X0 + (X1 - X0) * 0.86 * paperP;         // 尺头不贴边，留出"还在长"的余地
  // 读数固定在尺尾右上方（右对齐），不跟着尺头跑 —— 跟着跑必然会顶出画框
  const ticks = Array.from({ length: 13 }, (_, i) => i);
  // 冲出画框：纸带尾巴越过 X1，箭头接着往外
  const burst = clamp((paperP - 0.82) / 0.18);

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
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(rulerP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>{kicker}</div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 尺杆 */}
        <div
          style={{
            position: "absolute",
            left: X0,
            top: BASE_Y,
            width: (X1 - X0) * rulerP,
            height: 2,
            background: "linear-gradient(90deg, rgba(255,255,255,0.5), rgba(255,255,255,0.16))",
          }}
        />
        {/* 刻度 */}
        {ticks.map((i) => {
          const major = i % 3 === 0;
          const x = X0 + ((X1 - X0) * i) / 12;
          if (i / 12 > rulerP) return null;
          return (
            <div key={i}>
              <div
                style={{
                  position: "absolute",
                  left: x,
                  top: BASE_Y,
                  width: 1,
                  height: major ? 34 : 18,
                  background: major ? "rgba(255,255,255,0.42)" : "rgba(255,255,255,0.2)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: x - 40,
                  top: BASE_Y + 44,
                  width: 80,
                  textAlign: "center",
                  fontFamily: FONT,
                  fontSize: 20,
                  letterSpacing: 1,
                  color: "rgba(139,147,167,0.75)",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {Math.round((meters * i) / 12)}
              </div>
            </div>
          );
        })}

        {/* 单位 */}
        <div
          style={{
            position: "absolute",
            left: X0,
            top: BASE_Y + 96,
            fontFamily: FONT,
            fontSize: 22,
            letterSpacing: 6,
            color: "rgba(139,147,167,0.6)",
          }}
        >
          米
        </div>

        {/* 纸带：从尺头上方抽出来 */}
        <div
          style={{
            position: "absolute",
            left: X0,
            top: BASE_Y - 46,
            width: Math.max(0, tipX - X0 + 40 * burst),
            height: 40,
            background:
              "linear-gradient(180deg, #fffdf6 0%, #f8f2e4 52%, #efe6d2 100%)",
            boxShadow:
              "inset 0 -1px 0 rgba(190,175,140,0.55), 0 0 40px rgba(255,232,180,0.16)",
            transform: `scaleX(${0.02 + 0.98 * paperP})`,
            transformOrigin: "left center",
          }}
        >
          {/* 纸纹 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(90deg, rgba(160,140,100,0.16) 0 1px, rgba(160,140,100,0) 1px 7px)",
            }}
          />
          {/* 头上一道亮边 */}
          <div
            style={{
              position: "absolute",
              right: 0,
              top: 0,
              bottom: 0,
              width: 3,
              background: "#fff3d0",
              boxShadow: "0 0 26px rgba(255,226,150,0.9)",
            }}
          />
        </div>

        {/* 尺尾读数：右对齐钉在 1720，字号再大也不会出画 */}
        <div
          style={{
            position: "absolute",
            right: 200,
            top: BASE_Y - 262,
            textAlign: "right",
            opacity: numP,
            transform: `translateY(${(1 - numP) * 14}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontWeight: 700,
              fontSize: 96,
              lineHeight: 1,
              color: C.gold,
              fontVariantNumeric: "tabular-nums",
              textShadow: "0 0 50px rgba(243,193,75,0.3)",
            }}
          >
            {Math.round(meters * paperP).toLocaleString("en-US")}
            <span style={{ fontSize: 40, marginLeft: 10, color: C.ink }}>米</span>
          </div>
          <div
            style={{
              marginTop: 14,
              fontFamily: FONT,
              fontSize: 26,
              letterSpacing: 3,
              color: "rgba(139,147,167,0.9)",
            }}
          >
            折 {folds} 次，就要这么长
          </div>
          {/* 一根细竖线从这里落到纸带的头上，把读数与尺头连起来 */}
          <div
            style={{
              position: "absolute",
              right: 34,
              top: 96,
              width: 1,
              height: 150,
              background: "linear-gradient(180deg, rgba(243,193,75,0.55), rgba(243,193,75,0))",
            }}
          />
        </div>

        {/* 冲出画框：一个小箭头和"还有" */}
        <div
          style={{
            position: "absolute",
            left: X1 - 40,
            top: BASE_Y - 34,
            opacity: burst,
            fontFamily: FONT,
            fontSize: 40,
            color: "rgba(246,242,231,0.9)",
          }}
        >
          →
        </div>

        {/* 脚注公式 */}
        {formula ? (
          <div
            style={{
              position: "absolute",
              left: 120,
              top: 200,
              opacity: formP * 0.9,
              transform: `translateY(${(1 - formP) * 12}px)`,
            }}
          >
            <div style={{ fontFamily: FONT, fontSize: 20, letterSpacing: 6, color: "rgba(139,147,167,0.7)" }}>
              折 n 次需要的纸长
            </div>
            <div
              style={{
                marginTop: 10,
                fontFamily: FONT,
                fontSize: 38,
                letterSpacing: 2,
                color: "rgba(246,242,231,0.86)",
              }}
            >
              L = <span style={{ color: C.cyan }}>πt</span>/6 · (2
              <span style={{ fontSize: 22, verticalAlign: "super" }}>n</span>+4)(2
              <span style={{ fontSize: 22, verticalAlign: "super" }}>n</span>−1)
            </div>
            <div
              style={{
                marginTop: 18,
                width: 620,
                fontFamily: FONT,
                fontSize: 21,
                lineHeight: 1.8,
                letterSpacing: 1,
                color: "rgba(139,147,167,0.72)",
              }}
            >
              {note}
            </div>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
