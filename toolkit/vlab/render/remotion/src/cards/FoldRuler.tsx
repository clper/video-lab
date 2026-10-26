import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 一把尺：纵轴是"折了几次"，每一格 = 厚度再翻一倍，所以刻度是等距的（这本身就是对数尺）。
// 全片只有这一把尺：章二立起来、章三横过来量纸长、章四退成底线、结尾缩回消失。
// 右侧挂真实的东西（手掌 / 楼 / 塔 / 卡门线 / 地球 / 月球），观众才有得比。

export type LandmarkKind = "hand" | "building" | "tower" | "dash" | "earth" | "moon";

export type Landmark = {
  fold: number;
  label: string;
  sub?: string;
  kind: LandmarkKind;
};

type Props = {
  total?: number;
  /** 现在长到第几折 */
  fold?: number;
  landmarks?: Landmark[];
  kicker?: string;
  /** 尺脚下面那行小字（单位说明 / 出处） */
  note?: string;
  /** 高空过场：云、客机、天由蓝转黑 */
  sky?: boolean;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const BASE_Y = 812;
const TOP_Y = 176;
const SPAN = BASE_Y - TOP_Y;
const RULER_X = 1180;
// 刻度朝左长、数字在最左一列，右边整片留给地标；左边一大块留给读数——
// 16:9 的左边三分之二不能空着。
// LABEL_X 是数字框的左边，框的右边缘落在 RULER_X-136 上，离长刻度还差 16px。
const LABEL_W = 96;
const LABEL_X = RULER_X - 136 - LABEL_W;

const Silhouette: React.FC<{ kind: LandmarkKind; color: string }> = ({ kind, color }) => {
  const common = { fill: color, opacity: 0.9 } as const;
  if (kind === "hand") {
    return (
      <svg width="76" height="84" viewBox="0 0 76 84">
        <g {...common}>
          <rect x="26" y="30" width="10" height="34" rx="5" />
          <rect x="38" y="20" width="10" height="44" rx="5" />
          <rect x="50" y="26" width="10" height="38" rx="5" />
          <rect x="16" y="38" width="10" height="26" rx="5" />
          <path d="M14 56c0-6 4-10 10-10h30c6 0 10 4 10 10v6c0 10-8 18-18 18H32c-10 0-18-8-18-18z" />
          <path d="M14 58c-6 2-8 8-4 12 3 4 8 3 10-1z" />
        </g>
      </svg>
    );
  }
  if (kind === "building") {
    return (
      <svg width="76" height="84" viewBox="0 0 76 84">
        <g {...common}>
          <rect x="18" y="6" width="40" height="74" rx="2" />
        </g>
        <g fill="#06070d" opacity="0.75">
          {[0, 1, 2, 3].map((r) =>
            [0, 1].map((c) => (
              <rect key={`${r}-${c}`} x={25 + c * 16} y={14 + r * 17} width="10" height="10" rx="1" />
            )),
          )}
        </g>
      </svg>
    );
  }
  if (kind === "tower") {
    return (
      <svg width="76" height="84" viewBox="0 0 76 84">
        <g {...common}>
          <path d="M30 80 34 22h8l4 58z" />
          <path d="M37 22V6h2v16z" />
          <path d="M26 80h24v4H26z" />
        </g>
      </svg>
    );
  }
  if (kind === "earth") {
    return (
      <svg width="76" height="84" viewBox="0 0 76 84">
        <circle cx="38" cy="42" r="34" fill={color} opacity="0.18" />
        <circle cx="38" cy="42" r="30" fill="none" stroke={color} strokeWidth="1.6" opacity="0.85" />
        <path d="M14 34c8 3 12 10 20 9s11-9 20-7" fill="none" stroke={color} strokeWidth="1" opacity="0.5" />
        <path d="M18 54c9-4 15 3 24 0s12-7 16-5" fill="none" stroke={color} strokeWidth="1" opacity="0.35" />
      </svg>
    );
  }
  if (kind === "moon") {
    return (
      <svg width="76" height="84" viewBox="0 0 76 84">
        <circle cx="38" cy="42" r="26" fill={color} opacity="0.9" />
        <circle cx="30" cy="34" r="5" fill="#06070d" opacity="0.22" />
        <circle cx="45" cy="47" r="7" fill="#06070d" opacity="0.18" />
        <circle cx="33" cy="52" r="3.5" fill="#06070d" opacity="0.2" />
      </svg>
    );
  }
  // dash：卡门线
  return (
    <svg width="76" height="84" viewBox="0 0 76 84">
      <path d="M0 42h76" stroke={color} strokeWidth="1.6" strokeDasharray="6 6" opacity="0.9" />
      <path d="M0 42h76" stroke={color} strokeWidth="8" opacity="0.08" />
    </svg>
  );
};

export const FoldRuler: React.FC<Props> = ({
  total = 42,
  fold = 3,
  landmarks = [],
  kicker = "02 · 尺　THE RULER",
  note = "每一格 = 厚度翻一倍。格子等距，因为纵轴取了对数。",
  sky = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  // 尺先立起来，纸柱再长上来
  const drawP = ease((frame - Math.round(fps * 0.15)) / (fps * 0.75));
  const colP = ease((frame - Math.round(fps * 0.55)) / (fps * 0.6));
  const colH = (SPAN * clamp(fold / total)) * colP;
  const yOf = (f: number) => BASE_Y - (SPAN * f) / total;

  // 左边读数：折数 / 长度 / 层数
  const mmOf = 0.1 * Math.pow(2, fold);
  const fmtLen = (mm: number) => {
    if (mm < 10) return `${mm.toFixed(1)} 毫米`;
    if (mm < 1000) return `${Math.round(mm)} 毫米`;
    if (mm < 1e6) return `${Math.round(mm / 1000)} 米`;
    const km = mm / 1e6;
    return `${(km < 100 ? km.toFixed(1) : Math.round(km).toLocaleString("en-US"))} 公里`;
  };
  const layerText = fold <= 17 ? `${Math.round(Math.pow(2, fold)).toLocaleString("en-US")} 层` : null;

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
        {/* 高空过场：天由蓝转黑，云往下走（是镜头在上升） */}
        {sky ? (
          <>
            <div
              style={{
                position: "absolute",
                inset: 0,
                background:
                  "linear-gradient(180deg, rgba(8,12,24,0) 20%, rgba(24,68,116,0.26) 60%, rgba(56,116,176,0.40) 100%)",
                opacity: clamp(drawP * 1.2),
              }}
            />
            {[
              { y: 690, w: 1160, h: 150, o: 0.16, d: 150 },
              { y: 596, w: 900, h: 120, o: 0.13, d: 210 },
              { y: 512, w: 700, h: 96, o: 0.10, d: 260 },
            ].map((c, i) => (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: 960 - c.w / 2,
                  top: c.y + c.d * clamp((frame - fps * 0.3) / (fps * 3.2)),
                  width: c.w,
                  height: c.h,
                  background: `radial-gradient(ellipse at 50% 50%, rgba(190,214,238,${c.o}) 0%, rgba(190,214,238,0) 68%)`,
                  opacity: clamp(drawP * 1.5) * clamp(1 - (frame - fps * 2.6) / (fps * 1.2)),
                }}
              />
            ))}
            {/* 一架客机，正好飞在纸柱旁边 */}
            <div
              style={{
                position: "absolute",
                left: 1470,
                top: 560 + 180 * clamp((frame - fps * 0.3) / (fps * 3.2)),
                width: 92,
                height: 18,
                opacity: 0.5 * clamp(drawP * 1.5) * clamp(1 - (frame - fps * 2.4) / (fps * 1.2)),
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 8,
                  width: 92,
                  height: 2,
                  background: "rgba(226,236,248,0.9)",
                  borderRadius: 2,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 34,
                  top: 2,
                  width: 26,
                  height: 2,
                  background: "rgba(226,236,248,0.66)",
                  transform: "rotate(-22deg)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 34,
                  top: 14,
                  width: 26,
                  height: 2,
                  background: "rgba(226,236,248,0.66)",
                  transform: "rotate(22deg)",
                }}
              />
            </div>
          </>
        ) : null}

        {/* 尺杆 */}
        <div
          style={{
            position: "absolute",
            left: RULER_X - 1,
            top: BASE_Y - SPAN * drawP,
            width: 2,
            height: SPAN * drawP,
            background: "linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.52))",
          }}
        />

        {/* 尺脚：让它真的站在一张桌子上，不是浮在空里 */}
        <div
          style={{
            position: "absolute",
            left: RULER_X - 220,
            top: BASE_Y,
            width: 460,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.16) 50%, rgba(255,255,255,0) 100%)",
            opacity: drawP,
          }}
        />

        {/* 刻度：每 5 折一条长的 */}
        {Array.from({ length: total + 1 }, (_, i) => {
          const shown = i / total <= drawP;
          if (!shown) return null;
          const major = i % 5 === 0;
          const len = major ? 120 : 62;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: RULER_X - len,
                top: yOf(i),
                width: len,
                height: 1,
                background: major ? "rgba(255,255,255,0.46)" : "rgba(255,255,255,0.18)",
              }}
            />
          );
        })}

        {/* 刻度数：0 / 10 / 20 / 30 / 42 */}
        {[0, 10, 20, 30, 42].map((f) =>
          f / total <= drawP ? (
            <div
              key={f}
              style={{
                position: "absolute",
                left: LABEL_X,
                top: yOf(f) - 19,
                width: LABEL_W,
                textAlign: "right",
                fontFamily: FONT,
                fontSize: 32,
                letterSpacing: 2,
                color: f === total ? C.gold : "rgba(139,147,167,0.8)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {f}
            </div>
          ) : null,
        )}

        {/* 纸柱：从尺脚长上来，柱身还是纸的横纹（它一直是一叠纸） */}
        {colH > 0.5 ? (
          <div
            style={{
              position: "absolute",
              left: RULER_X - 38,
              top: BASE_Y - colH,
              width: 76,
              height: colH,
              background:
                "repeating-linear-gradient(180deg, #f8f2e4 0px, #f8f2e4 1.2px, #ded2b8 1.2px, #ded2b8 2.4px)",
              boxShadow:
                "inset 0 0 0 1px rgba(255,246,220,0.35), 0 0 42px rgba(243,193,75,0.20)",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: -2,
                right: -2,
                top: -2,
                height: 3,
                background: "#fff3d0",
                boxShadow: "0 0 22px rgba(255,226,150,0.95)",
              }}
            />
          </div>
        ) : null}

        {/* 地标：按折数排好，标签互相推开 118px（不然 10 折和 17 折会叠在一起）。
            外圈 / 内圈那种贴太近的地方，标签往下错，再用一小段斜线牵回来。 */}
        {landmarks
          .slice()
          .sort((a, b) => a.fold - b.fold)
          .map((m, i, arr) => {
          const y = yOf(m.fold);
          // 42 折的地标就在尺顶，判据要往上抬一点，否则最后一条永远不出现
          const appear = clamp((drawP * total - m.fold + 1.6) / 3);
          if (appear <= 0) return null;
          // 标签避让：折数越大的地标在屏幕上越高，所以后一个往“上”推，
          // 不能往下推 —— 往下推就压到矮的那个身上（10 折和 17 折就这么撞过）。
          let ly = y - 34;
          for (let k = 0; k < i; k += 1) {
            const py = yOf(arr[k].fold) - 34;
            if (py - ly < 118) ly = py - 118;
          }
          const nudge = ly - (y - 34);
          return (
            <React.Fragment key={`${m.kind}-${m.fold}`}>
              <div
                style={{
                  position: "absolute",
                  left: RULER_X + 70,
                  top: y,
                  width: 280,
                  height: 1,
                  background: "linear-gradient(90deg, rgba(255,255,255,0.30), rgba(255,255,255,0))",
                  opacity: appear,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: RULER_X + 96,
                  top: y - 42,
                  opacity: appear,
                  transform: `translateX(${(1 - appear) * 14}px)`,
                }}
              >
                <Silhouette kind={m.kind} color={C.ink} />
              </div>
              {/* 被推下去的标签，用一小段斜线牵回自己的高度 */}
              {nudge > 2 ? (
                <div
                  style={{
                    position: "absolute",
                    left: RULER_X + 78,
                    top: y - 40,
                    width: 22,
                    height: Math.abs(nudge) + 40,
                    opacity: appear * 0.5,
                    borderLeft: "1px solid rgba(255,255,255,0.28)",
                    transform: `skewX(${nudge > 0 ? -26 : 26}deg)`,
                    transformOrigin: "top left",
                  }}
                />
              ) : null}
              <div
                style={{
                  position: "absolute",
                  left: RULER_X + 186,
                  top: ly,
                  opacity: appear,
                  transform: `translateX(${(1 - appear) * 14}px)`,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT,
                    fontSize: 30,
                    color: C.gold,
                    fontVariantNumeric: "tabular-nums",
                    letterSpacing: 1,
                  }}
                >
                  {m.label}
                </div>
                {m.sub ? (
                  <div
                    style={{
                      marginTop: 6,
                      fontFamily: FONT,
                      fontSize: 22,
                      color: "rgba(139,147,167,0.9)",
                      letterSpacing: 2,
                    }}
                  >
                    {m.sub}
                  </div>
                ) : null}
              </div>
            </React.Fragment>
          );
        })}

        {/* 左上章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(drawP * 2),
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: 22,
              letterSpacing: 7,
              color: C.cyan,
            }}
          >
            {kicker}
          </div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 左边读数：折数 / 长度 / 层数。尺子一个人站不住，得有东西秤着它 */}
        <div
          style={{
            position: "absolute",
            left: 140,
            top: 286,
            width: 700,
            opacity: clamp(drawP * 1.4),
          }}
        >
          <div
            style={{
              fontFamily: FONT,
              fontSize: 24,
              letterSpacing: 8,
              color: C.dim,
            }}
          >
            已折
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginTop: 4 }}>
            <div
              style={{
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: 138,
                lineHeight: 1.02,
                color: C.gold,
                fontVariantNumeric: "tabular-nums",
                textShadow: "0 0 60px rgba(243,193,75,0.28)",
              }}
            >
              {fold}
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 46,
                letterSpacing: 2,
                color: "rgba(139,147,167,0.85)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              / {total}
            </div>
          </div>
          <div style={{ marginTop: 20, height: 1, width: 400, background: "rgba(255,255,255,0.12)" }} />
          <div
            style={{
              marginTop: 20,
              fontFamily: FONT,
              fontSize: 34,
              letterSpacing: 2,
              color: C.ink,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {fmtLen(mmOf)}
            {layerText ? (
              <span style={{ fontSize: 26, color: "rgba(139,147,167,0.85)", letterSpacing: 2 }}>
                　·　{layerText}
              </span>
            ) : null}
          </div>
          <div
            style={{
              marginTop: 40,
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

        {/* 纵轴名 */}
        <div
          style={{
            position: "absolute",
            left: LABEL_X,
            top: TOP_Y - 52,
            width: LABEL_W,
            textAlign: "right",
            fontFamily: FONT,
            fontSize: 22,
            letterSpacing: 6,
            color: "rgba(139,147,167,0.6)",
            opacity: clamp(drawP * 2),
          }}
        >
          折数
        </div>
      </div>
    </AbsoluteFill>
  );
};
