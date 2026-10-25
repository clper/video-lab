// 把仓库自带的思源黑体同步到 Remotion 的 public/fonts/。
// 字体正本在 toolkit/vlab/assets/fonts/，这里只是渲染时需要一份可被浏览器访问的副本，不入库。
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../../assets/fonts");
const dst = resolve(here, "../public/fonts");
mkdirSync(dst, { recursive: true });

for (const f of ["SourceHanSansCN-Regular.otf", "SourceHanSansCN-Bold.otf"]) {
  const s = resolve(src, f);
  if (existsSync(s)) {
    copyFileSync(s, resolve(dst, f));
    console.log("[fonts] copied", f);
  } else {
    console.warn("[fonts] missing", s, "—— 仓库字体应当随仓库入库");
  }
}
