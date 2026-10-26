import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 对折：一张纸 → 一叠纸。
// 不做几何真实的"长度减半"（第 7 次只剩几像素，看不见），只认真画厚度的翻倍：
// 每折一次，纸叠的层数 ×2，叠高高一点。片子的论点就是厚度，所以这里只演厚度。
// 折到第 8 次时纸叠会自己弹开——那一层不是"再加一层纸"，是"折不动了"。

type Props = {
  /** 这一镜里折几次 */
  folds?: number;
  /** 折完之后再试一次，折不动、弹开 */
  fail?: boolean;
  /** 左上角小字 */
  kicker?: string;
  /** 左下角公式小字 */
  note?: string;
  /** 是否显示右侧读数 */
  readout?: boolean;
  /** 镜头推近（1 = 不动） */
  zoom?: number;
  seed?: number;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

export const FoldSheet: React.FC<Props> = ({
  folds: foldsProp = 7,
  fail = true,
  kicker = "一张纸",
  note = "厚度 = 0.1 mm × 2ⁿ",
  readout = true,
  zoom = 1,
}) => {
  const frame = useCurrentFrame();
  const { s } = useStage();
  const { fps, durationInFrames } = useVideoConfig();

  const folds = Math.max(0, foldsProp);            // 0 = 只是摆着，不折
  const startF = Math.round(fps * 0.3);
  const failFrames = fail && folds > 0 ? Math.round(fps * 0.95) : 0;
  const span = Math.max(8, durationInFrames - startF - failFrames);
  const stepF = Math.max(1, span / Math.max(1, folds));
  const raw = folds > 0 ? Math.max(0, (frame - startF) / stepF) : 0;
  const idx = Math.min(folds, Math.floor(raw));       // 已经折完几次
  const p = folds === 0 || raw >= folds ? 0 : raw - idx;   // 当前这一折的进度
  // 数字只报真值：对折不出一层半，"19 层"这种状态根本不存在（006 在 8.4s 抓到过）。
  // 厚度条继续按 (1+p) 长——那是"正在折"的视觉；读数只在折完时跳到 2 的幂。
  const layers = Math.pow(2, idx) * (1 + p);           // 视觉：折的过程中在涨
  const layersDone = Math.pow(2, idx);                 // 读数：只有折完才是真值
  const mm = 0.1 * layersDone;

  // 折不动：压下去、别一下、弹回来
  const fStart = startF + folds * stepF;
  const fp = fail && folds > 0 ? clamp((frame - fStart) / Math.max(1, failFrames)) : 0;
  const press = Math.sin(fp * Math.PI) * (1 - fp * 0.72);
  const shake = Math.sin(fp * Math.PI * 7) * Math.exp(-fp * 4) * (fp > 0 ? 1 : 0);

  const baseY = 720;
  const stackW = 900;
  const cx = 620;
  // 真实的第 7 折只剩几毫米宽，看不见；这里只按 0.94 收一点点，让"越来越小"看得出来，
  // 厚度才是要量的东西。所以画面右下角挂一个"示意"。
  const wNow = stackW * Math.pow(0.94, idx + p);
  // 3.4 px = 一层，正好是纸白的条纹周期：折几次就能数出几条线
  const h = layers * 3.4;
  const faceY = baseY - h - 14;      // 最上面那张纸的顶边
  const mx = cx - wNow / 2 - 44;     // 量线贴着当前的左边缘
  const tilt = -5 - idx * 0.2;

  const rise = ease((frame - 2) / (fps * 0.5));   // 开场纸自己立起来一点

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: 1920,
          height: 1080,
          transform: `translate(-50%, -50%) scale(${s * zoom})`,
          transformOrigin: "50% 60%",
        }}
      >
        {/* 桌面上的一小片暖光：不然纸像是浮在真空里 */}
        <div
          style={{
            position: "absolute",
            left: cx - 760,
            top: baseY - 150,
            width: 1520,
            height: 300,
            background:
              "radial-gradient(ellipse at 50% 50%, rgba(255,224,160,0.055) 0%, rgba(255,224,160,0) 68%)",
            opacity: rise,
          }}
        />

        {/* 桌面：一道极淡的光带 + 影子 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            right: 120,
            top: baseY,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.10) 22%, rgba(255,255,255,0.16) 50%, rgba(255,255,255,0.10) 78%, rgba(255,255,255,0) 100%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: cx - stackW * 0.62,
            top: baseY - 8,
            width: stackW * 1.24,
            height: 64,
            background:
              "radial-gradient(ellipse at 50% 0%, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0) 70%)",
            opacity: 0.9,
          }}
        />

        {/* 纸叠 */}
        <div
          style={{
            position: "absolute",
            left: cx - wNow / 2,
            top: baseY - h,
            width: wNow,
            height: h,
            transform: `skewX(${tilt}deg) translate(${shake * 3}px, ${press * 10}px) rotate(${press * 0.8}deg)`,
            transformOrigin: "50% 100%",
            background:
              "repeating-linear-gradient(180deg, #f8f2e4 0px, #f8f2e4 2.4px, #d5c9ad 2.4px, #d5c9ad 3.4px)",
            boxShadow:
              "inset 0 0 0 1px rgba(255,246,220,0.55), inset -18px 0 30px rgba(0,0,0,0.28), 0 0 60px rgba(243,193,75,0.06)",
            opacity: 0.35 + 0.65 * rise,
            filter: press > 0.05 ? `brightness(${1 + press * 0.25})` : undefined,
          }}
        >
          {/* 纸的纤维与切边 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "repeating-linear-gradient(90deg, rgba(120,96,60,0.05) 0px, rgba(120,96,60,0.05) 2px, rgba(0,0,0,0) 2px, rgba(0,0,0,0) 9px)",
            }}
          />
          {/* 最上面一张的亮边：所有注意力都在这条线上 */}
          <div
            style={{
              position: "absolute",
              left: -1,
              right: -1,
              top: -2,
              height: 2,
              background: "linear-gradient(90deg, rgba(255,229,160,0.35), #ffe9b8 45%, #fff6df 55%, rgba(255,229,160,0.35))",
              boxShadow: "0 0 18px rgba(255,226,150,0.55)",
            }}
          />
        </div>

        {/* 最上面的一张：侧着看是一片有厚度的纸（只靠一层 0.1 毫米的线看不出是纸） */}
        <div
          style={{
            position: "absolute",
            left: cx - wNow / 2 - 7,
            top: faceY,
            width: wNow + 14,
            height: 14,
            transform: `skewX(${tilt}deg)`,
            background: "linear-gradient(180deg, #fffbef 0%, #f6eeda 55%, #e2d6bb 100%)",
            borderTop: "1px solid #fffdf7",
            boxShadow: "0 6px 26px rgba(255,232,180,0.22), 0 0 40px rgba(243,193,75,0.10)",
            opacity: 0.35 + 0.65 * rise,
          }}
        />

        {/* 一折落地：顶面亮一下，像刚压实了一道。比“一张纸从天上掉下来”干净得多 */}
        <div
          style={{
            position: "absolute",
            left: cx - wNow / 2,
            top: faceY - 2,
            width: wNow,
            height: 2,
            background:
              "linear-gradient(90deg, rgba(255,246,223,0) 0%, rgba(255,250,235,0.95) 50%, rgba(255,246,223,0) 100%)",
            boxShadow: "0 0 26px rgba(255,232,180,0.85)",
            opacity: folds > 0 ? clamp(1 - p / 0.45) * (1 - Math.abs(0.5 - p) * 0.8) : 0,
          }}
        />

        {/* 折不动时边缘泛红 */}
        <div
          style={{
            position: "absolute",
            left: cx - wNow / 2 - 7,
            top: faceY - 2,
            width: wNow + 14,
            height: 4,
            background: `linear-gradient(90deg, rgba(255,91,91,0), ${C.red}, rgba(255,91,91,0))`,
            opacity: fp > 0 ? Math.sin(clamp(fp * 1.6) * Math.PI) * 0.85 : 0,
            filter: "blur(1px)",
          }}
        />

        {/* 左侧量线：只标当前高度，跟着纸叠长，永远贴着左边缘 */}
        <div
          style={{
            position: "absolute",
            left: mx,
            top: faceY,
            width: 1,
            height: baseY - faceY,
            background: `linear-gradient(180deg, #ffe6a8, rgba(243,193,75,0.22))`,
            boxShadow: "0 0 10px rgba(243,193,75,0.45)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: mx - 8,
            top: baseY - 1,
            width: 16,
            height: 1,
            background: "rgba(243,193,75,0.55)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: mx - 12,
            top: faceY,
            width: 24,
            height: 1,
            background: C.gold,
            boxShadow: `0 0 12px ${C.gold}`,
          }}
        />

        {/* 一根虚线把纸和右边读数连上，不然两个东西像各说各的 */}
        <div
          style={{
            position: "absolute",
            left: cx + wNow / 2 + 6,
            top: faceY,
            width: Math.max(0, 1340 - (cx + wNow / 2 + 6)),
            height: 1,
            backgroundImage:
              "repeating-linear-gradient(90deg, rgba(243,193,75,0.42) 0px, rgba(243,193,75,0.42) 4px, rgba(0,0,0,0) 4px, rgba(0,0,0,0) 11px)",
            opacity: rise,
          }}
        />

        {/* 示意：挂在量线脚下，说明"量"是示意的 */}
        <div
          style={{
            position: "absolute",
            left: mx - 2,
            top: baseY + 12,
            fontFamily: FONT,
            fontSize: 17,
            letterSpacing: 4,
            color: "rgba(139,147,167,0.45)",
            opacity: rise,
          }}
        >
          示意
        </div>

        {/* 左侧标签 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 8,
            color: C.cyan,
            opacity: rise,
          }}
        >
          {kicker}
        </div>

        {/* 右侧读数 */}
        {readout ? (
          <div
            style={{
              position: "absolute",
              left: 1380,
              top: 286,
              width: 420,
              opacity: rise,
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
              现在这么厚
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
              {Math.round(layersDone)} 层
            </div>
          </div>
        ) : null}

        {/* 左上角算式：跟章节标排成一列，不下去和字幕抢地方 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 196,
            fontFamily: FONT,
            fontSize: 24,
            letterSpacing: 2,
            color: "rgba(139,147,167,0.8)",
            opacity: rise,
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
