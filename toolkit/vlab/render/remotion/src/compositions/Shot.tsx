import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { CARDS } from "../cards/registry";
import { C, FONT } from "../design/tokens";
import { FXLayer, GlobalFX } from "../fx/GlobalFX";

export type ShotProps = {
  /** 卡名（见 cards/registry.ts） */
  card: string;
  /** 卡组件的 props，原样透传 */
  params?: Record<string, unknown>;
  durationInFrames: number;
  /** 帧率；PREVIEW=1 时 build 会传 15 */
  fps?: number;
  /** 画幅；由 Python 桥按工程传，不传就用 tokens 里的默认值 */
  width?: number;
  height?: number;
  /** 逐层开关全局特效；字幕条默认关（字幕由 finalize 烧 ASS）。
   *  dipIn / dipOut / dipFrames 不是开关而是数值，一并放在 fx 里，yaml 一处配完 */
  fx?: Partial<Record<FXLayer, boolean>> & { dipIn?: number; dipOut?: number; dipFrames?: number };
  /** 本镜在全片的起始帧（build 传）：背景层用它计时，切镜时背景不动 */
  t0?: number;
  /** 角标文字，如视频编号 */
  brand?: string;
  slug?: string;
};

const Missing: React.FC<{ card: string }> = ({ card }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, 12], [0, 1], { easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: p }}>
      <div style={{ fontFamily: FONT, fontSize: 40, color: C.red }}>未知镜头卡：{card}</div>
      <div style={{ fontFamily: FONT, fontSize: 24, color: C.dim, marginTop: 16 }}>
        已在 cards/registry.ts 登记？
      </div>
    </AbsoluteFill>
  );
};

/**
 * 单镜头容器：给 Python 桥用。一个 Shot 组合 = 一张卡 + 一组参数 + 全局特效栈，
 * 这样 15 个分镜不需要 15 个 Composition，videokit 只按 card/params 出片。
 */
export const Shot: React.FC<ShotProps> = ({
  card,
  params,
  fx,
  t0 = 0,
  brand = "VIBE / 涌现",
  slug = "005",
}) => {
  const { dipIn, dipOut, dipFrames, ...layers } = fx ?? {};
  const Comp = CARDS[card];
  return (
    <GlobalFX
      // 不再每镜闪白：45 次白闪就是频闪。章节切换用 dip（压暗），配置在 project.yaml
      shotStarts={[]}
      layers={{ subtitleBar: false, ...layers }}
      t0={t0}
      dipIn={dipIn}
      dipOut={dipOut}
      dipFrames={dipFrames}
      brand={brand}
      slug={slug}
    >
      {Comp ? <Comp {...(params ?? {})} /> : <Missing card={card} />}
    </GlobalFX>
  );
};
