# 005 的 Remotion 部分

这一版**没有**在项目里复制一份镜头卡代码——卡片全部住在公共能力库：

```
toolkit/vlab/render/remotion/src/
├── cards/          15 张镜头卡（flock / lifeGame / lineGrow / techCard / …）
├── fx/GlobalFX.tsx 七层全局特效栈
├── design/tokens.ts 颜色、字体、缓动
└── compositions/Shot.tsx  通用单镜头组合（Python 桥就渲染它）
```

005 只在 `project.yaml` 里写「第几镜、用哪张卡、传什么参数」：

```yaml
  - id: S1
    renderer: remotion
    card: flock
    params: {n: 640, birth: true, seed: 1987}
```

Python 桥（`toolkit/vlab/render/remotion_bridge.py`）把 card + params 写进临时 props 文件，
调一次 `npx remotion render src/index.ts Shot out.mp4 --props=...` 出片。
这么做的好处是 006、007 直接换参数就能复用同一套卡，不用再抄一遍。

为什么不在项目里放 `remotion/`：项目目录只放"这一条片子特有的东西"——文案、着色器、渲染产物。
镜头卡是跨片子的资产，复制出去就会开始漂移（改了 A 忘了 B），所以只留这一个说明文件。

查看可用卡名：

```bash
uv run python -m vlab.render.remotion_bridge --list
```
