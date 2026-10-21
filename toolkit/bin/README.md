# toolkit/bin：本机程序（可选）

放本机专用的程序，比如 `ffmpeg.exe`、`ffprobe.exe`；这里的 `.exe` 不入库（见 `.gitignore`）。

`research/visual` 的测试脚本会先找这里，找不到就用系统 PATH 上的 ffmpeg。系统里已经装了 ffmpeg 的机器不用管这个目录。
