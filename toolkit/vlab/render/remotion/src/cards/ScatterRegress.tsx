import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { mulberry32, clamp } from "../common/random";

// 散点 + 回归线：全片那条"尺子"就长在这张卡里。
// 横轴 = 父母偏离均值多少，纵轴 = 子女偏离均值多少。斜率 2/3 是高尔顿量出来的：
// 偏离的那部分，只回来三分之二。928 个点不是装饰，是那 928 个成年子女。
//
// 中间那条永远在的灰线是"均值"——它在章三会横过来变成人生线，在落点变成海平面。

export type ScatterMode =
  | "intro"
  | "points"
  | "drift"
  | "tall"
  | "short"
  | "coef"
  | "line"
  | "push"
  | "one";

type Props = {
  mode?: ScatterMode;
  /** 样本量（默认 928 = 高尔顿量过的成年子女数） */
  n?: number;
  /** 回归系数：偏离的部分回来多少 */
  slope?: number;
  kicker?: string;
  note?: string;
  label?: string;
  seed?: number;
  /** one 模式从线下滑上来（低的那次回升）；默认从线上滑下来 */
  flip?: boolean;
};

const CX = 960;
const CY = 566;
const HW = 620; // 横轴半宽（px）
const HH = 300; // 纵轴半高（px）
const SPAN = 2.6; // 轴覆盖范围（σ）
const N_TOTAL = 928;

const px = (x: number) => CX + (x / SPAN) * HW;
const py = (y: number) => CY - (y / SPAN) * HH;

const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

export const ScatterRegress: React.FC<Props> = ({
  mode = "points",
  n = N_TOTAL,
  slope = 2 / 3,
  kicker = "03 · 线　THE LINE",
  note = "F. Galton, 1886：《Regression towards mediocrity in hereditary stature》",
  label = "",
  seed = 19,
  flip = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();
  const dur = durationInFrames;

  // 928 个点：y = slope·x + 噪声（父母越极端，子女仍更极端一点，但只回来三分之二）
  const pts = React.useMemo(() => {
    const rnd = mulberry32(seed * 7717 + 5);
    const g = () => (rnd() + rnd() + rnd() + rnd() - 2) * 1.15;
    return Array.from({ length: n }, () => {
      const x = g();
      return { x, y: slope * x + g() * 0.62 };
    });
  }, [n, slope, seed]);

  const showP = React.useMemo(() => {
    if (mode === "intro") return ease(clamp((frame - fps * 0.15) / (fps * 0.7)));
    if (mode === "points") return ease(clamp((frame - fps * 0.1) / (fps * (dur / fps - 0.3))));
    return 1;
  }, [frame, fps, dur, mode]);

  const shown = Math.round(n * showP);

  // drift / push：镜头在动（007 要的真运镜）
  const pan = mode === "drift" ? clamp((frame - fps * 0.1) / (fps * 1.4)) : 0;
  const zoom = mode === "push" ? 1 + 0.26 * clamp((frame - fps * 0.1) / (fps * 1.6)) : 1;

  // 高个父母 / 矮个父母：只看一个象限，箭头指回来
  const quadP =
    mode === "tall" || mode === "short"
      ? ease(clamp((frame - fps * 0.25) / (fps * 0.8)))
      : 0;
  const qx = mode === "tall" ? 1.9 : -1.9;

  // coef：把一段偏离切成"回来的 2/3"和"没回来的 1/3"
  const coefP = mode === "coef" ? ease(clamp((frame - fps * 0.2) / (fps * 0.9))) : 0;

  // line：金线长出来
  const lineP = mode === "line" ? clamp((frame - fps * 0.2) / (fps * 1.1)) : 0;
  const lineOn = mode === "line" || mode === "push" || mode === "one" || mode === "coef" ? 1 : 0;

  // one：被点中的那个孩子，滑回自己的线
  const oneP = mode === "one" ? clamp((frame - fps * 0.3) / (fps * 1.3)) : 0;
  const onePt = React.useMemo(() => {
    const rnd = mulberry32(seed * 9176 + 11);
    const g = () => (rnd() + rnd() + rnd() + rnd() - 2) * 1.15;
    const x = flip ? -2.05 : 2.05;
    const off = flip ? -(0.55 + Math.abs(g()) * 0.62) : 0.55 + Math.abs(g()) * 0.62;
    return { x, y: slope * x + off };
  }, [slope, seed, flip]);
  const oneY = onePt.y + (slope * onePt.x - onePt.y) * oneP;

  const axisP = ease(clamp((frame - fps * 0.1) / (fps * 0.6)));
  const tag = (x: number, y: number) => ({ left: px(x), top: py(y) });

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
        {/* 单点光：只照散点云 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(700px 520px at 50% 52%, rgba(255,232,180,0.10) 0%, rgba(255,232,180,0.03) 45%, rgba(0,0,0,0) 74%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(1100px 800px at 50% 50%, rgba(0,0,0,0) 42%, rgba(0,0,0,0.60) 100%)",
          }}
        />

        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 1920,
            height: 1080,
            transform: `translateX(${-46 * pan}px) scale(${zoom})`,
            transformOrigin: `${CX + 60}px ${CY}px`,
          }}
        >
          {/* 轴 */}
          <div
            style={{
              position: "absolute",
              left: px(-SPAN) - 40,
              top: CY,
              width: HW * 2 + 80,
              height: 1,
              background:
                "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.22) 50%, rgba(255,255,255,0) 100%)",
              opacity: axisP,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: CX,
              top: py(SPAN) - 30,
              width: 1,
              height: HH * 2 + 60,
              background:
                "linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0) 100%)",
              opacity: axisP,
            }}
          />

          {/* 928 个孩子 */}
          {pts.slice(0, shown).map((p, i) => {
            const inQuad =
              (mode === "tall" && p.x > 0.9) || (mode === "short" && p.x < -0.9);
            const dim = (mode === "tall" || mode === "short") && !inQuad;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: px(p.x) - 2.6,
                  top: py(p.y) - 2.6,
                  width: 5.2,
                  height: 5.2,
                  borderRadius: 3,
                  background: inQuad ? C.gold : "rgba(226,236,248,0.85)",
                  opacity: dim ? 0.16 : 0.8,
                }}
              />
            );
          })}

          {/* 回归线：斜率 2/3 */}
          {lineOn ? (
            <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
              <line
                x1={px(-SPAN)}
                y1={py(slope * -SPAN)}
                x2={px(-SPAN) + (HW * 2 * lineP)}
                y2={py(slope * (-SPAN + (2 * SPAN * lineP)))}
                stroke={C.gold}
                strokeWidth={2.6}
                opacity={0.92}
              />
              {/* 完全遗传会走的线：做对照，观众才看得出"少了三分之一" */}
              {coefP > 0 || mode === "line" ? (
                <line
                  x1={px(-SPAN)}
                  y1={py(-SPAN)}
                  x2={px(SPAN)}
                  y2={py(SPAN)}
                  stroke="rgba(255,91,91,0.55)"
                  strokeWidth={1.6}
                  strokeDasharray="7 7"
                />
              ) : null}
            </svg>
          ) : null}

          {/* 高个 / 矮个父母的箭头：从"如果完全遗传"掉回"实际" */}
          {quadP > 0 ? (
            <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
              <line
                x1={px(qx)}
                y1={py(qx)}
                x2={px(qx)}
                y2={py(slope * qx)}
                stroke={C.gold}
                strokeWidth={3}
                opacity={quadP}
              />
              <circle cx={px(qx)} cy={py(qx)} r={6} fill="none" stroke="rgba(255,91,91,0.8)" strokeWidth={2} opacity={quadP} />
              <circle cx={px(qx)} cy={py(slope * qx)} r={7} fill={C.gold} opacity={quadP} />
            </svg>
          ) : null}
          {quadP > 0 ? (
            <>
              <div
                style={{
                  position: "absolute",
                  left: px(qx) + 18,
                  top: py(qx) - 16,
                  fontFamily: FONT,
                  fontSize: 26,
                  color: "rgba(255,91,91,0.9)",
                  opacity: quadP,
                }}
              >
                如果完全遗传
              </div>
              <div
                style={{
                  position: "absolute",
                  left: px(qx) + 18,
                  top: py(slope * qx) - 16,
                  fontFamily: FONT,
                  fontSize: 26,
                  color: C.gold,
                  opacity: quadP,
                }}
              >
                实际
              </div>
            </>
          ) : null}

          {/* coef：把偏离切成 2/3 和 1/3 */}
          {coefP > 0 ? (
            <>
              <div
                style={{
                  position: "absolute",
                  left: px(1.85) + 14,
                  top: py(slope * 1.85),
                  width: 4,
                  height: Math.abs(py(slope * 1.85) - py(0)) - Math.abs(py(slope * 1.85) - py(slope * 1.85)),
                  background: C.gold,
                  opacity: coefP,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: px(1.85) + 26,
                  top: py(slope * 1.85) - 14,
                  fontFamily: FONT,
                  fontSize: 30,
                  color: C.gold,
                  opacity: coefP,
                }}
              >
                2 / 3
              </div>
            </>
          ) : null}

          {/* one：一个孩子滑回自己的线 */}
          {mode === "one" ? (
            <>
              <div
                style={{
                  position: "absolute",
                  left: px(onePt.x) - 13,
                  top: py(oneY) - 13,
                  width: 26,
                  height: 26,
                  borderRadius: 13,
                  border: `2px solid ${C.red}`,
                  opacity: 0.95,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: px(onePt.x) - 22,
                  top: py(onePt.y) - 22,
                  width: 44,
                  height: 44,
                  borderRadius: 22,
                  border: `1px solid ${C.red}`,
                  opacity: 0.35 * (1 - oneP),
                }}
              />
            </>
          ) : null}
        </div>

        {/* 中位灰线：全片那条"尺子"，永远在 */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: CY,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(73,227,209,0) 0%, rgba(73,227,209,0.42) 50%, rgba(73,227,209,0) 100%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 132,
            top: CY - 34,
            fontFamily: FONT,
            fontSize: 20,
            letterSpacing: 4,
            color: C.cyan,
            opacity: 0.75,
          }}
        >
          均值
        </div>

        {/* 左上章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(axisP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>
            {kicker}
          </div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 右上：样本量 */}
        <div style={{ position: "absolute", right: 130, top: 118, textAlign: "right", fontFamily: FONT }}>
          <div style={{ fontSize: 21, letterSpacing: 6, color: C.dim }}>成年子女</div>
          <div
            style={{
              fontSize: 62,
              fontWeight: 700,
              color: C.gold,
              fontVariantNumeric: "tabular-nums",
              lineHeight: 1.1,
            }}
          >
            {Math.round(n * showP)}
          </div>
          <div style={{ fontSize: 20, letterSpacing: 4, color: "rgba(139,147,167,0.9)" }}>个 / 928</div>
        </div>

        {/* 屏上的字 */}
        {label ? (
          <div
            style={{
              position: "absolute",
              left: 148,
              top: 760,
              width: 560,
              fontFamily: FONT,
              fontSize: 44,
              fontWeight: 700,
              lineHeight: 1.45,
              letterSpacing: 3,
              color: C.ink,
              opacity: clamp((frame - fps * 0.4) / (fps * 0.5)),
              textShadow: "0 0 40px rgba(0,0,0,0.6)",
            }}
          >
            {label}
          </div>
        ) : null}

        <div
          style={{
            position: "absolute",
            right: 130,
            bottom: 96,
            width: 560,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 19,
            lineHeight: 1.8,
            letterSpacing: 1,
            color: "rgba(139,147,167,0.66)",
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
