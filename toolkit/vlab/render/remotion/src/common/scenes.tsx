// 程序化"照片"：不引入任何图片素材，用渐变 + 太阳 + 地平线 + 鸟字形拼出一张风景照，
// 给拍立得、蒙版擦除这类需要"一张图"的卡片当素材。同一个 seed 永远画出同一张。
import React from "react";
import { C } from "../design/tokens";
import { mulberry32 } from "./random";

export type SceneHue = "gold" | "cyan" | "red" | "night";

const HUE: Record<SceneHue, string> = {
  gold: "#f3c14b",
  cyan: "#49e3d1",
  red: "#ff5b5b",
  night: "#8fa7ff",
};

type Props = {
  seed?: number;
  hue?: SceneHue;
  /** 鸟的数量，0 表示纯风景 */
  birds?: number;
  style?: React.CSSProperties;
};

export const AbstractScene: React.FC<Props> = ({ seed = 3, hue = "gold", birds = 26, style }) => {
  const rnd = mulberry32(seed);
  const accent = HUE[hue];
  const horizon = 0.62 + rnd() * 0.12; // 地平线在画面高度里的位置
  const sunX = 0.2 + rnd() * 0.6;
  const sunY = horizon - 0.1 - rnd() * 0.18;
  const sunR = 0.1 + rnd() * 0.06;

  const flock = Array.from({ length: birds }, () => {
    const x = 0.05 + rnd() * 0.9;
    const y = horizon - 0.12 - rnd() * 0.42;
    const s = 0.012 + rnd() * 0.022;
    return { x, y, s, o: 0.25 + rnd() * 0.6 };
  });
  const bands = Array.from({ length: 7 }, (_, i) => ({ y: horizon + i * 0.055, o: 0.1 - i * 0.012 }));

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        background: `radial-gradient(120% 80% at ${sunX * 100}% ${sunY * 100}%, ${accent}33 0%, transparent 55%),
                     linear-gradient(180deg, #070912 0%, #131a2c 55%, #05070e 100%)`,
        ...style,
      }}
    >
      {/* 太阳 */}
      <div
        style={{
          position: "absolute",
          left: `${sunX * 100}%`,
          top: `${sunY * 100}%`,
          width: `${sunR * 200}%`,
          height: `${sunR * 200}%`,
          marginLeft: `-${sunR * 100}%`,
          marginTop: `-${sunR * 100}%`,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${accent} -20%, ${accent}00 70%)`,
          filter: "blur(2px)",
        }}
      />
      {/* 云带 */}
      {bands.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: `${b.y * 100}%`,
            height: `${0.02 + i * 0.004}%`,
            background: `linear-gradient(90deg, transparent, ${accent}${Math.round(b.o * 255).toString(16).padStart(2, "0")}, transparent)`,
          }}
        />
      ))}
      {/* 鸟群：两条弧线拼的 V 字 */}
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: "absolute", inset: 0 }}>
        {flock.map((b, i) => (
          <path
            key={i}
            d={`M ${b.x * 100 - b.s * 100} ${b.y * 100 - b.s * 40} Q ${b.x * 100} ${b.y * 100 + b.s * 30} ${b.x * 100 + b.s * 100} ${b.y * 100 - b.s * 40}`}
            fill="none"
            stroke={C.ink}
            strokeWidth={0.22}
            opacity={b.o}
          />
        ))}
      </svg>
    </div>
  );
};
