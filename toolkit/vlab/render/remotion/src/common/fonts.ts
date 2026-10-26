import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";
import { FONT } from "../design/tokens";

// 引入即开始加载。loadFont 内部用 delayRender 等字体真正可用后才截帧，
// 避免"字体悄悄回退"的假象。字体副本由 scripts/sync-fonts.mjs 放到 public/fonts/。
loadFont({
  family: FONT,
  url: staticFile("fonts/SourceHanSansCN-Regular.otf"),
  weight: "400",
});

loadFont({
  family: FONT,
  url: staticFile("fonts/SourceHanSansCN-Bold.otf"),
  weight: "700",
});
