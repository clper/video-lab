import React from "react";
import { Sequence } from "remotion";
import { GlobalFX } from "../fx/GlobalFX";
import { ParticleText } from "../cards/ParticleText";
import { TechCard } from "../cards/TechCard";
import { CountUp } from "../cards/CountUp";
import { LineGrow } from "../cards/LineGrow";
import { KineticSubtitle } from "../cards/KineticSubtitle";

// 15 秒验证样片：5 个镜头、5 张卡、7 层全局特效。
// 目的不是讲完一个故事，而是验证"这套观感能不能打"。
const SHOTS = [
  { from: 0, dur: 90 },
  { from: 90, dur: 105 },
  { from: 195, dur: 90 },
  { from: 285, dur: 90 },
  { from: 375, dur: 75 },
];

export const Sample15s: React.FC = () => {
  return (
    <GlobalFX shotStarts={SHOTS.map((s) => s.from)}>
      <Sequence from={SHOTS[0].from} durationInFrames={SHOTS[0].dur}>
        <ParticleText text="涌现" kicker="EMERGENCE" sub="简单规则，长出智能" />
      </Sequence>

      <Sequence from={SHOTS[1].from} durationInFrames={SHOTS[1].dur}>
        <TechCard />
      </Sequence>

      <Sequence from={SHOTS[2].from} durationInFrames={SHOTS[2].dur}>
        <CountUp to={640} label="只鸟" note="0 个指挥" />
      </Sequence>

      <Sequence from={SHOTS[3].from} durationInFrames={SHOTS[3].dur}>
        <LineGrow />
      </Sequence>

      <Sequence from={SHOTS[4].from} durationInFrames={SHOTS[4].dur}>
        <KineticSubtitle
          text="你无法从一只鸟，读出整个鸟群。"
          highlight="整个鸟群"
          charsPerSecond={10}
          footer="EMERGENCE / 未完待续"
        />
      </Sequence>
    </GlobalFX>
  );
};
