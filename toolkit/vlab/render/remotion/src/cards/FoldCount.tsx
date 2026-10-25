import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 层数记事板：左边一个大数在翻倍，右边一条竖着的"层"在加密。
// 数越大、纹越密，到 128 层已经看不出是一层层了——镜头只好推上去，
// 推到最后那一片密纹就是纸的横纹本身。

type Props = {
  /** 这一镜折到第几次（层数 = 2ⁿ） */
  to?: number;
  /** 从第几次接着数（上一镜已经数到哪）：跨镜续上，不要归零重来 */
  from?: number;
  /** 最后推近，让密纹化成纸纹 */
  zoom?: boolean;
  kicker?: string;
  note?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const STRIP = { x: 1300, y: 110, w: 200, h: 762 };
// 中间那条“翻倍阶梯”：1→2→4→…→128，折到哪一级就点亮哪一级，
// 把左边的大数和右边的层带连起来（不然 16:9 中间一大片空）。
const LADDER_X = 780;
const LADDER_Y = 300;
const LADDER_GAP = 54;

export const FoldCount: React.FC<Props> = ({
  to = 7,
  from = 0,
  zoom = false,
  kicker = "章一 · 手",
  note = "层数 = 2ⁿ",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();

  // 折的动作：留 0.35s 起手，最后一折提前 0.5s 收住
  const t0 = fps * 0.35;
  const span = durationInFrames - t0 - fps * 0.5;
  const n = Math.max(1, to - from);              // 这一镜要折几次
  const step = span / n;
  const raw = Math.max(0, (frame - t0) / step);
  const done = Math.min(n, Math.floor(raw));
  const p = raw >= n ? 0 : raw - done;           // 当前这一折的进度
  const folds = from + done;                    // 全片第几次，接着上一镜数
  // 读数只报 2 的幂（层数没有 19 这一档）；密纹密度继续连续，那是"正在长"的视觉。
  const layers = Math.pow(2, folds);
  const layersF = layers * (1 + p);

  const inP = ease((frame - 2) / (fps * 0.45));
  // 推镜给足 1.4s：0.9s 里放 7 倍，30fps 下每帧换一张图（006 实测帧间差到 44）
  const zoomP = zoom ? ease((frame - (durationInFrames - fps * 1.4)) / (fps * 1.4)) : 0;

  const lines = Math.min(256, Math.max(1, Math.round(layersF)));
  const period = STRIP.h / lines;

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
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 118,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 8,
            color: C.cyan,
            opacity: inP * (1 - zoomP),
          }}
        >
          {kicker}
        </div>

        {/* 左：层数 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 300,
            opacity: inP * (1 - zoomP * 0.9),
            transform: `translateX(${-zoomP * 60}px)`,
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: 26,
              letterSpacing: 10,
              color: C.dim,
            }}
          >
            要弯的层数
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 6 }}>
            <div
              style={{
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: 210,
                lineHeight: 1,
                color: C.gold,
                fontVariantNumeric: "tabular-nums",
                textShadow: "0 0 70px rgba(243,193,75,0.3)",
              }}
            >
              {layers.toLocaleString("en-US")}
            </div>
            <div style={{ fontFamily: FONT, fontSize: 46, color: C.ink, letterSpacing: 2 }}>层</div>
          </div>
          <div
            style={{
              marginTop: 18,
              fontFamily: FONT,
              fontSize: 28,
              letterSpacing: 3,
              color: "rgba(139,147,167,0.9)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            第 {Math.max(1, folds + (p > 0 ? 1 : 0))} 次对折
          </div>
          <div
            style={{
              marginTop: 44,
              width: 520,
              fontFamily: FONT,
              fontSize: 21,
              lineHeight: 1.8,
              letterSpacing: 1,
              color: "rgba(139,147,167,0.7)",
            }}
          >
            {note}
          </div>
        </div>

        {/* 中：翻倍阶梯 */}
        <div
          style={{
            position: "absolute",
            left: LADDER_X,
            top: LADDER_Y,
            opacity: inP * (1 - zoomP),
          }}
        >
          {Array.from({ length: 8 }, (_, i) => {
            const v = Math.pow(2, i);
            const lit = i <= folds;
            const active = i === Math.min(7, folds);
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                  height: LADDER_GAP,
                  opacity: lit ? 1 : 0.22,
                }}
              >
                <div
                  style={{
                    width: active ? 26 : 12,
                    height: 2,
                    background: active ? C.gold : "rgba(255,255,255,0.4)",
                    boxShadow: active ? "0 0 14px rgba(243,193,75,0.9)" : undefined,
                  }}
                />
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: 34,
                    letterSpacing: 2,
                    color: active ? C.gold : lit ? "rgba(246,242,231,0.72)" : C.dim,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {v.toLocaleString("en-US")}
                </div>
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: 18,
                    letterSpacing: 2,
                    color: "rgba(139,147,167,0.55)",
                  }}
                >
                  层
                </div>
              </div>
            );
          })}
        </div>
        
        {/* 右：竖着的"层" */}
        <div
          style={{
            position: "absolute",
            left: STRIP.x,
            top: STRIP.y,
            width: STRIP.w,
            height: STRIP.h,
            transformOrigin: "50% 50%",
            transform: `scale(${1 + zoomP * 5})`,
            opacity: inP,
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              border: "1px solid rgba(248,242,228,0.18)",
              background: "rgba(248,242,228,0.02)",
            }}
          />
          {/* 每一层一条线：条数跟着层数涨 */}
          <div
            style={{
              position: "absolute",
              inset: 1,
              background: `repeating-linear-gradient(180deg, rgba(255,250,236,0.95) 0px, rgba(255,250,236,0.95) ${Math.max(
                1,
                period * 0.55,
              )}px, rgba(160,141,106,0.55) ${Math.max(1, period * 0.55)}px, rgba(160,141,106,0.55) ${Math.max(
                2,
                period,
              )}px)`,
              opacity: 0.92,
            }}
          />
          {/* 顶上一道亮边：最上面那一张 */}
          <div
            style={{
              position: "absolute",
              left: -1,
              right: -1,
              top: -1,
              height: 2,
              background: "#fff6df",
              boxShadow: "0 0 26px rgba(255,226,150,0.9)",
            }}
          />
        </div>

        <div
          style={{
            position: "absolute",
            left: STRIP.x,
            top: STRIP.y + STRIP.h + 18,
            width: STRIP.w,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 20,
            letterSpacing: 2,
            color: "rgba(139,147,167,0.7)",
            opacity: inP * (1 - zoomP),
            fontVariantNumeric: "tabular-nums",
          }}
        >
          ×2 每一折
        </div>
      </div>
    </AbsoluteFill>
  );
};
