import { Config } from "@remotion/cli/config";

// 每帧存 jpeg，体积小；输出覆盖；并发降到 2，避开 Windows 上 3D/WebGL 镜头偶发超时。
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(2);
