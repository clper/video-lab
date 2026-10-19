"""Blender 基础能力测试

通过 Blender Python API 测试：
1. 创建 3D 场景（立方体 + 灯光 + 相机）
2. 材质和纹理
3. 相机动画（环绕旋转）
4. 渲染输出（图片 + 视频）

用法：
    blender --background --python test_blender.py

输出：
    renders/scene_static.png
    renders/scene_orbit.mp4
"""

import bpy
import os
import sys
import math
from mathutils import Vector

# ---------- 配置 ----------
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
os.makedirs(OUT_DIR, exist_ok=True)

RES_X, RES_Y = 1080, 1920  # 竖屏
FPS = 30


def clear_scene():
    """清空场景"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # 清除所有材质
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)


def setup_camera():
    """创建相机"""
    bpy.ops.object.camera_add(location=(6, -6, 4))
    cam = bpy.context.active_object
    cam.name = "Camera"
    
    # 对准原点
    direction = Vector((0, 0, 0)) - cam.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    
    # 相机设置
    cam.data.lens = 50
    bpy.context.scene.camera = cam
    return cam


def setup_light():
    """创建灯光"""
    # 主光源（太阳光）
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.data.color = (1.0, 0.95, 0.9)
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    
    # 补光（点光源）
    bpy.ops.object.light_add(type='POINT', location=(-3, -3, 3))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 100
    fill.data.color = (0.7, 0.8, 1.0)
    
    return sun, fill


def create_material(name, color, metallic=0.0, roughness=0.5):
    """创建 PBR 材质"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def create_objects():
    """创建测试物体"""
    # 1. 立方体（金属材质）
    bpy.ops.mesh.primitive_cube_add(size=1.5, location=(0, 0, 0.75))
    cube = bpy.context.active_object
    cube.name = "Cube"
    mat_metal = create_material("GoldMetal", (0.8, 0.6, 0.1), metallic=1.0, roughness=0.2)
    cube.data.materials.append(mat_metal)
    
    # 2. 球体（玻璃材质）
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(2.5, 0, 0.8))
    sphere = bpy.context.active_object
    sphere.name = "GlassSphere"
    mat_glass = create_material("Glass", (0.9, 0.95, 1.0), metallic=0.0, roughness=0.0)
    mat_glass.use_nodes = True
    # 设置透明
    bsdf = mat_glass.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Alpha"].default_value = 0.3
    bsdf.inputs["IOR"].default_value = 1.45
    sphere.data.materials.append(mat_glass)
    
    # 3. 环面（粗糙材质）
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.2, minor_radius=0.3,
        location=(-2.5, 0, 1.2)
    )
    torus = bpy.context.active_object
    torus.name = "Torus"
    mat_rough = create_material("RoughRed", (0.8, 0.1, 0.1), metallic=0.0, roughness=0.9)
    torus.data.materials.append(mat_rough)
    
    # 4. 地面
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    mat_ground = create_material("Ground", (0.15, 0.15, 0.18), metallic=0.0, roughness=0.8)
    ground.data.materials.append(mat_ground)
    
    return cube, sphere, torus, ground


def setup_world():
    """设置世界环境"""
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.02, 0.02, 0.05, 1.0)
    bg.inputs["Strength"].default_value = 0.5


def render_static():
    """渲染静态图片"""
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'
    scene.render.film_transparent = False
    
    # Cycles 设置
    scene.cycles.samples = 64  # 快速测试用，正式用 128+
    scene.cycles.use_denoising = True
    
    # 输出路径
    output_path = os.path.join(OUT_DIR, "scene_static.png")
    scene.render.filepath = output_path
    
    # 渲染
    bpy.ops.render.render(write_still=True)
    print(f"静态渲染完成: {output_path}")
    return output_path


def setup_camera_animation(cam, frames=FPS * 6):
    """设置相机环绕动画"""
    # 起始位置
    cam.location = (6, -6, 4)
    cam.keyframe_insert(data_path="location", frame=1)
    
    # 动画：相机环绕
    for f in range(1, frames + 1):
        t = f / frames
        angle = t * 2 * math.pi  # 完整一圈
        
        radius = 8
        height = 3 + 1.5 * math.sin(t * 4 * math.pi)  # 上下波动
        
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = height
        
        cam.location = (x, y, z)
        
        # 对准原点
        direction = Vector((0, 0, 1)) - cam.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam.rotation_euler = rot_quat.to_euler()
        
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)
    
    # 物体旋转动画
    cube = bpy.data.objects.get("Cube")
    if cube:
        cube.rotation_euler = (0, 0, 0)
        cube.keyframe_insert(data_path="rotation_euler", frame=1)
        cube.rotation_euler = (0, 0, 2 * math.pi)
        cube.keyframe_insert(data_path="rotation_euler", frame=frames)
    
    torus = bpy.data.objects.get("Torus")
    if torus:
        torus.rotation_euler = (0, 0, 0)
        torus.keyframe_insert(data_path="rotation_euler", frame=1)
        torus.rotation_euler = (math.radians(360), math.radians(180), 0)
        torus.keyframe_insert(data_path="rotation_euler", frame=frames)


def render_animation():
    """渲染动画"""
    scene = bpy.context.scene
    
    # 帧范围
    frame_count = FPS * 6  # 6 秒
    scene.frame_start = 1
    scene.frame_end = frame_count
    scene.render.fps = FPS
    
    # 渲染设置
    scene.render.resolution_x = 540  # 半分辨率加速
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32  # 快速测试
    
    # 输出路径
    output_dir = os.path.join(OUT_DIR, "frames")
    os.makedirs(output_dir, exist_ok=True)
    scene.render.filepath = os.path.join(output_dir, "frame_")
    scene.render.image_settings.file_format = 'PNG'
    
    # 渲染动画
    bpy.ops.render.render(animation=True)
    print(f"动画帧渲染完成: {output_dir}")
    
    # 用 FFmpeg 合成视频
    ffmpeg = r"d:\Projects\personal_ip\AI-Vedio\tools\bin\ffmpeg.exe"
    output_video = os.path.join(OUT_DIR, "scene_orbit.mp4")
    
    import subprocess
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", os.path.join(output_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_video
    ]
    subprocess.run(cmd, check=True)
    print(f"视频合成完成: {output_video}")
    
    return output_video


# ---------- 主流程 ----------
def main():
    print("=" * 50)
    print("Blender 基础能力测试")
    print("=" * 50)
    
    # 清空场景
    print("\n1. 清空场景...")
    clear_scene()
    
    # 设置环境
    print("2. 设置世界环境...")
    setup_world()
    
    # 创建相机和灯光
    print("3. 创建相机和灯光...")
    cam = setup_camera()
    setup_light()
    
    # 创建物体
    print("4. 创建物体（立方体/球体/环面/地面）...")
    create_objects()
    
    # 渲染静态图
    print("\n5. 渲染静态图片...")
    render_static()
    
    # 设置相机动画
    print("\n6. 设置相机环绕动画...")
    setup_camera_animation(cam)
    
    # 渲染动画
    print("\n7. 渲染动画...")
    render_animation()
    
    print("\n" + "=" * 50)
    print("Blender 测试完成！")
    print(f"输出目录: {OUT_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
