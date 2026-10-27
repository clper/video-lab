"""快速看动作：不走 Remotion，用 Pillow 把指定时刻的骨架画成一张拼图（几秒出图，改关键帧时用）。"""
from PIL import Image, ImageDraw

from vlab import fonts

BONES = [(0, 1), (1, 3), (3, 4), (1, 5), (5, 6), (0, 7), (7, 8), (0, 9), (9, 10)]
BACK = {(1, 5), (5, 6), (0, 9), (9, 10)}


def sheet(data, times, out, cols=4, scale=0.36, onion=0):
    """times：真实时间（秒）。onion>0 时每格再叠画前几帧的淡影，看动作的轨迹和速度"""
    fps = data["fps"]
    W, H = int(1920 * scale), int(1080 * scale)
    rows = (len(times) + cols - 1) // cols
    img = Image.new("RGB", (cols * W, rows * H), "#06070d")
    font = fonts.pil(18)
    for k, t in enumerate(times):
        f = min(data["frames"] - 1, round(t * fps))
        cx, cy, z = data["camera"][f]
        tile = Image.new("RGB", (W, H), "#06070d")      # 每格单独画再贴，越界的线不会画到隔壁格
        ox, oy = 0, 0

        def P(x, y):
            return ox + ((x - cx) * z + 960) * scale, oy + ((y - cy) * z + 540) * scale

        d = ImageDraw.Draw(tile)
        g = data["ground"]
        d.line([P(-2000, g), P(4000, g)], fill="#3a4152", width=2)
        for w in data.get("walls", []):
            d.line([P(w["x"], w["y0"]), P(w["x"], w["y1"])], fill="#8b93a7", width=3)
        for p in data.get("paths", []):
            if f >= p["f0"]:
                pts = [P(*q) for q in p["pts"]]
                d.line(pts, fill="#2c6f68", width=1)
        for gh in data.get("ghosts", []):
            for fa, x, y in gh["pts"]:
                if f >= fa:
                    r = gh["r"] * z * scale
                    X, Y = P(x, y)
                    d.ellipse([X - r, Y - r, X + r, Y + r], outline="#2c8f86")
        for b in data.get("balls", []):
            q = b["p"][f]
            if q:
                r = b["r"] * z * scale
                X, Y = P(q[0], q[1])
                d.ellipse([X - r, Y - r, X + r, Y + r], fill=b["color"])
        for fig in data["figures"]:
            for back in range(onion, -1, -1):
                ff = max(0, f - back * 2)
                j = fig["j"][ff]
                pts = [P(j[2 * i], j[2 * i + 1]) for i in range(11)]
                shade = 1.0 if back == 0 else 0.25
                for a, b in BONES:
                    c = fig["color"] if (a, b) not in BACK else "#7d6a3a" if fig["color"] == "#f3c14b" else "#2f8077"
                    col = _mix(c, shade)
                    d.line([pts[a], pts[b]], fill=col, width=max(1, int(fig["width"] * z * scale)))
                r = fig["headR"] * z * scale
                X, Y = pts[2]
                d.ellipse([X - r, Y - r, X + r, Y + r], fill=_mix(fig["color"], shade))
        d.text((8, 6), f"{t:.2f}s", fill="#8b93a7", font=font)
        d.rectangle([0, 0, W - 1, H - 1], outline="#1c2233")
        img.paste(tile, ((k % cols) * W, (k // cols) * H))
    img.save(out)
    return out


def _mix(hex_color, k):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    bg = (6, 7, 13)
    return tuple(int(bg[i] + ([r, g, b][i] - bg[i]) * k) for i in range(3))
