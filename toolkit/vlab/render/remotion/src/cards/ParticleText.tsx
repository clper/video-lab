import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  Easing,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { C, FONT } from "../design/tokens";
import { mulberry32 } from "../common/random";

type Pt = { x: number; y: number };

type Props = {
  text: string;
  kicker?: string;
  sub?: string;
  seed?: number;
};

const SAMPLE_W = 620;
const SAMPLE_H = 320;
const FONT_PX = 200;
const MAX_PARTICLES = 760;

// 粒子聚字：先把文字画进离屏 canvas，采样字形里的点当目标位置，
// 粒子从四周飞入落位，最后真字淡入接管。同一 seed 永远同一轨迹。
export const ParticleText: React.FC<Props> = ({ text, kicker, sub, seed = 7 }) => {
  const frame = useCurrentFrame();
  const [targets, setTargets] = useState<Pt[] | null>(null);
  const [handle] = useState(() => delayRender("采样文字粒子"));

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await document.fonts.load(`700 ${FONT_PX}px "${FONT}"`);
        await document.fonts.ready;
      } catch {
        // 字体没加载到也要继续，否则整帧卡死
      }

      const canvas = document.createElement("canvas");
      canvas.width = SAMPLE_W;
      canvas.height = SAMPLE_H;
      const ctx = canvas.getContext("2d");
      const pts: Pt[] = [];

      if (ctx) {
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.font = `700 ${FONT_PX}px "${FONT}"`;
        ctx.fillText(text, SAMPLE_W / 2, SAMPLE_H / 2);
        const { data } = ctx.getImageData(0, 0, SAMPLE_W, SAMPLE_H);
        const step = 4;
        for (let y = 0; y < SAMPLE_H; y += step) {
          for (let x = 0; x < SAMPLE_W; x += step) {
            if (data[(y * SAMPLE_W + x) * 4 + 3] > 128) {
              pts.push({ x: x - SAMPLE_W / 2, y: y - SAMPLE_H / 2 });
            }
          }
        }
      }

      if (!cancelled) setTargets(pts);
      continueRender(handle);
    })();
    return () => {
      cancelled = true;
    };
  }, [handle, text]);

  const particles = useMemo(() => {
    if (!targets || targets.length === 0) return [];
    const rnd = mulberry32(seed);
    const idx = targets.map((_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    return idx.slice(0, Math.min(MAX_PARTICLES, idx.length)).map((i) => {
      const t = targets[i];
      const ang = rnd() * Math.PI * 2;
      // 起点半径和延迟都收小一点：原来粒子要飞近 2 秒才成形，
      // 镜头开头 0.4 秒里几乎没东西（逐帧质检会报“缺结构”，观感上也像卡了一下）
      const rad = 380 + rnd() * 520;
      return {
        tx: t.x,
        ty: t.y,
        sx: Math.cos(ang) * rad,
        sy: Math.sin(ang) * rad * 0.85,
        delay: rnd() * 10,
        size: 1.5 + rnd() * 2.6,
        color: rnd() > 0.88 ? C.cyan : rnd() > 0.83 ? C.magenta : C.gold,
      };
    });
  }, [targets, seed]);

  const textOpacity = interpolate(frame, [56, 80], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textScale = interpolate(frame, [56, 90], [1.14, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const textBlur = interpolate(frame, [56, 82], [10, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      {particles.map((p, i) => {
        const t = Math.min(1, Math.max(0, (frame - p.delay) / 38));
        const e = 1 - Math.pow(1 - t, 3);
        const x = p.sx + (p.tx - p.sx) * e;
        const y = p.sy + (p.ty - p.sy) * e;
        const glow = t >= 1 ? 0.4 + 0.22 * Math.sin((frame + i) * 0.2) : 1;
        // 透明度单独走一条快弧线：跟着飞行进度走的话，镜头开头粒子还在远处就是全透明的，
        // 前 0.4 秒画面只剩底色（逐帧质检会判“缺结构”，观感也像没开镜）。
        const appear = Math.min(1, Math.max(0, (frame - p.delay) / 6));
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 540 + x - p.size / 2,
              top: 1055 + y - p.size / 2,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              background: p.color,
              opacity: appear * glow,
              boxShadow: `0 0 ${p.size * 4}px ${p.color}`,
            }}
          />
        );
      })}

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 872,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 22,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 26,
            letterSpacing: 10,
            color: C.cyan,
            opacity: interpolate(frame, [4, 20], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {kicker}
        </div>
        <div
          style={{
            fontFamily: FONT,
            fontWeight: 700,
            fontSize: 200,
            letterSpacing: 12,
            color: C.ink,
            opacity: textOpacity,
            transform: `scale(${textScale})`,
            filter: `blur(${textBlur}px)`,
            textShadow: "0 0 48px rgba(243,193,75,0.35)",
          }}
        >
          {text}
        </div>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 34,
            letterSpacing: 6,
            color: C.dim,
            opacity: interpolate(frame, [66, 86], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          {sub}
        </div>
      </div>
    </AbsoluteFill>
  );
};
