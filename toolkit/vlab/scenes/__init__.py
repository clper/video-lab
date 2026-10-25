"""可复用的画面生成器。正式视频和 lab 测试都从这里引用，不互相依赖。"""

from pathlib import Path

SHADERS = Path(__file__).resolve().parent / "shaders"     # cloudsea.frag（云海飞越雪山）、atmosphere.frag（大气散射天空）
