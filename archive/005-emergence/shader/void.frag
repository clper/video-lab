#version 330
// 空镜：极慢的尘埃 + 一层很淡的星云辉光。收尾用（005 的 S15）。
// 画面几乎不动，只让"呼吸"看得出——金句压在上面时，背景动太快会抢字。
out vec4 fragColor;

uniform vec2  iResolution;
uniform float iTime;
uniform float uGlow;        // 星云亮度，0–1

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);                     // 平滑插值
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float amp = 0.5;
    for (int i = 0; i < 5; i++) {
        v += amp * noise(p);
        p *= 2.03;
        amp *= 0.5;
    }
    return v;
}

// 一层尘埃：格子里最多一颗，扫 3x3 邻格，否则光晕会在格子边界被硬切
float dust(vec2 p, float cell, float t, float seed) {
    vec2 g = p * cell;
    vec2 base = floor(g);
    float acc = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 id = base + vec2(dx, dy);
            if (hash(id + seed) < 0.86) continue;
            vec2 off = vec2(hash(id + 1.7 + seed), hash(id + 5.3 + seed)) - 0.5;
            vec2 d2 = g - id - 0.5 - off * 0.6;
            float d = length(d2);
            float tw = 0.35 + 0.65 * (0.5 + 0.5 * sin(t * 1.6 + hash(id) * 40.0));
            acc += smoothstep(0.14, 0.0, d) * tw;
        }
    }
    return acc;
}

void main() {
    vec2 uv = gl_FragCoord.xy / iResolution.xy;
    vec2 p = (gl_FragCoord.xy - 0.5 * iResolution.xy) / min(iResolution.x, iResolution.y);
    float t = iTime * 0.55;

    vec3 col = vec3(0.018, 0.022, 0.042);

    // 星云：两层 fbm 缓慢错动，颜色从冷蓝过渡到暗金
    vec2 q = p * 1.5 + vec2(t * 0.03, -t * 0.02);
    float f = fbm(q) * 0.65 + fbm(q * 2.1 - vec2(t * 0.05, t * 0.03)) * 0.35;
    vec3 neb = mix(vec3(0.10, 0.14, 0.30), vec3(0.34, 0.26, 0.10), smoothstep(0.35, 0.85, f));
    col += neb * pow(f, 2.2) * (0.6 + 0.7 * uGlow);

    // 尘埃
    col += vec3(0.86, 0.92, 1.0) * dust(p, 13.0, t, 0.0) * 0.55;
    col += vec3(1.0, 0.86, 0.60) * dust(p, 22.0, t * 1.3, 7.0) * 0.32;

    // 底部一点暖光，让金句落下去的时候有托底
    col += vec3(0.93, 0.72, 0.30) * smoothstep(0.55, -0.35, p.y) * 0.085;
    // 一层很慢的金色晕开：空镜不能是死屏，但动快了会抢字，所以只让亮度呼吸
    float bloom = smoothstep(0.78, 0.0, length((p - vec2(0.0, -0.28)) * vec2(0.85, 1.25)));
    col += vec3(1.0, 0.82, 0.45) * bloom * 0.030 * (0.75 + 0.45 * sin(t * 0.32));

    col *= 1.0 - 0.62 * smoothstep(0.30, 1.05, length(p));
    fragColor = vec4(pow(max(col, 0.0), vec3(0.92)), 1.0);
}
