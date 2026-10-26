import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../design/tokens";
import { useStage } from "../common/stage";
import { clamp, lerp, mulberry32 } from "../common/random";
import { N_SONGS, N_WORLDS, appealHeights, heightsOf, makeWorlds } from "../lib/worlds";
import { Badge, Note, Panel, Ring, TopLight, ease, span } from "../lib/boardDraw";

// 8 块世界板的总览：008《你没火，可能只是没被选中》的主画面。
// 一块板 = 一个世界，板上 48 颗光点 = 48 首歌；看得到下载数的世界里，光点长成高低不同的光柱。
// 所有数字来自 lib/worlds.ts 的模拟（片中标"示意"），那首"第 1 名 / 第 40 名"的歌是论文作者讲过的原例。

export type BoardsMode =
  | "inflow"        // 一万四千多人涌进来，计数器滚到 count
  | "songs"         // 48 颗光点排成一行逐颗点亮
  | "boards"        // 8 块板出现，人流分成 8 股，每颗光点下的下载数都是 0
  | "control"       // 8 块板让到左边，右边亮起对照组（冷色）
  | "ruler"         // 对照组的光点按"本来有多好"排成一把尺子
  | "grow"          // 8 块板的光点开始长成光柱（还看不出差别）
  | "guess"         // 直觉：每块板上画出同一条虚线轮廓
  | "diverge"       // 虚线碎掉，各板长出不同的最高柱
  | "champion"      // 推近一块板：中等的那首歌冲到第 1
  | "loser"         // 推近另一块板：同一首歌排在第 40
  | "compare"       // 逐块和对照组比：块块更陡，8 / 8
  | "unpredictable" // 各板冠军的位置各不相同，依次闪
  | "glide"         // 呼吸镜：贴着光柱掠过
  | "final"         // 8 块板的最终结果
  | "best"          // 最好的几首套金圈
  | "worst"         // 最差的几首套灰圈
  | "youdot";       // 你是板上的一颗点

type Props = {
  mode?: BoardsMode;
  count?: number;
  label?: string;
  note?: string;
  badge?: string;
  push?: boolean;
  tint?: "gold" | "none";
};

const W = 1920;
const H = 1080;
const PW = 392;
const PH = 330;
const GAP_X = 53;
const X0 = 96;
const Y0 = 130;
const Y1 = 530;

const gridPos = (w: number) => ({ x: X0 + (w % 4) * (PW + GAP_X), y: w < 4 ? Y0 : Y1 });

/** 对照组在右边时，8 块板缩到左边 */
const sidePos = (w: number) => ({ x: 60 + (w % 4) * (PW * 0.72 + 30), y: (w < 4 ? 190 : 530) });

export const WorldBoards: React.FC<Props> = ({
  mode = "final",
  count = 14341,
  label = "",
  note = "",
  badge = "",
  push = false,
  tint = "none",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { s } = useStage();
  const p = clamp(frame / Math.max(1, durationInFrames - 1));
  const data = makeWorlds();
  const appeal = appealHeights(data);
  const finals = data.downloads.map(heightsOf);
  const ex = data.example;

  // ---------- 每个 mode 的状态 ----------
  const side = mode === "control" || mode === "ruler" || mode === "compare";
  const focus = mode === "champion" ? ex.top : mode === "loser" ? ex.bottom : -1;

  const panelOpacity = (w: number) => {
    if (mode === "inflow" || mode === "songs") return 0;
    if (mode === "boards") return ease(span(p, 0.02 + w * 0.05, 0.3 + w * 0.05));
    if (focus >= 0) return w === focus ? 1 : 0.14;
    if (mode === "youdot") return 0.42 * ease(span(p, 0, 0.5));
    return 1;
  };

  // 光点 → 光柱
  const morph = (() => {
    if (mode === "boards" || mode === "control" || mode === "ruler") return 0;
    if (mode === "grow") return ease(span(p, 0.05, 0.5));
    return 1;
  })();
  const grow = (() => {
    if (mode === "grow") return 0.42 * ease(span(p, 0.3, 1));
    if (mode === "guess") return 0.46;
    if (mode === "diverge") return lerp(0.46, 1, ease(span(p, 0.15, 0.8)));
    if (mode === "boards" || mode === "control" || mode === "ruler") return 0;
    return 1;
  })();

  // 柱高：直觉阶段大家一样（appeal），反转后各是各的
  const heightsFor = (w: number): number[] => {
    if (mode === "grow" || mode === "guess") return appeal;
    if (mode === "diverge") {
      const k = ease(span(p, 0.15, 0.8));
      return appeal.map((a, i) => lerp(a, finals[w][i], k));
    }
    if (mode === "champion" && w === ex.top) {
      const k = ease(span(p, 0.18, 0.7));
      return finals[w].map((h, i) => (i === ex.song ? lerp(appeal[i], h, k) : h));
    }
    return finals[w];
  };

  // 相机：champion / loser 推近那块板；glide 贴着上排掠过；final 可以缓推
  const cam = (() => {
    if (focus >= 0) {
      const g = gridPos(focus);
      const k = ease(span(p, 0, 0.55));
      const sc = lerp(1, 1.85, k);
      const cx = g.x + PW / 2;
      const cy = g.y + PH / 2 + 30;
      return { sc, ox: lerp(0, W / 2 - cx, k), oy: lerp(0, H / 2 - cy, k), origin: `${cx}px ${cy}px` };
    }
    if (mode === "glide") {
      const sc = 2.3;
      return { sc, ox: lerp(760, -760, p), oy: 300, origin: "960px 540px" };
    }
    if (mode === "final" && push) return { sc: 1 + 0.07 * p, ox: 0, oy: 0, origin: "960px 520px" };
    if (mode === "boards") return { sc: 1.02, ox: lerp(18, -18, p), oy: 0, origin: "960px 540px" };
    return { sc: 1, ox: 0, oy: 0, origin: "960px 540px" };
  })();

  // 圈：最好的 5 首（金）/ 最差的 5 首（灰）
  const ringSongs = mode === "best" ? data.byQuality.slice(0, 5) : mode === "worst" ? data.byQuality.slice(N_SONGS - 5) : [];
  const ringsFor = (w: number): Ring[] =>
    ringSongs.map((song, k) => ({ song, color: mode === "best" ? C.gold : "#9aa3b5", p: span(p, 0.15 + k * 0.06 + w * 0.025, 0.45 + k * 0.06 + w * 0.025) }));

  // 徽章
  const badgesFor = (w: number): Badge[] => {
    if (mode === "champion" && w === ex.top) return [{ song: ex.song, text: badge || "第 1 名", color: C.gold, p: span(p, 0.68, 0.9) }];
    if (mode === "loser" && w === ex.bottom) return [{ song: ex.song, text: badge || "第 40 名 / 48", color: "#aeb6c6", p: span(p, 0.35, 0.65) }];
    return [];
  };

  // 高亮：那首中等的歌 / 你那颗点
  const hiFor = (w: number) => {
    if ((mode === "champion" && w === ex.top) || (mode === "loser" && w === ex.bottom)) return { song: ex.song, color: C.gold, glow: 1 };
    if (mode === "youdot" && w === 5) return { song: 21, color: C.cyan, glow: 1 + 0.6 * Math.sin(frame / 5) };
    if (mode === "unpredictable") {
      const k = span(p, 0.05 + w * 0.1, 0.25 + w * 0.1);
      if (k > 0 && k < 1) {
        const top = finals[w].indexOf(Math.max(...finals[w]));
        return { song: top, color: C.gold, glow: 1.6 * Math.sin(k * Math.PI) };
      }
    }
    return null;
  };

  // 压暗别的歌（champion / loser 只看那一首）
  const dimFor = (w: number) => {
    if ((mode === "champion" && w === ex.top) || (mode === "loser" && w === ex.bottom)) return new Array(N_SONGS).fill(0.45);
    return undefined;
  };

  // 虚线轮廓：guess 画出来，diverge 碎掉
  const dashedFor = () => {
    if (mode === "guess") return { heights: appeal, p: ease(span(p, 0.1, 0.75)) };
    if (mode === "diverge") return { heights: appeal, p: 1, shatter: ease(span(p, 0.05, 0.5)) };
    return null;
  };

  // compare：扫过 8 块板，比完一块亮一格
  const compared = mode === "compare" ? Math.floor(span(p, 0.1, 0.82) * N_WORLDS + 1e-6) : 0;
  const comparing = mode === "compare" ? Math.min(N_WORLDS - 1, compared) : -1;

  // inflow 的人流 / boards 的 8 股人流
  const flow = React.useMemo(() => {
    const rnd = mulberry32(20261026);
    return Array.from({ length: 760 }, (_, i) => {
      const side = Math.floor(rnd() * 4);
      const u = rnd();
      const from =
        side === 0 ? { x: -40, y: u * H } : side === 1 ? { x: W + 40, y: u * H } : side === 2 ? { x: u * W, y: -40 } : { x: u * W, y: H + 40 };
      const a = rnd() * Math.PI * 2;
      const r = 40 + rnd() * 250;
      return { from, to: { x: 960 + Math.cos(a) * r * 1.5, y: 540 + Math.sin(a) * r * 0.75 }, delay: rnd() * 0.55, size: 1.6 + rnd() * 2.2, world: i % N_WORLDS, lane: rnd() };
    });
  }, []);

  const counterVal = Math.round(count * ease(span(p, 0.08, 0.78)));

  // 对照组板
  const ctrlX = 1400;
  const ctrlY = 330;
  const ctrlHeights = (() => {
    if (mode === "ruler") return [...appeal].sort((a, b) => b - a);
    return appeal;
  })();
  const ctrlMorph = mode === "ruler" ? ease(span(p, 0.08, 0.55)) : 0;
  const ctrlGrow = mode === "ruler" ? ease(span(p, 0.3, 0.9)) : 0;
  const ctrlOpacity = mode === "control" ? ease(span(p, 0.15, 0.6)) : 1;

  const goldTint = tint === "gold" || mode === "glide";

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: "50%", top: "50%", width: W, height: H, transform: `translate(-50%, -50%) scale(${s})` }}>
        <TopLight cx={960} cy={120} strength={mode === "inflow" || mode === "songs" ? 0.6 : 1} />

        <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transform: `translate(${cam.ox}px, ${cam.oy}px) scale(${cam.sc})`, transformOrigin: cam.origin }}>
          <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
            {/* 人流：inflow 从四边涌向中间；boards 从板顶落进 8 块板 */}
            {mode === "inflow"
              ? flow.map((f, i) => {
                  const k = ease(span(p * 1.25, f.delay, f.delay + 0.5));
                  if (k <= 0) return null;
                  return <circle key={i} cx={lerp(f.from.x, f.to.x, k)} cy={lerp(f.from.y, f.to.y, k)} r={f.size} fill={C.ink} opacity={0.25 + 0.55 * k} />;
                })
              : null}
            {mode === "boards"
              ? flow.slice(0, 480).map((f, i) => {
                  const g = gridPos(f.world);
                  const k = span(p, 0.08 + f.delay * 0.9, 0.5 + f.delay * 0.9);
                  if (k <= 0 || k >= 1) return null;
                  const x0 = 960 + (f.lane - 0.5) * 300;
                  const x1 = g.x + 24 + f.lane * (PW - 48);
                  const y1 = g.y + 36 + (f.size - 1.6) * 90;
                  const kk = ease(k);
                  return <circle key={i} cx={lerp(x0, x1, kk)} cy={lerp(-30, y1, kk)} r={1.8} fill={C.ink} opacity={0.7 * (1 - k)} />;
                })
              : null}

            {/* 48 颗光点排成一行（songs） */}
            {mode === "songs"
              ? Array.from({ length: N_SONGS }, (_, i) => {
                  const k = span(p, 0.05 + (i / N_SONGS) * 0.7, 0.12 + (i / N_SONGS) * 0.7);
                  const x = 200 + (i / (N_SONGS - 1)) * 1520;
                  return (
                    <g key={i}>
                      <circle cx={x} cy={560} r={7 + 3 * ease(k)} fill={ease(k) > 0 ? C.ink : "rgba(226,236,248,0.18)"} opacity={0.25 + 0.7 * ease(k)} style={ease(k) > 0.9 ? { filter: "drop-shadow(0 0 8px rgba(246,242,231,0.7))" } : undefined} />
                      <line x1={x} y1={590} x2={x} y2={604} stroke="rgba(226,236,248,0.25)" strokeWidth={1} />
                    </g>
                  );
                })
              : null}

            {/* 8 块板 */}
            {mode !== "inflow" && mode !== "songs"
              ? Array.from({ length: N_WORLDS }, (_, w) => {
                  const g = side ? sidePos(w) : gridPos(w);
                  const pw = side ? PW * 0.72 : PW;
                  const ph = side ? PH * 0.82 : PH;
                  const isComparing = w === comparing && compared < N_WORLDS;
                  const done = mode === "compare" && w < compared;
                  return (
                    <g key={w}>
                      {isComparing ? <rect x={g.x - 6} y={g.y - 6} width={pw + 12} height={ph + 12} rx={14} fill="none" stroke={C.cyan} strokeWidth={2} opacity={0.8} /> : null}
                      <Panel
                        x={g.x}
                        y={g.y}
                        w={pw}
                        h={ph}
                        heights={heightsFor(w)}
                        morph={morph}
                        grow={grow}
                        opacity={panelOpacity(w) * (mode === "compare" && !done && !isComparing ? 0.55 : 1)}
                        tone={goldTint ? "warm" : "warm"}
                        counters={mode === "boards" ? new Array(N_SONGS).fill(0) : null}
                        counterSize={11}
                        dashed={dashedFor()}
                        rings={ringsFor(w)}
                        badges={badgesFor(w)}
                        highlight={hiFor(w)}
                        dim={dimFor(w)}
                        tag={`${w + 1}`}
                        shimmer={mode === "final" || mode === "glide" || mode === "best" || mode === "worst" ? 1 : 0}
                        seed={w + 1 + frame * 0.03}
                      />
                      {done ? (
                        <text x={g.x + pw - 12} y={g.y + ph - 10} textAnchor="end" fontFamily={FONT} fontSize={18} fill={C.cyan} opacity={0.9}>
                          ✓
                        </text>
                      ) : null}
                    </g>
                  );
                })
              : null}

            {/* 对照组 */}
            {side ? (
              <Panel
                x={ctrlX}
                y={ctrlY}
                w={PW}
                h={PH}
                heights={ctrlHeights}
                morph={mode === "compare" ? 1 : ctrlMorph}
                grow={mode === "compare" ? 1 : ctrlGrow}
                opacity={ctrlOpacity}
                tone="cool"
                counters={null}
                label={mode === "compare" ? "" : label}
                tag=""
              />
            ) : null}
            {/* 尺子：对照组排好之后底下一条刻度 */}
            {mode === "ruler" && ctrlGrow > 0.2 ? (
              <g opacity={ease(span(p, 0.45, 0.8))}>
                <line x1={ctrlX + 20} y1={ctrlY + PH - 14} x2={ctrlX + PW - 20} y2={ctrlY + PH - 14} stroke={C.cyan} strokeWidth={1} opacity={0.7} />
                {Array.from({ length: 9 }, (_, k) => (
                  <line key={k} x1={ctrlX + 20 + (k * (PW - 40)) / 8} y1={ctrlY + PH - 14} x2={ctrlX + 20 + (k * (PW - 40)) / 8} y2={ctrlY + PH - 8} stroke={C.cyan} strokeWidth={1} opacity={0.7} />
                ))}
                <text x={ctrlX + 20} y={ctrlY + PH + 12} fontFamily={FONT} fontSize={13} fill={C.cyan} opacity={0.8}>
                  好
                </text>
                <text x={ctrlX + PW - 20} y={ctrlY + PH + 12} textAnchor="end" fontFamily={FONT} fontSize={13} fill={C.cyan} opacity={0.8}>
                  差
                </text>
              </g>
            ) : null}

            {/* 你那颗点：往外扩的涟漪 */}
            {mode === "youdot"
              ? [0, 1, 2].map((k) => {
                  const g = gridPos(5);
                  const slot = (PW - 40) / N_SONGS;
                  const cx = g.x + 20 + slot * 21.5;
                  const cy = g.y + PH - 26 - (PH - 70) * finals[5][21];
                  const u = ((frame / fps) * 0.5 + k / 3) % 1;
                  return <circle key={k} cx={cx} cy={cy} r={8 + u * 70} fill="none" stroke={C.cyan} strokeWidth={1.5} opacity={(1 - u) * 0.7 * ease(span(p, 0.2, 0.5))} />;
                })
              : null}
          </svg>
        </div>

        {/* inflow 的计数器 */}
        {mode === "inflow" ? (
          <div style={{ position: "absolute", left: 0, right: 0, top: 400, textAlign: "center" }}>
            <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 170, lineHeight: 1, color: C.gold, fontVariantNumeric: "tabular-nums", textShadow: "0 0 70px rgba(243,193,75,0.35)", opacity: ease(span(p, 0.05, 0.3)) }}>
              {counterVal.toLocaleString("en-US")}
            </div>
            <div style={{ fontFamily: FONT, fontSize: 30, letterSpacing: 10, color: C.ink, marginTop: 18, opacity: 0.85 * ease(span(p, 0.3, 0.6)) }}>人</div>
          </div>
        ) : null}

        {/* songs 的计数 */}
        {mode === "songs" ? (
          <div style={{ position: "absolute", left: 0, right: 0, top: 330, textAlign: "center", fontFamily: FONT, fontWeight: 700, fontSize: 150, lineHeight: 1, color: C.ink, fontVariantNumeric: "tabular-nums", textShadow: "0 0 50px rgba(246,242,231,0.25)", opacity: ease(span(p, 0.04, 0.2)) }}>
            {Math.round(N_SONGS * clamp(span(p, 0.05, 0.75)))}
          </div>
        ) : null}

        {/* compare 的 k / 8 */}
        {mode === "compare" ? (
          <div style={{ position: "absolute", left: 60, right: 460, top: 70, textAlign: "center", fontFamily: FONT, fontWeight: 700, fontSize: 56, color: compared >= N_WORLDS ? C.gold : C.ink, fontVariantNumeric: "tabular-nums", letterSpacing: 4, textShadow: compared >= N_WORLDS ? "0 0 40px rgba(243,193,75,0.5)" : "none" }}>
            {Math.min(N_WORLDS, compared)} / 8
          </div>
        ) : null}

        <Note text={note} p={span(p, 0.25, 0.5)} />
      </div>
    </AbsoluteFill>
  );
};
