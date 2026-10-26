import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 一张纸：立着，微微侧过身，悬在桌面上方 30 像素。
// 一条金线从纸的下缘垂到桌面——"量"这个动作第一次出现，到章二它就长成那把 42 格的尺。
// 这里只演厚度，不演花活：一张纸立在黑里，纸边一道光，就够了。

type Props = {
  kicker?: string;
  note?: string;
  /** 右侧读数的抬头 */
  label?: string;
  /** 厚度（毫米） */
  mm?: number;
  /** 层数 */
  layers?: number;
  readout?: boolean;
  /** 打在纸面上的一行大字（如一个问号） */
  stamp?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const BASE_Y = 720; // 桌面
const CX = 800;
const W = 840;
const H = 510;
const GAP = 30; // 纸悬在桌面上方多少

export const FoldPage: React.FC<Props> = ({
  kicker = "一张纸 · 80 克复印纸",
  note = "0.1 毫米 —— 比头发丝还薄一点",
  label = "现在这么厚",
  mm = 0.1,
  layers = 1,
  readout = true,
  stamp,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const pageP = ease((frame - 2) / (fps * 0.85));
  const lineP = ease((frame - Math.round(fps * 0.45)) / (fps * 0.6));
  const drift = 1 + 0.012 * clamp(1 - frame / (fps * 7)); // 极慢的呼吸，别让画面死住

  const sheetTop = BASE_Y - GAP - H;
  const sheetBottom = BASE_Y - GAP;

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
        {/* 桌面：一道极淡的光带 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: BASE_Y,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.10) 22%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0.10) 78%, rgba(255,255,255,0) 100%)",
            opacity: pageP,
          }}
        />

        {/* 纸落在桌上的影子：光从左上来，影子往右下偏 */}
        <div
          style={{
            position: "absolute",
            left: CX - 420,
            top: BASE_Y - 12,
            width: 840,
            height: 74,
            background: "radial-gradient(ellipse at 50% 34%, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0) 70%)",
            opacity: pageP,
          }}
        />

        {/* 灯从左上落下来，纸中间一块软高光 */}
        <div
          style={{
            position: "absolute",
            left: CX - W / 2,
            top: sheetTop - 140,
            width: W,
            height: H + 280,
            background:
              "radial-gradient(ellipse at 42% 48%, rgba(255,240,200,0.16) 0%, rgba(255,240,200,0) 62%)",
            opacity: pageP,
          }}
        />

        {/* 那张纸 */}
        <div
          style={{
            position: "absolute",
            left: CX - W / 2,
            top: sheetTop,
            width: W,
            height: H,
            transform: `perspective(1700px) rotateY(-21deg) rotateX(7deg) rotateZ(-1.2deg) scale(${drift}) translateY(${(1 - pageP) * 16}px)`,
            background: "linear-gradient(168deg, #fffdf6 0%, #f8f2e4 52%, #eee4cf 100%)",
            boxShadow:
              "-26px 34px 90px rgba(0,0,0,0.55), inset 0 0 0 1px rgba(255,250,235,0.6), 0 0 130px rgba(255,235,180,0.08)",
            opacity: pageP,
          }}
        >
          {/* 纸的纤维：三组周期不一样、极淡的纹，合起来像纤维，不像瓦楞 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(0deg, rgba(150,124,80,0.013) 0px, rgba(150,124,80,0.013) 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 7px)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(0deg, rgba(255,255,255,0.06) 0px, rgba(255,255,255,0.06) 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 13px)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(90deg, rgba(150,124,80,0.011) 0px, rgba(150,124,80,0.011) 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 11px)",
            }}
          />
          {/* 灯从左上来：左上角亮，右下角压暗 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(118deg, rgba(255,255,255,0.62) 0%, rgba(255,255,255,0.12) 34%, rgba(120,104,74,0.06) 62%, rgba(40,34,24,0.22) 100%)",
            }}
          />
          {/* 左边一道高光边 */}
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              bottom: 0,
              width: 3,
              background: "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.25))",
            }}
          />
          {/* 下缘：纸的厚度就在这一条上 */}
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 0,
              height: 5,
              background: "linear-gradient(90deg, #fffdf6, #fff4d8 50%, #f0e4c8)",
              boxShadow: "0 0 30px rgba(255,232,180,0.7), 0 0 6px rgba(255,246,220,0.9)",
            }}
          />
          {/* 纸面上的一行大字：一个问号停在纸上 */}
          {stamp ? (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: 240,
                lineHeight: 1,
                color: "rgba(120,96,50,0.16)",
                transform: `scale(${1 + 0.04 * Math.sin((frame / fps) * 2.4)})`,
              }}
            >
              {stamp}
            </div>
          ) : null}
        </div>

        {/* 金线：从纸的下缘垂到桌面，这一次是"量" */}
        <div
          style={{
            position: "absolute",
            left: CX,
            top: sheetBottom,
            width: 1,
            height: GAP * lineP,
            background: "linear-gradient(180deg, #ffe6a8, rgba(243,193,75,0.25))",
            boxShadow: "0 0 14px rgba(243,193,75,0.75)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: CX - 13,
            top: BASE_Y,
            width: 26,
            height: 1,
            background: "rgba(243,193,75,0.5)",
            opacity: lineP,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: CX - 3,
            top: BASE_Y - 3,
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: C.gold,
            boxShadow: `0 0 18px ${C.gold}`,
            opacity: lineP,
          }}
        />

        {/* 左上章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 118,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 8,
            color: C.cyan,
            opacity: pageP,
          }}
        >
          {kicker}
        </div>

        {/* 说明放桌线下面，像展签，不去和字幕抢横向 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: BASE_Y + 44,
            fontFamily: FONT,
            fontSize: 23,
            letterSpacing: 2,
            color: "rgba(139,147,167,0.82)",
            opacity: pageP,
          }}
        >
          {note}
        </div>

        {/* 右侧读数 */}
        {readout ? (
          <div
            style={{
              position: "absolute",
              left: 1380,
              top: 286,
              width: 420,
              opacity: pageP,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 26,
                letterSpacing: 6,
                color: C.dim,
                marginBottom: 10,
              }}
            >
              {label}
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <div
                style={{
                  fontFamily: FONT,
                  fontWeight: 700,
                  fontSize: 132,
                  lineHeight: 1,
                  color: C.gold,
                  fontVariantNumeric: "tabular-nums",
                  textShadow: "0 0 50px rgba(243,193,75,0.35)",
                }}
              >
                {mm < 10 ? mm.toFixed(1) : Math.round(mm * 10) / 10}
              </div>
              <div style={{ fontFamily: FONT, fontSize: 40, color: C.ink }}>mm</div>
            </div>
            <div
              style={{
                marginTop: 22,
                height: 1,
                width: 320,
                background: "rgba(255,255,255,0.12)",
              }}
            />
            <div
              style={{
                marginTop: 18,
                fontFamily: FONT,
                fontSize: 30,
                color: C.dim,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {layers} 层
            </div>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
