"""项目统一字体：思源黑体 CN（Source Han Sans CN），SIL OFL 1.1，可商用，可随仓库分发。

为什么换掉微软雅黑：它的著作权归方正，微软只取得了预装和使用的授权，无权转授商业发布权，
字库公司在批量维权（来源见 research/content/08-compliance/README.md 第 4 节）。

字体文件在 vlab/assets/fonts/，随仓库入库：克隆即可用，不依赖系统装没装。
来源：https://github.com/adobe-fonts/source-han-sans （release 分支 SubsetOTF/CN，2026-10-23 下载）
许可证：license/OFL-SourceHanSans.txt（SIL Open Font License 1.1；"Source" 是保留字体名，改字体文件才受限，直接用不受影响）

用法:
    from vlab import fonts
    fonts.pil(48, bold=True)        # Pillow 叠字
    fonts.register_manim()          # Manim：scene.py 顶部调用一次，然后 Text(..., font=fonts.FAMILY)
    fonts.DIR                       # ffmpeg 字幕滤镜（libass）的 fontsdir
"""

from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FAMILY = "Source Han Sans CN"
REGULAR = DIR / "SourceHanSansCN-Regular.otf"
BOLD = DIR / "SourceHanSansCN-Bold.otf"
LICENSE = DIR / "license" / "OFL-SourceHanSans.txt"   # 放子目录：libass 会把 fontsdir 里每个文件都当字体试一遍


@lru_cache(maxsize=64)
def pil(size: int, bold: bool = False):
    """Pillow 字体对象（带缓存，逐帧叠字时不会重复加载）。"""
    from PIL import ImageFont

    return ImageFont.truetype(str(BOLD if bold else REGULAR), size)


_registered = False


def register_manim() -> str:
    """把常规体和粗体注册给 Manim（manimpango），只在本进程有效，不用装进系统。返回族名。

    注册后 Text(..., font=FAMILY, weight=BOLD) 会自动选到粗体文件。
    注册失败时直接报错：Manim 找不到字体会悄悄换成别的字体，画面看着正常但字体错了。
    """
    global _registered
    if _registered:
        return FAMILY
    import manimpango

    for p in (REGULAR, BOLD):
        if not p.exists():
            raise FileNotFoundError(f"缺字体文件 {p}；它应该随仓库一起入库")
        if not manimpango.register_font(str(p)):
            raise RuntimeError(f"Manim 注册字体失败：{p}")
    if FAMILY not in manimpango.list_fonts():
        raise RuntimeError(f"注册后 Manim 仍找不到字体族 {FAMILY!r}")
    _registered = True
    return FAMILY
