"""生成艺术基础测试

用 Python 实现 Processing 风格的生成艺术：
1. 分形树（递归）
2. 粒子系统（引力/排斥）
3. Lissajous 曲线
4. 流场（Perlin noise）
5. 螺旋图案例案
6. 视频合成

用法：
    python test_generative.py

输出：
    renders/generative_demo.mp4
"""

import numpy as np
import cv2
import subprocess
import os
from pathlib import Path

FFMPEG = r"d:\Projects\personal_ip\AI-Vedio\tools\bin\ffmpeg.exe"
OUT_DIR = Path(__file__).parent / "renders"
OUT_DIR.mkdir(exist_ok=True)

W, H = 1080, 1920
FPS = 30

# ---------- 配色 ----------
BG = (10, 6, 5)
PALETTE = [
    (238, 211, 34),    # cyan
    (249, 121, 233),   # magenta
    (36, 191, 251),    # gold
    (128, 222, 74),    # green
    (182, 114, 244),   # pink
    (255, 255, 255),   # white
]


def text_overlay(frame, text, pos, color=(255, 255, 255), scale=1.5):
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, 2, cv2.LINE_AA)


# ---------- 1. 分形树 ----------
def test_fractal_tree():
    """递归分形树"""
    print("  1. 分形树...")
    frames = []
    max_depth = 12

    for i in range(FPS * 5):  # 5 秒
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        t = i / FPS
        # 逐渐生长
        current_depth = min(max_depth, int(t * 3) + 1)
        
        draw_branch(frame, (W // 2, H - 200), -np.pi / 2, 250, 0, current_depth, t)
        
        text_overlay(frame, f"Fractal Tree (depth={current_depth})", (50, 100), PALETTE[0], 1.0)
        frames.append(frame)
    return frames


def draw_branch(frame, start, angle, length, depth, max_depth, time):
    if depth >= max_depth or length < 3:
        return
    
    end = (
        int(start[0] + length * np.cos(angle)),
        int(start[1] + length * np.sin(angle))
    )
    
    thickness = max(1, (max_depth - depth) * 2)
    color = PALETTE[depth % len(PALETTE)]
    cv2.line(frame, start, end, color, thickness)
    
    # 风摆效果
    sway = np.sin(time * 2 + depth * 0.5) * 0.1
    
    new_length = length * 0.72
    angle_spread = 0.4 + depth * 0.03
    
    draw_branch(frame, end, angle - angle_spread + sway, new_length, depth + 1, max_depth, time)
    draw_branch(frame, end, angle + angle_spread + sway, new_length, depth + 1, max_depth, time)


# ---------- 2. 粒子系统 ----------
def test_particles():
    """粒子系统"""
    print("  2. 粒子系统...")
    n_particles = 200
    # 初始化粒子
    particles = {
        'x': np.random.uniform(0, W, n_particles),
        'y': np.random.uniform(0, H, n_particles),
        'vx': np.random.uniform(-2, 2, n_particles),
        'vy': np.random.uniform(-2, 2, n_particles),
        'color': np.random.randint(0, len(PALETTE), n_particles),
        'size': np.random.randint(2, 8, n_particles),
    }
    
    # 引力中心
    centers = [
        (W // 3, H // 3),
        (2 * W // 3, 2 * H // 3),
    ]
    
    frames = []
    for i in range(FPS * 5):
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        t = i / FPS
        
        # 移动引力中心
        cx = int(W // 2 + W // 4 * np.cos(t * 0.5))
        cy = int(H // 2 + H // 4 * np.sin(t * 0.7))
        
        for j in range(n_particles):
            # 引力
            dx = cx - particles['x'][j]
            dy = cy - particles['y'][j]
            dist = max(np.sqrt(dx**2 + dy**2), 50)
            force = 500 / dist**2
            
            particles['vx'][j] += dx / dist * force
            particles['vy'][j] += dy / dist * force
            
            # 阻尼
            particles['vx'][j] *= 0.98
            particles['vy'][j] *= 0.98
            
            # 更新位置
            particles['x'][j] += particles['vx'][j]
            particles['y'][j] += particles['vy'][j]
            
            # 边界反弹
            if particles['x'][j] < 0 or particles['x'][j] > W:
                particles['vx'][j] *= -1
            if particles['y'][j] < 0 or particles['y'][j] > H:
                particles['vy'][j] *= -1
            
            # 绘制
            color = PALETTE[particles['color'][j]]
            size = int(particles['size'][j])
            cv2.circle(frame, (int(particles['x'][j]), int(particles['y'][j])),
                       size, color, -1)
        
        text_overlay(frame, f"Particles: {n_particles}", (50, 100), PALETTE[1], 1.0)
        frames.append(frame)
    return frames


# ---------- 3. Lissajous 曲线 ----------
def test_lissajous():
    """Lissajous 曲线"""
    print("  3. Lissajous 曲线...")
    frames = []
    
    for i in range(FPS * 5):
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        t = i / FPS
        
        # 参数变化
        a = 3 + np.sin(t * 0.3) * 2
        b = 2 + np.cos(t * 0.5) * 2
        delta = t * 0.5
        
        # 生成曲线点
        theta = np.linspace(0, 2 * np.pi, 1000)
        x = (W // 2 + 300 * np.sin(a * theta + delta)).astype(np.int32)
        y = (H // 2 + 500 * np.sin(b * theta)).astype(np.int32)
        
        # 绘制多条（不同相位）
        for k in range(5):
            phase = k * np.pi / 5
            xk = (W // 2 + 300 * np.sin(a * theta + delta + phase)).astype(np.int32)
            yk = (H // 2 + 500 * np.sin(b * theta + phase)).astype(np.int32)
            
            pts = np.column_stack([xk, yk])
            color = PALETTE[k % len(PALETTE)]
            cv2.polylines(frame, [pts], False, color, 2)
        
        text_overlay(frame, f"Lissajous (a={a:.1f}, b={b:.1f})", (50, 100), PALETTE[2], 1.0)
        frames.append(frame)
    return frames


# ---------- 4. 流场 ----------
def test_flow_field():
    """Perlin noise 流场"""
    print("  4. 流场...")
    n_agents = 300
    
    # 简单噪声（用正弦波叠加模拟 Perlin）
    def noise2d(x, y, t):
        return (np.sin(x * 0.01 + t) + np.sin(y * 0.01 + t * 0.7) +
                np.sin((x + y) * 0.007 + t * 0.3)) * np.pi
    
    # 初始化 agents
    agents_x = np.random.uniform(0, W, n_agents)
    agents_y = np.random.uniform(0, H, n_agents)
    agents_color = np.random.randint(0, len(PALETTE), n_agents)
    
    frames = []
    trail = np.full((H, W, 3), BG, dtype=np.uint8)
    
    for i in range(FPS * 5):
        frame = trail.copy()
        t = i / FPS
        
        for j in range(n_agents):
            # 计算流场角度
            angle = noise2d(agents_x[j], agents_y[j], t)
            
            # 移动
            agents_x[j] += 3 * np.cos(angle)
            agents_y[j] += 3 * np.sin(angle)
            
            # 边界环绕
            agents_x[j] %= W
            agents_y[j] %= H
            
            # 绘制轨迹
            color = PALETTE[agents_color[j]]
            cv2.circle(trail, (int(agents_x[j]), int(agents_y[j])), 1, color, -1)
        
        text_overlay(frame, f"Flow Field ({n_agents} agents)", (50, 100), PALETTE[3], 1.0)
        frames.append(frame)
    return frames


# ---------- 5. 螺旋图案 ----------
def test_spiral():
    """螺旋图案"""
    print("  5. 螺旋图案...")
    frames = []
    
    for i in range(FPS * 5):
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        t = i / FPS
        
        # 多个螺旋
        for s in range(4):
            center_x = W // 2
            center_y = H // 2
            
            n_points = 500
            theta = np.linspace(0, 8 * np.pi + t * 2, n_points)
            
            # 不同螺旋参数
            offset = s * np.pi / 2
            r = np.linspace(0, 400, n_points)
            
            x = (center_x + r * np.cos(theta + offset)).astype(np.int32)
            y = (center_y + r * np.sin(theta + offset)).astype(np.int32)
            
            pts = np.column_stack([x, y])
            color = PALETTE[s % len(PALETTE)]
            cv2.polylines(frame, [pts], False, color, 2)
            
            # 在螺旋末端加点
            for k in range(0, n_points, 20):
                size = int(2 + 4 * (k / n_points))
                cv2.circle(frame, (x[k], y[k]), size, color, -1)
        
        text_overlay(frame, "Spiral Patterns", (50, 100), PALETTE[4], 1.0)
        frames.append(frame)
    return frames


# ---------- 6. 合成视频 ----------
def generate_video():
    """生成完整演示视频"""
    print("生成生成艺术演示视频...")
    
    all_frames = []
    
    # 标题
    print("  标题...")
    for i in range(FPS * 2):
        frame = np.full((H, W, 3), BG, dtype=np.uint8)
        text_overlay(frame, "Generative Art", (W // 2 - 250, H // 2 - 30), PALETTE[0], 2.0)
        text_overlay(frame, "Python + OpenCV + NumPy", (W // 2 - 200, H // 2 + 60), PALETTE[5], 1.0)
        all_frames.append(frame)
    
    # 各测试
    tests = [
        ("1. Fractal Tree", test_fractal_tree),
        ("2. Particles", test_particles),
        ("3. Lissajous", test_lissajous),
        ("4. Flow Field", test_flow_field),
        ("5. Spiral", test_spiral),
    ]
    
    for name, func in tests:
        print(f"测试: {name}")
        frames = func()
        all_frames.extend(frames)
    
    # 写入视频
    print("写入视频...")
    raw_path = OUT_DIR / "generative_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(raw_path), fourcc, FPS, (W, H))
    
    for frame in all_frames:
        writer.write(frame)
    writer.release()
    
    # FFmpeg 转码
    final_path = OUT_DIR / "generative_demo.mp4"
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-i", str(raw_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(final_path)
    ]
    subprocess.run(cmd, check=True)
    print(f"完成 -> {final_path}")
    
    raw_path.unlink()
    return final_path


if __name__ == "__main__":
    final = generate_video()
    print(f"\n输出: {final}")
