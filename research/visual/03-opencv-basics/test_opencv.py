"""OpenCV 基础能力测试

测试 OpenCV 的图像处理和计算机视觉能力：
1. 图像绘制（几何图形、文字）
2. 颜色空间转换（RGB/HSV/Gray）
3. 滤镜（模糊/锐化/中值）
4. 边缘检测（Canny/Sobel/Laplacian）
5. 轮廓检测
6. 阈值处理
7. 形态学操作
8. 特征检测（角点）
9. 视频生成（逐帧合成）

用法：
    python test_opencv.py

输出：
    renders/opencv_demo.mp4
"""

import cv2
import numpy as np
import shutil
import subprocess
from pathlib import Path

# 先找仓库里的 toolkit/bin/ffmpeg.exe（原开发机），没有就用 PATH 上的 ffmpeg
_LOCAL_FFMPEG = Path(__file__).resolve().parents[3] / "toolkit" / "bin" / "ffmpeg.exe"
FFMPEG = str(_LOCAL_FFMPEG) if _LOCAL_FFMPEG.exists() else (shutil.which("ffmpeg") or "ffmpeg")
OUT_DIR = Path(__file__).parent / "renders"
OUT_DIR.mkdir(exist_ok=True)

W, H = 1080, 1920  # 竖屏
FPS = 30

# ---------- 配色 ----------
CYAN = (238, 211, 34)     # BGR
MAGENTA = (249, 121, 233)
GOLD = (36, 191, 251)
GREEN = (128, 222, 74)
PINK = (182, 114, 244)
WHITE = (255, 255, 255)
DIM = (110, 110, 110)
BG = (10, 6, 5)


def text_overlay(frame, text, pos, color=WHITE, scale=1.5, thickness=2):
    """添加中文文字（用 Pillow 更好，但先测试 OpenCV 原生）"""
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def text_cn(frame, text, pos, color=WHITE, font_size=48):
    """添加中文文字（用 Pillow）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)
        except:
            font = ImageFont.load_default()
        draw.text(pos, text, fill=color[::-1], font=font)  # RGB color
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        frame[:] = result
    except ImportError:
        text_overlay(frame, text, pos, color)


# ---------- 1. 基础绘制 ----------
def test_drawing():
    """测试基础绘制能力"""
    print("  1. 基础绘制...")
    frames = []
    for i in range(FPS * 3):  # 3 秒
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        t = i / FPS

        # 动态圆形
        cx, cy = W // 2, H // 3
        radius = int(100 + 50 * np.sin(t * 2 * np.pi))
        cv2.circle(frame, (cx, cy), radius, CYAN, 3)

        # 矩形旋转效果
        for j in range(5):
            size = 80 + j * 30
            angle = t * 60 + j * 15
            center = (W // 2, H // 2)
            rect = ((center[0], center[1]), (size, size), angle)
            box = cv2.boxPoints(rect)
            box = np.round(box).astype(np.int32)
            color = [CYAN, MAGENTA, GOLD, GREEN, PINK][j]
            cv2.drawContours(frame, [box], 0, color, 2)

        # 文字标签
        text_cn(frame, "基础绘制", (W // 2 - 150, H // 4 - 50), CYAN, 60)
        text_overlay(frame, f"Frame: {i}", (50, H - 100), WHITE, 0.8, 1)

        frames.append(frame)
    return frames


# ---------- 2. 颜色空间 ----------
def test_color_space():
    """测试颜色空间转换"""
    print("  2. 颜色空间...")
    frames = []
    # 创建渐变图
    gradient = np.zeros((H, W, 3), dtype=np.uint8)
    xs = np.arange(W, dtype=np.float32).reshape(1, -1)
    ys = np.arange(H, dtype=np.float32).reshape(-1, 1)
    gradient[:, :, 0] = (xs / W * 255).astype(np.uint8)
    gradient[:, :, 1] = (ys / H * 255).astype(np.uint8)
    gradient[:, :, 2] = 128

    for i in range(FPS * 4):  # 4 秒
        t = i / (FPS * 4)
        frame = np.full((H, W, 3), BG, dtype=np.uint8)

        # 原图
        roi_h = H // 4
        frame[0:roi_h, :] = cv2.resize(gradient, (W, roi_h))

        # 灰度
        gray = cv2.cvtColor(gradient, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        frame[roi_h:roi_h*2, :] = cv2.resize(gray_bgr, (W, roi_h))

        # HSV
        hsv = cv2.cvtColor(gradient, cv2.COLOR_BGR2HSV)
        frame[roi_h*2:roi_h*3, :] = cv2.resize(hsv, (W, roi_h))

        # 边缘
        edges = cv2.Canny(gradient, 50, 150)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        frame[roi_h*3:, :] = cv2.resize(edges_bgr, (W, H - roi_h*3))

        # 标签
        labels = ["Original", "Gray", "HSV", "Canny Edge"]
        for j, label in enumerate(labels):
            text_overlay(frame, label, (50, j * roi_h + 50), WHITE, 1.0, 2)

        frames.append(frame)
    return frames


# ---------- 3. 滤镜 ----------
def test_filters():
    """测试各种滤镜"""
    print("  3. 滤镜...")
    # 创建测试图案
    base = np.full((H, W, 3), BG, dtype=np.uint8)
    for i in range(20):
        cx, cy = np.random.randint(100, W-100), np.random.randint(100, H-100)
        r = np.random.randint(30, 100)
        color = [CYAN, MAGENTA, GOLD, GREEN, PINK][i % 5]
        cv2.circle(base, (cx, cy), r, color, -1)

    filters = [
        ("Original", lambda x: x),
        ("Blur", lambda x: cv2.blur(x, (15, 15))),
        ("Gaussian", lambda x: cv2.GaussianBlur(x, (15, 15), 0)),
        ("Median", lambda x: cv2.medianBlur(x, 15)),
        ("Bilateral", lambda x: cv2.bilateralFilter(x, 15, 75, 75)),
    ]

    frames = []
    per_filter = FPS * 2  # 每个滤镜 2 秒
    for name, func in filters:
        for i in range(per_filter):
            frame = func(base.copy())
            text_cn(frame, name, (50, 100), WHITE, 50)
            frames.append(frame)
    return frames


# ---------- 4. 边缘检测 ----------
def test_edge_detection():
    """测试边缘检测算法"""
    print("  4. 边缘检测...")
    # 创建测试图案（几何图形）
    base = np.full((H, W, 3), BG, dtype=np.uint8)
    cv2.rectangle(base, (200, 400), (800, 1000), WHITE, 3)
    cv2.circle(base, (W//2, H//2), 300, WHITE, 3)
    cv2.line(base, (100, 1500), (900, 1500), WHITE, 5)
    # 三角形
    pts = np.array([[W//2, 200], [200, 800], [800, 800]], np.int32)
    cv2.polylines(base, [pts], True, WHITE, 3)

    methods = [
        ("Canny", lambda x: cv2.Canny(x, 50, 150)),
        ("Sobel X", lambda x: cv2.Sobel(x, cv2.CV_64F, 1, 0, ksize=5)),
        ("Sobel Y", lambda x: cv2.Sobel(x, cv2.CV_64F, 0, 1, ksize=5)),
        ("Laplacian", lambda x: cv2.Laplacian(x, cv2.CV_64F)),
    ]

    frames = []
    per_method = FPS * 2
    for name, func in methods:
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        edge = func(gray)
        # 归一化到 0-255
        edge_norm = cv2.normalize(edge, None, 0, 255, cv2.NORM_MINMAX)
        edge_uint8 = np.abs(edge_norm).astype(np.uint8)
        edge_bgr = cv2.cvtColor(edge_uint8, cv2.COLOR_GRAY2BGR)

        for i in range(per_method):
            frame = edge_bgr.copy()
            text_cn(frame, name, (50, 100), GOLD, 50)
            frames.append(frame)
    return frames


# ---------- 5. 轮廓检测 ----------
def test_contours():
    """测试轮廓检测"""
    print("  5. 轮廓检测...")
    frames = []
    for i in range(FPS * 4):
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        t = i / FPS

        # 动态图形
        shapes = np.full((H, W, 3), BG, dtype=np.uint8)
        for j in range(5):
            cx = int(W * (j + 1) / 6)
            cy = H // 2 + int(100 * np.sin(t + j))
            r = int(50 + 30 * np.sin(t * 2 + j))
            cv2.circle(shapes, (cx, cy), r, WHITE, -1)

        gray = cv2.cvtColor(shapes, cv2.COLOR_BGR2GRAY)
        contours, hierarchy = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # 绘制轮廓
        result = np.full((H, W, 3), BG, dtype=np.uint8)
        for idx, cnt in enumerate(contours):
            color = [CYAN, MAGENTA, GOLD, GREEN, PINK][idx % 5]
            cv2.drawContours(result, [cnt], -1, color, 3)
            # 质心
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.circle(result, (cx, cy), 5, WHITE, -1)

        text_cn(result, f"Contours: {len(contours)}", (50, 100), CYAN, 50)
        frames.append(result)
    return frames


# ---------- 6. 阈值处理 ----------
def test_threshold():
    """测试阈值处理"""
    print("  6. 阈值处理...")
    # 创建渐变
    gradient = np.zeros((H, W), dtype=np.uint8)
    for x in range(W):
        gradient[:, x] = int(x / W * 255)

    methods = [
        ("Binary", lambda x: cv2.threshold(x, 128, 255, cv2.THRESH_BINARY)[1]),
        ("Binary Inv", lambda x: cv2.threshold(x, 128, 255, cv2.THRESH_BINARY_INV)[1]),
        ("Trunc", lambda x: cv2.threshold(x, 128, 255, cv2.THRESH_TRUNC)[1]),
        ("ToZero", lambda x: cv2.threshold(x, 128, 255, cv2.THRESH_TOZERO)[1]),
        ("Otsu", lambda x: cv2.threshold(x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
        ("Adaptive Mean", lambda x: cv2.adaptiveThreshold(x, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)),
        ("Adaptive Gauss", lambda x: cv2.adaptiveThreshold(x, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
    ]

    frames = []
    per_method = FPS * 2
    for name, func in methods:
        for i in range(per_method):
            result = func(gradient)
            frame = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
            text_cn(frame, name, (50, 100), MAGENTA, 45)
            frames.append(frame)
    return frames


# ---------- 7. 形态学操作 ----------
def test_morphology():
    """测试形态学操作"""
    print("  7. 形态学操作...")
    # 创建测试图案
    base = np.zeros((H, W), dtype=np.uint8)
    for i in range(10):
        cx, cy = np.random.randint(100, W-100), np.random.randint(200, H-200)
        cv2.circle(base, (cx, cy), 40, 255, -1)

    kernel = np.ones((7, 7), np.uint8)
    operations = [
        ("Original", lambda x: x),
        ("Erode", lambda x: cv2.erode(x, kernel, iterations=2)),
        ("Dilate", lambda x: cv2.dilate(x, kernel, iterations=2)),
        ("Open", lambda x: cv2.morphologyEx(x, cv2.MORPH_OPEN, kernel)),
        ("Close", lambda x: cv2.morphologyEx(x, cv2.MORPH_CLOSE, kernel)),
        ("Gradient", lambda x: cv2.morphologyEx(x, cv2.MORPH_GRADIENT, kernel)),
        ("Top Hat", lambda x: cv2.morphologyEx(x, cv2.MORPH_TOPHAT, kernel)),
        ("Black Hat", lambda x: cv2.morphologyEx(x, cv2.MORPH_BLACKHAT, kernel)),
    ]

    frames = []
    per_op = FPS * 2
    for name, func in operations:
        result = func(base)
        frame = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        text_cn(frame, name, (50, 100), GREEN, 50)
        for i in range(per_op):
            frames.append(frame.copy())
    return frames


# ---------- 8. 特征检测 ----------
def test_features():
    """测试特征/角点检测"""
    print("  8. 特征检测...")
    # 创建棋盘格图案
    base = np.zeros((H, W), dtype=np.uint8)
    cell_size = 80
    for y in range(0, H, cell_size):
        for x in range(0, W, cell_size):
            if (x // cell_size + y // cell_size) % 2 == 0:
                base[y:y+cell_size, x:x+cell_size] = 255

    frames = []
    for i in range(FPS * 3):
        frame_color = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)

        # Harris 角点检测
        dst = cv2.cornerHarris(base, 2, 3, 0.04)
        dst_norm = cv2.normalize(dst, None, 0, 255, cv2.NORM_MINMAX)
        corners = np.where(dst_norm > 200)

        for pt_y, pt_x in zip(corners[0][::10], corners[1][::10]):
            cv2.circle(frame_color, (int(pt_x), int(pt_y)), 5, CYAN, -1)

        text_cn(frame_color, "Harris Corners", (50, 100), GOLD, 50)
        frames.append(frame_color)
    return frames


# ---------- 9. 视频合成 ----------
def generate_video():
    """生成完整演示视频"""
    print("生成 OpenCV 演示视频...")

    all_frames = []

    # 标题
    print("  标题...")
    for i in range(FPS * 2):
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        text_cn(frame, "OpenCV 基础能力测试", (W//2 - 350, H//2 - 50), CYAN, 60)
        text_cn(frame, "计算机视觉 · 图像处理", (W//2 - 280, H//2 + 50), DIM, 40)
        all_frames.append(frame)

    # 各测试
    tests = [
        ("1. 基础绘制", test_drawing),
        ("2. 颜色空间", test_color_space),
        ("3. 滤镜", test_filters),
        ("4. 边缘检测", test_edge_detection),
        ("5. 轮廓检测", test_contours),
        ("6. 阈值处理", test_threshold),
        ("7. 形态学", test_morphology),
        ("8. 特征检测", test_features),
    ]

    for name, func in tests:
        print(f"测试: {name}")
        frames = func()
        all_frames.extend(frames)

    # 写入视频
    print("写入视频...")
    raw_path = OUT_DIR / "opencv_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(raw_path), fourcc, FPS, (W, H))

    for frame in all_frames:
        writer.write(frame)
    writer.release()
    print(f"  原始视频: {raw_path}")

    # 用 FFmpeg 转码（H.264）
    final_path = OUT_DIR / "opencv_demo.mp4"
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-i", str(raw_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(final_path)
    ]
    subprocess.run(cmd, check=True)
    print(f"  最终视频: {final_path}")

    # 清理临时文件
    raw_path.unlink()

    return final_path


if __name__ == "__main__":
    final = generate_video()
    print(f"\n完成！输出: {final}")
