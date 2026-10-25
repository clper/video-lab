import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";

// 2002 年，加州，一间房的地板。
// 全片只有这一镜有"人"——而且是个剪影，没有脸。
// 一束冷光从窗口斜切进来，人和那卷纸都坐在光里；右侧是三个信息：
// 年份、地名、名字。年份滚上去，名字最后落下来——她叫 Britney Gallivan，16 岁。

type Props = {
  kicker?: string;
  note?: string;
  /** room：只有年份和地名；name：名字落下来 */
  stage?: "room" | "name";
  name?: string;
  sub?: string;
};

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (v: number) => 1 - Math.pow(1 - clamp(v), 3);

const FLOOR_Y = 772;

/** 坐在地板上的人：头、肩、弯着的腿。只用一条路径，不画细节 */
const Sitter: React.FC<{ color: string }> = ({ color }) => (
  <svg width="300" height="330" viewBox="0 0 300 330">
    <g fill={color}>
      {/* 头 */}
      <circle cx="150" cy="52" r="34" />
      {/* 头发：垂到肩 */}
      <path d="M116 46c0-26 14-42 34-42s34 16 34 42c0 10-4 16-10 20 6 12 6 26 2 40-6-14-10-22-18-26-10 6-26 6-36 0-8 6-12 16-16 28-4-14-6-28 0-42-6-4-10-10-10-20z" />
      {/* 身子：坐着往前倾，抱着膝盖 */}
      <path d="M150 96c26 0 44 18 46 44l6 62c1 10-6 18-16 18h-56c-10 0-17-8-16-18l6-62c2-26 20-44 46-44z" />
      {/* 腿：盘在身前 */}
      <path d="M96 214c26-14 76-14 106 0 18 8 22 22 10 34-16 16-52 24-88 18-34-6-52-22-44-36 4-8 12-12 16-16z" />
      {/* 胳膊：把纸卷抱在怀里 */}
      <path d="M104 148c-10 14-14 34-8 52 4 12 16 16 24 8 6-6 6-16 2-24-6-12-6-26 0-36z" />
    </g>
  </svg>
);

export const Gallivan: React.FC<Props> = ({
  kicker = "03 · 墙　THE WALL",
  note = "她那年 16 岁。没有实验室，只有一卷卫生纸和一条走廊。",
  stage = "room",
  name = "Britney Gallivan",
  sub = "16 岁 · 加州",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s } = useStage();

  const sceneP = ease((frame - 2) / (fps * 0.8));
  const yearP = ease((frame - Math.round(fps * 0.35)) / (fps * 0.7));
  const nameP = stage === "name" ? ease((frame - Math.round(fps * 0.5)) / (fps * 0.9)) : 0;

  // 年份从下面滚上去
  const yearRoll = (1 - yearP) * 90;

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
        {/* 窗光：一块斜着落在地板上的冷光 */}
        <div
          style={{
            position: "absolute",
            left: 200,
            top: 120,
            width: 980,
            height: 660,
            clipPath: "polygon(22% 0%, 78% 0%, 100% 100%, 0% 100%)",
            background:
              "linear-gradient(175deg, rgba(96,150,210,0.30) 0%, rgba(96,150,210,0.16) 55%, rgba(96,150,210,0.05) 100%)",
            filter: "blur(14px)",
            opacity: sceneP,
          }}
        />
        {/* 地板线 */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: FLOOR_Y,
            width: 1920,
            height: 1,
            background:
              "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.14) 45%, rgba(255,255,255,0) 92%)",
            opacity: sceneP,
          }}
        />
        {/* 地板上的一点反光 */}
        <div
          style={{
            position: "absolute",
            left: 210,
            top: FLOOR_Y,
            width: 760,
            height: 150,
            background: "radial-gradient(ellipse at 40% 0%, rgba(120,170,225,0.14) 0%, rgba(120,170,225,0) 70%)",
            opacity: sceneP,
          }}
        />

        {/* 人：比场景小一号，但轮廓要清楚（逆光，不画脸） */}
        <div
          style={{
            position: "absolute",
            left: 372,
            top: FLOOR_Y - 372,
            opacity: sceneP,
            transform: `translateY(${(1 - sceneP) * 16}px) scale(1.12)`,
            transformOrigin: "50% 100%",
          }}
        >
          <Sitter color="#04050a" />
        </div>
        {/* 坐在地上的影子 */}
        <div
          style={{
            position: "absolute",
            left: 356,
            top: FLOOR_Y - 18,
            width: 380,
            height: 40,
            background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 72%)",
            opacity: sceneP,
          }}
        />
        {/* 剪影的轮廓光（左侧来光） */}
        <div
          style={{
            position: "absolute",
            left: 388,
            top: FLOOR_Y - 328,
            width: 296,
            height: 326,
            opacity: sceneP * 0.85,
            mixBlendMode: "screen",
            filter: "blur(5px)",
            background: "radial-gradient(ellipse at 16% 42%, rgba(165,205,250,0.42) 0%, rgba(165,205,250,0) 58%)",
          }}
        />

        {/* 怀里的那卷纸：用圆柱的明暗来做，不要发光 —— 发光的圆柱看着像灯管 */}
        <div
          style={{
            position: "absolute",
            left: 428,
            top: FLOOR_Y - 158,
            width: 124,
            height: 34,
            borderRadius: 4,
            background:
              "linear-gradient(180deg, #8e846d 0%, #cfc4a6 22%, #f4ecd8 46%, #fffaf0 55%, #ddd2b6 78%, #7d735c 100%)",
            boxShadow: "0 6px 18px rgba(0,0,0,0.45)",
            opacity: sceneP,
            transform: "rotate(-6deg)",
          }}
        >
          {/* 纸头露出来的那一道边 */}
          <div
            style={{
              position: "absolute",
              left: 10,
              top: 1,
              bottom: 1,
              width: 2,
              background: "rgba(120,108,86,0.45)",
            }}
          />
          {/* 卷芯：一道深色的缝 */}
          <div
            style={{
              position: "absolute",
              left: 46,
              top: 3,
              bottom: 3,
              width: 1,
              background: "rgba(90,80,62,0.35)",
            }}
          />
        </div>

        {/* 章节标 */}
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 124,
            display: "flex",
            alignItems: "center",
            gap: 16,
            opacity: clamp(sceneP * 2),
          }}
        >
          <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: 7, color: C.cyan }}>{kicker}</div>
          <div style={{ width: 90, height: 1, background: "rgba(73,227,209,0.45)" }} />
        </div>

        {/* 年份 + 地名。不要再套 overflow:hidden：它会把 70px 的金色泛光裁成一块
            硬边矩形（背在“2002”后面像贴了张纸）。滚动靠 translateY + 淡入就够了。 */}
        <div style={{ position: "absolute", left: 1000, top: 300 }}>
          <div
            style={{
              fontFamily: FONT,
              fontWeight: 700,
              fontSize: 210,
              lineHeight: 1,
              color: C.gold,
              fontVariantNumeric: "tabular-nums",
              transform: `translateY(${yearRoll}px)`,
              opacity: clamp(yearP * 1.4),
              textShadow: "0 0 70px rgba(243,193,75,0.18)",
            }}
          >
            2002
          </div>
        </div>
        <div
          style={{
            position: "absolute",
            left: 1006,
            top: 540,
            fontFamily: FONT,
            fontSize: 34,
            letterSpacing: 12,
            color: "rgba(246,242,231,0.8)",
            opacity: yearP,
          }}
        >
          CALIFORNIA
        </div>

        {/* 名字 */}
        {stage === "name" ? (
          <div
            style={{
              position: "absolute",
              left: 1006,
              top: 626,
              opacity: nameP,
              transform: `translateY(${(1 - nameP) * 18}px)`,
            }}
          >
            <div style={{ width: 76, height: 2, background: C.cyan, opacity: 0.8 }} />
            <div
              style={{
                marginTop: 20,
                fontFamily: FONT,
                fontWeight: 700,
                fontSize: 62,
                letterSpacing: 1,
                color: C.ink,
              }}
            >
              {name}
            </div>
            <div
              style={{
                marginTop: 12,
                fontFamily: FONT,
                fontSize: 28,
                letterSpacing: 3,
                color: "rgba(139,147,167,0.9)",
              }}
            >
              {sub}
            </div>
          </div>
        ) : null}

        {/* 出处小字 */}
        <div
          style={{
            position: "absolute",
            right: 120,
            bottom: 96,
            fontFamily: FONT,
            fontSize: 20,
            letterSpacing: 1,
            color: "rgba(139,147,167,0.55)",
            opacity: sceneP,
          }}
        >
          {note}
        </div>
      </div>
    </AbsoluteFill>
  );
};
