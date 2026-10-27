import React from "react";
import { ChartCard } from "./ChartCard";
import { CountUp } from "./CountUp";
import { Flock } from "./Flock";
import { FoldCount } from "./FoldCount";
import { FoldCross } from "./FoldCross";
import { FoldCurve } from "./FoldCurve";
import { FoldFormula } from "./FoldFormula";
import { FoldGalaxy } from "./FoldGalaxy";
import { FoldLimit } from "./FoldLimit";
import { FoldPage } from "./FoldPage";
import { FoldPile } from "./FoldPile";
import { FoldRuler } from "./FoldRuler";
import { FoldSheet } from "./FoldSheet";
import { FoldTitle } from "./FoldTitle";
import { Gallivan } from "./Gallivan";
import { GlitchText } from "./GlitchText";
import { KineticSubtitle } from "./KineticSubtitle";
import { LifeGame } from "./LifeGame";
import { LineGrow } from "./LineGrow";
import { MaskWipe } from "./MaskWipe";
import { Nebula3D } from "./Nebula3D";
import { ParticleText } from "./ParticleText";
import { GaltonBoard } from "./GaltonBoard";
import { RegressTitle } from "./RegressTitle";
import { BriefRoom } from "./BriefRoom";
import { ScatterRegress } from "./ScatterRegress";
import { WaveField } from "./WaveField";
import { StreetScene } from "./StreetScene";
import { WorldBoards } from "./WorldBoards";
import { WorldBoard } from "./WorldBoard";
import { LifeCounters } from "./LifeCounters";
import { PaperLength } from "./PaperLength";
import { PaperRoll } from "./PaperRoll";
import { Polaroid } from "./Polaroid";
import { ScaleCard } from "./ScaleCard";
import { StampStrike } from "./StampStrike";
import { StickScene } from "./StickScene";
import { TechCard } from "./TechCard";
import { VortexBlocks } from "./VortexBlocks";

// 镜头卡注册表：Python 侧只认这里的名字（remotion_bridge.py 会解析这个文件校验卡名）。
// 新增卡只需在 cards/ 写组件 + 在这里登记一行。
export const CARDS: Record<string, React.ComponentType<any>> = {
  particleText: ParticleText,
  kineticSubtitle: KineticSubtitle,
  countUp: CountUp,
  techCard: TechCard,
  lineGrow: LineGrow,
  polaroid: Polaroid,
  maskWipe: MaskWipe,
  glitchText: GlitchText,
  nebula3d: Nebula3D,
  vortexBlocks: VortexBlocks,
  lifeGame: LifeGame,
  scaleCard: ScaleCard,
  stampStrike: StampStrike,
  flock: Flock,
  chartCard: ChartCard,
  foldSheet: FoldSheet,
  foldPage: FoldPage,
  foldLimit: FoldLimit,
  foldCross: FoldCross,
  foldCount: FoldCount,
  foldPile: FoldPile,
  foldRuler: FoldRuler,
  foldFormula: FoldFormula,
  paperLength: PaperLength,
  gallivan: Gallivan,
  paperRoll: PaperRoll,
  foldGalaxy: FoldGalaxy,
  foldCurve: FoldCurve,
  foldTitle: FoldTitle,
  galtonBoard: GaltonBoard,
  regressTitle: RegressTitle,
  briefRoom: BriefRoom,
  scatterRegress: ScatterRegress,
  waveField: WaveField,
  // 008《你没火，可能只是没被选中》
  streetScene: StreetScene,
  worldBoards: WorldBoards,
  worldBoard: WorldBoard,
  lifeCounters: LifeCounters,
  // research/visual/15-stickfigure：火柴人场景播放器（动作数据由 Python 算好传进来）
  stickScene: StickScene,
};

export const CARD_NAMES = Object.keys(CARDS);
