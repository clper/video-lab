import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C } from "../design/tokens";
import { mulberry32 } from "../common/random";

// 七层全局特效栈：手持微动、扫光、快门闪、暗场呼吸、颗粒扫描线、星尘底纹、字幕条。
// 每一层都能单独关掉（Phase 2 做逐镜开关时直接传 layers）。
//
// 两条与“频闪”有关的规矩（006 修）：
//   1. flash（切点白闪）默认关：每镜都闪一次，51 镜就是 51 次白闪，暗场里全变成灰屏；
//      章节切换改用 dip（压暗）—— 人眼对“变暗”的容忍度远高于“变白”。
//   2. 星尘/扫光/呼吸用 t0（全片绝对帧）计时，不用镜内帧：否则每次切镜相位归零，
//      120 颗星会在同一帧集体换亮度，背景“跳一下”。
export type FXLayer =
  | "handheld"
  | "sweep"
  | "flash"
  | "breathing"
  | "grain"
  | "stardust"
  | "dip"
  | "subtitleBar";

type Props = {
  children: React.ReactNode;
  shotStarts?: number[];
  layers?: Partial<Record<FXLayer, boolean>>;
  /** 本镜在全片的起始帧：背景层用它计时，切镜时背景不动 */
  t0?: number;
  /** 入场从多黑浮起（0 = 不用）；普通镜 0.15，章节首镜 0.55 */
  dipIn?: number;
  /** 出场压到多黑；章节末镜 0.55 */
  dipOut?: number;
  /** 压暗用几帧走完（默认 4 帧 = 0.13s，看不见，但硬切变圆） */
  dipFrames?: number;
  /** 左上角角标，按视频换 */
  brand?: string;
  /** 右下角编号 */
  slug?: string;
};

const on = (layers: Props["layers"], name: FXLayer): boolean =>
  layers?.[name] !== false;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

const Stardust: React.FC<{ t: number }> = ({ t }) => {
  const { width, height } = useVideoConfig();
  const stars = useMemo(() => {
    const rnd = mulberry32(20261024);
    return Array.from({ length: 120 }, () => ({
      x: rnd() * width,
      y: rnd() * height,
      r: 0.8 + rnd() * 2.2,
      ph: rnd() * Math.PI * 2,
      sp: 0.4 + rnd() * 0.8,
      cyan: rnd() > 0.78,
    }));
  }, [width, height]);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {stars.map((s, i) => {
        const twinkle = 0.18 + 0.5 * (0.5 + 0.5 * Math.sin(t * 0.05 * s.sp + s.ph));
        const drift = Math.sin(t * 0.01 + s.ph) * 6;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: s.x,
              top: s.y + drift,
              width: s.r * 2,
              height: s.r * 2,
              borderRadius: "50%",
              background: s.cyan ? C.cyan : C.ink,
              opacity: twinkle,
              boxShadow: `0 0 ${s.r * 4}px ${s.cyan ? C.cyan : C.ink}`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const Sweep: React.FC<{ t: number }> = ({ t }) => {
  // 一道细光斜着扫过，而不是一条常驻的宽灰带：
  // 宽度 36%、峰值 0.06 时整块画面有三分之一被提亮，暗底上看像蒙了层脏，
  // 而且每个镜头都全程可见。改成窄光（16%）+ 只在周期前 42% 出现，其余时间完全隐形。
  const period = 150;
  const pass = 0.42;
  const ph = (t % period) / period;
  if (ph > pass) return null;
  const p = ph / pass;
  const left = -25 + p * 150;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          top: "-30%",
          left: `${left}%`,
          width: "16%",
          height: "160%",
          transform: "rotate(12deg)",
          background:
            "linear-gradient(105deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.02) 38%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.02) 62%, rgba(255,255,255,0) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

const Flash: React.FC<{ frame: number; shotStarts: number[] }> = ({ frame, shotStarts }) => {
  // 切点白闪：每个镜头单独渲染，shotStarts 里通常只有 0。
  // 峰值 0.30 / 两帧退完：0.42 三帧把整帧推到了接近灰白（YAVG 26→94），连看 15 次太晃，
  // 抽帧对照图也会正好落在闪帧上，看着像渲坏了。
  let opacity = 0;
  for (const s of shotStarts) {
    const d = frame - s;
    if (d >= 0 && d <= 2) opacity = Math.max(opacity, 0.3 * (1 - d / 2));
  }
  if (opacity <= 0) return null;
  return <AbsoluteFill style={{ background: "#ffffff", opacity, pointerEvents: "none" }} />;
};

const Breathing: React.FC<{ t: number }> = ({ t }) => {
  const opacity = 0.62 + 0.12 * Math.sin(t * 0.045);
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        opacity,
        background:
          "radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 34%, rgba(0,0,0,0.62) 100%)",
      }}
    />
  );
};

const Scanlines: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      opacity: 0.2,
      background:
        "repeating-linear-gradient(to bottom, rgba(0,0,0,0.10) 0px, rgba(0,0,0,0.10) 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 3px)",
      transform: `translateY(${t % 3}px)`,
    }}
  />
);

/**
 * 入场/出场压暗。章节切换用它，不用白闪：
 * 人眼对“变暗”宽容，对“整屏发白”敏感 —— 暗场片子里白闪就是那个频闪感。
 */
const Dip: React.FC<{ frame: number; dur: number; inDepth: number; outDepth: number; frames: number }> = ({
  frame,
  dur,
  inDepth,
  outDepth,
  frames,
}) => {
  const f = Math.max(1, Math.round(frames));
  let opacity = 0;
  if (inDepth > 0) opacity = Math.max(opacity, inDepth * (1 - clamp01(frame / f)));
  if (outDepth > 0) opacity = Math.max(opacity, outDepth * clamp01((frame - (dur - f)) / f));
  if (opacity <= 0.002) return null;
  return <AbsoluteFill style={{ background: C.bg, opacity, pointerEvents: "none" }} />;
};

const Grain: React.FC = () => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <svg width="100%" height="100%" style={{ opacity: 0.06, mixBlendMode: "overlay" }}>
      <filter id="vlab-grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#vlab-grain)" />
    </svg>
  </AbsoluteFill>
);

const SubtitleBar: React.FC<{ brand: string; slug: string }> = ({ brand, slug }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    <div style={{ position: "absolute", left: 64, top: 58 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ width: 10, height: 10, background: C.gold, transform: "rotate(45deg)" }} />
        <div style={{ fontFamily: "SourceHanSansCN", fontSize: 22, letterSpacing: 8, color: C.gold }}>
          {brand}
        </div>
      </div>
      <div
        style={{
          marginTop: 14,
          marginLeft: 24,
          width: 150,
          height: 1,
          background: C.goldDim,
          opacity: 0.6,
        }}
      />
    </div>
    <div
      style={{
        position: "absolute",
        right: 64,
        bottom: 46,
        fontFamily: "SourceHanSansCN",
        fontSize: 18,
        letterSpacing: 4,
        color: C.dim,
      }}
    >
      {slug}
    </div>
  </AbsoluteFill>
);

export const GlobalFX: React.FC<Props> = ({
  children,
  shotStarts = [],
  layers,
  t0 = 0,
  dipIn = 0,
  dipOut = 0,
  dipFrames = 4,
  brand = "VIBE / 涌现",
  slug = "005",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = frame + t0;         // 背景层的“时钟”：跨镜连续，切镜时不归一

  // 手持微动：叠加在内容上，特效层保持屏幕空间固定，避免整块画面跟着抖
  const hx = Math.sin(t * 0.17) * 1.6 + Math.sin(t * 0.53) * 0.5;
  const hy = Math.cos(t * 0.13) * 1.9 + Math.cos(t * 0.41) * 0.6;
  const rot = Math.sin(t * 0.09) * 0.12;
  // 缓推：整镜极慢推近 1.5%（首尾各留 8% 不动）。
  // 不推的话长镜就是一张静帧，观众只能靠读字幕撑着（006 实测：全片每 10s 平均帧间差
  // 只有 0.5，唯独 30–40s 那段是 3.1 —— 不是太快，是太死）。幅度小到说不出哪里在动。
  const push = clamp01((frame - durationInFrames * 0.08) / (durationInFrames * 0.84));
  const dolly = 1.012 + 0.015 * push;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(120% 80% at 50% 28%, ${C.bg2} 0%, ${C.bg} 62%)`,
      }}
    >
      {on(layers, "stardust") && <Stardust t={t} />}

      <AbsoluteFill
        style={{
          transform: on(layers, "handheld")
            ? `translate(${hx}px, ${hy}px) rotate(${rot}deg) scale(${dolly})`
            : undefined,
        }}
      >
        {children}
      </AbsoluteFill>

      {on(layers, "sweep") && <Sweep t={t} />}
      {on(layers, "grain") && (
        <>
          <Scanlines t={t} />
          <Grain />
        </>
      )}
      {on(layers, "breathing") && <Breathing t={t} />}
      {on(layers, "dip") && (
        <Dip frame={frame} dur={durationInFrames} inDepth={dipIn} outDepth={dipOut} frames={dipFrames} />
      )}
      {on(layers, "flash") && <Flash frame={frame} shotStarts={shotStarts} />}
      {on(layers, "subtitleBar") && <SubtitleBar brand={brand} slug={slug} />}
    </AbsoluteFill>
  );
};
