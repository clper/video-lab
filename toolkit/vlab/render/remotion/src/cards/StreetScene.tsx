import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp, lerp, mulberry32 } from "../common/random";
import { Note, ease, span } from "../lib/boardDraw";

// 黄昏的街：两家一样的小店，一家门口排长队，一家空着。
// 008 的开场和回场都在这条街上——结尾回来时是夜里，那家没人排队的店灯还亮着，第一次有人停下脚步。
// 全是程序化的形状（天空渐变、剪影、暖窗、路灯、湿地面的倒影），不用图片；人只画剪影，不画脸。

export type StreetMode =
  | "queue"     // 定场：排队的和空着的
  | "doors"     // 镜头推向两扇门之间
  | "shadow"    // 队伍的影子越拉越长 + 大字
  | "dark"      // 街景淡出，暗场里亮起 8 个光点
  | "title"     // 片名：那家没人排队的店，灯亮着
  | "callback"  // 夜里回到这条街 + 大字
  | "visitor";  // 一个人走过来，在空着的那家门口停下 + 大字

type Props = {
  mode?: StreetMode;
  /** 大字（代替字幕） */
  line?: string;
  title?: string;
  note?: string;
};

const W = 1920;
const H = 1080;
const GROUND = 800;
// 左边那家排队，右边那家空着
const SHOP_L = { x: 250, w: 520 };
const SHOP_R = { x: 1150, w: 520 };
const WARM = "rgba(255,186,108,1)";

const Person: React.FC<{ x: number; y: number; h?: number; sway?: number; rim?: string; phone?: number }> = ({
  x,
  y,
  h = 1,
  sway = 0,
  rim = "rgba(255,196,120,0.55)",
  phone = 0,
}) => (
  <g transform={`translate(${x} ${y}) scale(${h})`}>
    <circle cx={sway * 2} cy={-118} r={13} fill="#070910" stroke={rim} strokeWidth={1.4} />
    <path d={`M${-19 + sway} 0 L${-14 + sway} -98 Q0 -112 ${14 + sway} -98 L${19 + sway} 0 Z`} fill="#070910" stroke={rim} strokeWidth={1.4} />
    {/* 低头看手机：胸前一小块冷光 */}
    {phone > 0 ? (
      <>
        <rect x={4 + sway} y={-80} width={7} height={11} rx={1.5} fill="#bfe9ff" opacity={0.85 * phone} />
        <circle cx={7.5 + sway} cy={-76} r={16} fill="#9fdcff" opacity={0.16 * phone} filter="url(#ss-glow-s)" />
      </>
    ) : null}
  </g>
);

const Lamp: React.FC<{ x: number; on: number; flip?: boolean }> = ({ x, on, flip = false }) => {
  const d = flip ? -1 : 1;
  const hx = x + 47 * d;
  return (
    <g>
      <path d={`M${x} ${GROUND} L${x} ${GROUND - 330} Q${x} ${GROUND - 352} ${x + 24 * d} ${GROUND - 352} L${x + 40 * d} ${GROUND - 352}`} stroke="#090b13" strokeWidth={7} fill="none" />
      <rect x={Math.min(x + 30 * d, x + 64 * d)} y={GROUND - 358} width={34} height={10} rx={3} fill="#090b13" />
      <path d={`M${hx - 7} ${GROUND - 344} L${hx + 7} ${GROUND - 344} L${hx + 120} ${GROUND} L${hx - 120} ${GROUND} Z`} fill="url(#ss-cone)" opacity={0.6 * on} />
      <ellipse cx={hx} cy={GROUND + 22} rx={170} ry={26} fill="rgba(255,214,150,1)" opacity={0.14 * on} filter="url(#ss-blur)" />
      <circle cx={hx} cy={GROUND - 344} r={16} fill="#ffe2b0" opacity={0.5 * on} filter="url(#ss-glow-s)" />
      <circle cx={hx} cy={GROUND - 344} r={5} fill="#fff3da" opacity={0.3 + 0.7 * on} />
    </g>
  );
};

const Shop: React.FC<{ x: number; w: number; lit: number; night: number; busy: boolean }> = ({ x, w, lit, night, busy }) => {
  const top = GROUND - 360;
  const warm = `rgba(255,190,110,${0.18 + 0.72 * lit})`;
  return (
    <g>
      {/* 窗光往外溢 */}
      <rect x={x + 26} y={top + 136} width={w - 212} height={198} rx={10} fill={WARM} opacity={0.4 * lit} filter="url(#ss-glow)" />
      <rect x={x + w - 184} y={top + 136} width={148} height={238} rx={10} fill={WARM} opacity={0.34 * lit} filter="url(#ss-glow)" />
      {/* 门脸 */}
      <rect x={x} y={top} width={w} height={360} fill={night > 0.5 ? "#0b0e18" : "#171527"} stroke="rgba(255,255,255,0.08)" />
      {/* 遮阳篷：一条条的 */}
      <path d={`M${x - 16} ${top + 92} L${x + w + 16} ${top + 92} L${x + w - 10} ${top + 130} L${x + 10} ${top + 130} Z`} fill={busy ? "#5a2a2a" : "#2a3a5a"} opacity={0.9 - 0.4 * night} />
      {Array.from({ length: 9 }, (_, i) => (
        <path
          key={i}
          d={`M${x - 16 + ((w + 32) * (i + 0.5)) / 9} ${top + 92} L${x + 10 + ((w - 20) * (i + 0.5)) / 9 - 6} ${top + 130} L${x + 10 + ((w - 20) * (i + 0.5)) / 9 + 6} ${top + 130} L${x - 16 + ((w + 32) * (i + 0.5)) / 9 + 8} ${top + 92} Z`}
          fill="rgba(255,255,255,0.06)"
        />
      ))}
      {/* 招牌（不写字） */}
      <rect x={x + 60} y={top + 26} width={w - 120} height={46} rx={6} fill="rgba(0,0,0,0.35)" stroke={`rgba(255,220,160,${0.25 + 0.5 * lit})`} />
      <rect x={x + 90} y={top + 44} width={w - 180} height={10} rx={5} fill={`rgba(255,220,160,${0.12 + 0.3 * lit})`} />
      {/* 大窗 + 窗格 + 里面的桌椅剪影 */}
      <rect x={x + 40} y={top + 150} width={w - 240} height={170} rx={4} fill={warm} opacity={0.92} />
      <line x1={x + 40 + (w - 240) / 2} y1={top + 150} x2={x + 40 + (w - 240) / 2} y2={top + 320} stroke="rgba(30,20,20,0.35)" strokeWidth={4} />
      {[0.22, 0.72].map((f, i) => (
        <g key={i} fill="rgba(40,24,18,0.45)">
          <rect x={x + 40 + (w - 240) * f - 34} y={top + 268} width={68} height={8} rx={2} />
          <rect x={x + 40 + (w - 240) * f - 4} y={top + 276} width={8} height={44} />
        </g>
      ))}
      <rect x={x + 40} y={top + 150} width={w - 240} height={170} rx={4} fill="none" stroke="rgba(255,255,255,0.12)" />
      {/* 门 */}
      <rect x={x + w - 170} y={top + 150} width={120} height={210} rx={3} fill={`rgba(255,180,100,${0.12 + 0.6 * lit})`} stroke="rgba(255,255,255,0.14)" />
      <circle cx={x + w - 66} cy={top + 260} r={4} fill="rgba(60,40,30,0.7)" />
      {/* 门口洒在地上的光 */}
      <path d={`M${x + w - 190} ${GROUND} L${x + w - 30} ${GROUND} L${x + w + 90} ${GROUND + 150} L${x + w - 330} ${GROUND + 150} Z`} fill={`rgba(255,180,100,${0.05 + 0.22 * lit})`} />
      {/* 湿地面上的倒影 */}
      <rect x={x + 40} y={GROUND + 12} width={w - 240} height={120} fill={WARM} opacity={0.11 * lit} filter="url(#ss-blur)" />
      <rect x={x + w - 170} y={GROUND + 12} width={120} height={150} fill={WARM} opacity={0.1 * lit} filter="url(#ss-blur)" />
    </g>
  );
};

export const StreetScene: React.FC<Props> = ({ mode = "queue", line = "", title = "", note = "" }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();
  const p = clamp(frame / Math.max(1, durationInFrames - 1));
  const t = frame / fps;

  const night = mode === "title" || mode === "callback" || mode === "visitor" ? 1 : mode === "shadow" ? 0.25 : mode === "dark" ? 0.4 : 0;
  const darkOut = mode === "dark" ? 0.82 * ease(span(p, 0.3, 0.8)) : 0;
  const lampOn = night > 0.5 ? 1 : 0.35 + 0.3 * night;

  // 队伍：14 个人从左边那家的门口排到街头，微微挪动；有几个人低头看手机
  const queue = React.useMemo(() => {
    const rnd = mulberry32(20261027);
    return Array.from({ length: 14 }, (_, i) => ({
      x: SHOP_L.x + SHOP_L.w - 120 - i * 36 - rnd() * 10,
      h: 0.92 + rnd() * 0.16,
      ph: rnd() * Math.PI * 2,
      sp: 0.6 + rnd() * 0.8,
      phone: i % 3 === 1 ? 1 : 0,
    }));
  }, []);
  const stars = React.useMemo(() => {
    const rnd = mulberry32(1027);
    return Array.from({ length: 70 }, () => ({ x: rnd() * W, y: rnd() * 380, r: 0.6 + rnd() * 1.6, ph: rnd() * 6.28 }));
  }, []);

  // 相机
  const cam = (() => {
    if (mode === "queue") return { sc: 1 + 0.035 * p, ox: 0, oy: 0, origin: "960px 700px" };
    if (mode === "doors") return { sc: lerp(1.03, 1.3, ease(p)), ox: 0, oy: lerp(0, -40, ease(p)), origin: "960px 660px" };
    if (mode === "shadow") return { sc: 1.08, ox: lerp(40, -40, p), oy: -10, origin: "960px 700px" };
    if (mode === "title") {
      const cx = SHOP_R.x + SHOP_R.w / 2;
      return { sc: 1.35, ox: 960 - cx, oy: -60, origin: `${cx}px 640px` };
    }
    if (mode === "visitor") return { sc: lerp(1.05, 1.18, ease(p)), ox: lerp(0, -160, ease(p)), oy: -30, origin: "1300px 680px" };
    return { sc: 1.02, ox: 0, oy: 0, origin: "960px 660px" };
  })();

  // 影子长度（shadow）：太阳越低影子越长
  const shadowLen = mode === "shadow" ? lerp(60, 260, ease(p)) : 60;

  // 天空
  const skyTop = night > 0.5 ? "#04060d" : mode === "shadow" || mode === "dark" ? "#181030" : "#1c1838";
  const skyMid = night > 0.5 ? "#0a0f22" : "#5a2a4a";
  const skyHorizon = night > 0.5 ? "#262036" : "#f3a560";

  const sceneO = 1 - darkOut;
  const lineP = line ? ease(span(p, mode === "visitor" ? 0.35 : 0.2, mode === "visitor" ? 0.7 : 0.55)) : 0;
  const titleP = title ? ease(span(p, 0.12, 0.5)) : 0;

  // visitor：一个人从右边走过来，在右边那家门口停下
  const vK = mode === "visitor" ? ease(span(p, 0.08, 0.72)) : 0;
  const vX = lerp(1900, SHOP_R.x + SHOP_R.w - 110, vK);
  const vBob = Math.abs(Math.sin(t * 7)) * 3 * (1 - vK);

  // dark：8 个光点亮起
  const pointsP = mode === "dark" ? ease(span(p, 0.35, 0.85)) : 0;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: "50%", top: "50%", width: W, height: H, transform: `translate(-50%, -50%) scale(${s})` }}>
        <div style={{ position: "absolute", inset: 0, opacity: sceneO, transform: `translate(${cam.ox}px, ${cam.oy}px) scale(${cam.sc})`, transformOrigin: cam.origin }}>
          {/* 天 */}
          <div style={{ position: "absolute", inset: 0, background: `linear-gradient(180deg, ${skyTop} 0%, ${skyMid} 52%, ${skyHorizon} 74%, ${skyHorizon} 100%)` }} />
          {/* 太阳 / 月：黄昏时压在地平线上 */}
          {night < 0.5 ? (
            <>
              <div style={{ position: "absolute", left: 960 - 520, top: GROUND - 560, width: 1040, height: 700, borderRadius: "50%", background: "radial-gradient(closest-side, rgba(255,190,120,0.35) 0%, rgba(255,150,90,0.12) 50%, rgba(255,150,90,0) 100%)" }} />
              <div style={{ position: "absolute", left: 960 - 130, top: GROUND - 360, width: 260, height: 260, borderRadius: 130, background: "radial-gradient(circle, rgba(255,222,160,0.98) 0%, rgba(255,176,96,0.6) 42%, rgba(255,150,80,0) 70%)", filter: "blur(2px)" }} />
            </>
          ) : (
            <div style={{ position: "absolute", left: 1500, top: 120, width: 60, height: 60, borderRadius: 30, background: "radial-gradient(circle, #f6f2e7 0%, #cfd6e6 60%, rgba(0,0,0,0) 72%)", opacity: 0.85, filter: "blur(0.5px)", boxShadow: "0 0 60px rgba(220,228,245,0.25)" }} />
          )}
          <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
            <defs>
              <filter id="ss-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="24" />
              </filter>
              <filter id="ss-glow-s" x="-300%" y="-300%" width="700%" height="700%">
                <feGaussianBlur stdDeviation="7" />
              </filter>
              <filter id="ss-blur" x="-30%" y="-100%" width="160%" height="300%">
                <feGaussianBlur stdDeviation="12" />
              </filter>
              <linearGradient id="ss-cone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="rgba(255,224,170,0.5)" />
                <stop offset="1" stopColor="rgba(255,224,170,0)" />
              </linearGradient>
              <linearGradient id="ss-haze" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="rgba(255,170,100,0)" />
                <stop offset="1" stopColor={night > 0.5 ? "rgba(120,110,170,0.18)" : "rgba(255,170,100,0.26)"} />
              </linearGradient>
            </defs>

            {/* 夜里的星 / 黄昏的云带 */}
            {night > 0.5
              ? stars.map((st, i) => <circle key={i} cx={st.x} cy={st.y} r={st.r} fill="#e8ecf6" opacity={0.25 + 0.35 * (0.5 + 0.5 * Math.sin(t * 1.3 + st.ph))} />)
              : [0, 1, 2, 3].map((i) => (
                  <ellipse
                    key={i}
                    cx={260 + i * 470 + Math.sin(t * 0.2 + i) * 20}
                    cy={300 + i * 38}
                    rx={360 - i * 40}
                    ry={14 + i * 3}
                    fill={i % 2 ? "rgba(255,170,120,0.28)" : "rgba(255,140,120,0.22)"}
                    filter="url(#ss-blur)"
                  />
                ))}

            {/* 远处的楼：剪影 + 几扇亮窗 */}
            {Array.from({ length: 16 }, (_, i) => {
              const rnd = mulberry32(300 + i);
              const bw = 90 + rnd() * 120;
              const bx = -40 + i * 125 + rnd() * 20;
              const bh = 140 + rnd() * 220;
              return (
                <g key={i}>
                  <rect x={bx} y={GROUND - 120 - bh} width={bw} height={bh + 120} fill={night > 0.5 ? "#070a14" : "#2a1f3b"} opacity={0.95} />
                  {Array.from({ length: 6 }, (_, k) => (
                    <rect key={k} x={bx + 14 + (k % 3) * (bw / 3)} y={GROUND - 100 - bh + 24 + Math.floor(k / 3) * 46} width={9} height={12} fill="rgba(255,210,140,0.6)" opacity={rnd() > 0.45 ? 0.3 + 0.7 * night : 0.08} />
                  ))}
                </g>
              );
            })}
            {/* 地平线上的雾 */}
            <rect x={0} y={GROUND - 170} width={W} height={170} fill="url(#ss-haze)" />
            {/* 地 */}
            <rect x={0} y={GROUND} width={W} height={H - GROUND} fill={night > 0.5 ? "#05070d" : "#100d1a"} />
            <line x1={0} y1={GROUND} x2={W} y2={GROUND} stroke="rgba(255,255,255,0.08)" />

            {/* 两家店 */}
            <Shop x={SHOP_L.x} w={SHOP_L.w} lit={night > 0.5 ? 0.35 : 0.75} night={night} busy />
            <Shop x={SHOP_R.x} w={SHOP_R.w} lit={night > 0.5 ? 1 : 0.85} night={night} busy={false} />

            {/* 路灯：两家店中间一盏，右边一盏 */}
            <Lamp x={905} on={lampOn} />
            <Lamp x={1810} on={lampOn} flip />

            {/* 队伍的影子 */}
            {night < 0.5
              ? queue.map((q, i) => <ellipse key={`s${i}`} cx={q.x + shadowLen * 0.5} cy={GROUND + 6} rx={shadowLen * 0.5 + 14} ry={9} fill="rgba(0,0,0,0.45)" />)
              : null}
            {/* 队伍 */}
            {queue.map((q, i) => (
              <Person
                key={i}
                x={q.x + Math.sin(t * q.sp + q.ph) * 1.5}
                y={GROUND}
                h={q.h}
                sway={Math.sin(t * q.sp * 0.7 + q.ph) * 1.2}
                rim={night > 0.5 ? "rgba(180,200,240,0.35)" : undefined}
                phone={q.phone * (0.6 + 0.4 * Math.sin(t * 2 + q.ph))}
              />
            ))}

            {/* 回场：一个人走过来停下 */}
            {mode === "visitor" ? (
              <g>
                <ellipse cx={vX} cy={GROUND + 6} rx={26} ry={8} fill="rgba(0,0,0,0.45)" />
                <Person x={vX} y={GROUND - vBob} h={1.02} rim="rgba(255,196,120,0.85)" />
              </g>
            ) : null}
          </svg>
        </div>

        {/* dark：暗场里的 8 个光点 */}
        {mode === "dark"
          ? Array.from({ length: 8 }, (_, i) => {
              const k = ease(span(pointsP, i / 8, i / 8 + 0.35));
              return <div key={i} style={{ position: "absolute", left: 560 + i * 114, top: 520, width: 14, height: 14, borderRadius: 7, background: C.gold, opacity: k, boxShadow: `0 0 ${20 * k}px ${C.gold}` }} />;
            })
          : null}

        {/* 大字 */}
        {line ? (
          <div style={{ position: "absolute", left: 120, right: 120, top: mode === "shadow" ? 150 : 170, textAlign: "center", fontFamily: FONT, fontWeight: 700, fontSize: 78, lineHeight: 1.4, letterSpacing: 4, color: C.ink, opacity: lineP, transform: `translateY(${(1 - lineP) * 18}px)`, textShadow: "0 0 50px rgba(0,0,0,0.9), 0 4px 24px rgba(0,0,0,0.95)" }}>
            {line}
          </div>
        ) : null}

        {/* 片名 */}
        {title ? (
          <div style={{ position: "absolute", left: 100, right: 100, top: 230, textAlign: "center" }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 112, lineHeight: 1.3, letterSpacing: 6, color: C.ink, opacity: titleP, filter: `blur(${(1 - titleP) * 8}px)`, textShadow: "0 0 90px rgba(243,193,75,0.25), 0 6px 40px rgba(0,0,0,0.95)" }}>{title}</div>
            <div style={{ margin: "26px auto 0", width: 520 * titleP, height: 1, background: `linear-gradient(90deg, rgba(243,193,75,0) 0%, ${C.gold} 50%, rgba(243,193,75,0) 100%)`, opacity: 0.85 }} />
          </div>
        ) : null}

        <Note text={note} p={span(p, 0.2, 0.45)} />
      </div>
    </AbsoluteFill>
  );
};
