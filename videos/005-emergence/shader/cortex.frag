#version 330
// 皮层放电：一片神经元在放电。
// 每个神经元在格点里抖一点位置，各自有随机相位；用高次幂把"想起就亮一下"做出来，
// 再叠一段从中心向外扩散的行波当"传播"。用在 005 的 S10（大脑也是涌现）。
out vec4 fragColor;

uniform vec2  iResolution;
uniform float iTime;
uniform float uIntensity;   // 放电强度，0.5–1.2 之间调

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec2 hash2(vec2 p) {
    return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

// 一层神经元：格点内抖动 + 独立放电相位。返回该层贡献的颜色。
vec3 layer(vec2 p, float cell, float t, float seed) {
    vec2 g = p * cell;
    vec2 id = floor(g);
    vec2 f = fract(g) - 0.5;
    vec2 off = (hash2(id + seed) - 0.5) * 0.55;     // 抖动，避免看起来像棋盘
    float d = length(f - off);
    float ph = hash(id + seed + 3.7);
    // 高次幂 = 长时间暗、短时间亮，才像放电而不是呼吸灯
    float fire = pow(0.5 + 0.5 * sin(t * 2.2 + ph * 43.0), 14.0);
    float body = smoothstep(0.20, 0.02, d);
    float halo = smoothstep(0.60, 0.0, d) * 0.35;
    vec3 col = mix(vec3(0.28, 0.45, 0.85), vec3(0.30, 0.90, 0.82), ph);
    return col * (body * (0.14 + fire * 1.5) + halo * fire * 0.8);
}

// 从中心扩散的放电波
float wave(vec2 p, float t) {
    float d = length(p * vec2(1.0, 1.35));
    return pow(0.5 + 0.5 * sin(d * 26.0 - t * 5.5), 12.0) * smoothstep(0.80, 0.05, d);
}

void main() {
    // 用短边归一，竖屏下细胞才不会被拉长
    vec2 p = (gl_FragCoord.xy - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float t = iTime * 1.15;

    vec3 col = vec3(0.020, 0.025, 0.050);
    col += layer(p, 11.0, t, 0.0) * 1.00;
    col += layer(p, 19.0, t * 0.85 + 1.7, 5.0) * 0.55;

    float w = wave(p, t);
    col += vec3(0.95, 0.72, 0.28) * w * 0.55 * (0.6 + 0.4 * uIntensity);

    // 中心一点冷光，把视线收住
    float core = smoothstep(0.42, 0.0, length(p));
    col += vec3(0.25, 0.55, 0.75) * core * 0.10;

    col *= 1.0 - 0.55 * smoothstep(0.35, 1.05, length(p * vec2(0.85, 1.0)));
    fragColor = vec4(pow(max(col, 0.0), vec3(0.92)), 1.0);
}
