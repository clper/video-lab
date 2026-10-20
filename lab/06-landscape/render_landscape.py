"""程序化风景测试：日落湖景（山、水、鹿、雁群、跃鱼）。

渲染代码在 vlab/scenes/landscape.py（003 的结尾也复用它），这里只负责把成片输出到本目录的 renders/。

用法（任意目录）:
    uv run python lab/06-landscape/render_landscape.py              # → lab/06-landscape/renders/landscape.mp4
    uv run python lab/06-landscape/render_landscape.py --still 4.8  # 只出一帧 PNG
    uv run python lab/06-landscape/render_landscape.py --fps 15     # 快速预览
"""

from pathlib import Path

from vlab.scenes import landscape

if __name__ == "__main__":
    landscape.main(Path(__file__).resolve().parent / "renders")
