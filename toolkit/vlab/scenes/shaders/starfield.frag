#version 330
// 深空星场：星星的颜色按真实色温给（黑体辐射近似），不是随便涂的。
// 用在《为什么没有绿色的恒星》：开场、反思、片尾。
out vec4 fragColor;

uniform vec2  iResolution;
uniform float iTime;
uniform float uDrift;      // 横向漂移速度
uniform float uZoom;       // 推进：1 不变，>1 拉远
uniform float uDim;        // 整体压暗：0 正常，1 全黑
uniform float uGreenTry;   // 绿色光点的亮度（试图亮起又熄灭）
uniform float uTwinkle;    // 闪烁强度

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// 色温 → RGB。分段近似，覆盖 1500K–15000K；星场里最热只到 13000K，够用。
// 要画 O 型星（3 万度以上）得把上限提到 40000K，否则和 B 型算出来一样（004 的 scene.py 踩过）。
vec3 blackbody(float t) {
    t = clamp(t, 1500.0, 15000.0) / 100.0;
    float r, g, b;
    r = t <= 66.0 ? 255.0 : 329.698727446 * pow(t - 60.0, -0.1332047592);
    g = t <= 66.0 ? 99.4708025861 * log(t) - 161.1195681661
                  : 288.1221695283 * pow(t - 60.0, -0.0755148492);
    b = t >= 66.0 ? 255.0 : (t <= 19.0 ? 0.0 : 138.5177312231 * log(t - 10.0) - 305.0447927307);
    return clamp(vec3(r, g, b) / 255.0, 0.0, 1.0);
}

// 一层星星：格子里每格最多一颗。要扫一圈 3x3 的邻格，
// 否则星星的光晕会在格子边界被硬切掉，画面上会出现方块状的亮斑。
vec3 layer(vec2 uv, float cell, float bright, float seed) {
    vec2 g = uv * cell;
    vec2 base = floor(g);
    vec3 acc = vec3(0.0);
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            vec2 id = base + vec2(dx, dy);
            float h = hash(id + seed);
            if (h < 0.80) continue;                      // 大部分格子是空的
            vec2 off = (vec2(hash(id + 1.3 + seed), hash(id + 7.7 + seed)) - 0.5) * 0.7;
            vec2 d2 = g - id - 0.5 - off;                // 相对这颗星的偏移（格子单位）
            float d = length(d2);
            float mag = hash(id + 3.1 + seed);
            // 色温分布：多数偏黄红（和真实恒星一致：M、K 型最多），少数蓝白
            float temp = mix(2800.0, 13000.0, pow(hash(id + 5.9 + seed), 2.2));
            float tw = 1.0 + uTwinkle * 0.5 * sin(iTime * (1.5 + mag * 3.0) + h * 30.0);
            float core = bright * pow(mag, 1.5) * tw / (1.0 + 700.0 * d * d);
            float halo = bright * pow(mag, 2.2) * 0.18 / (1.0 + 70.0 * d);
            // 光晕必须在一格之内衰减干净，否则 3x3 邻域兜不住，边界会显出方块
            acc += blackbody(temp) * (core + halo) * smoothstep(1.45, 0.25, d);
        }
    }
    return acc;
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * iResolution.xy) / iResolution.y;
    uv *= uZoom;
    uv.x += iTime * uDrift;

    vec3 col = vec3(0.012, 0.015, 0.035);                    // 深空底色，带一点蓝
    col += vec3(0.02, 0.012, 0.03) * smoothstep(0.9, 0.0, length(uv));  // 中心微亮

    col += layer(uv, 7.0,  1.35, 0.0);
    col += layer(uv, 14.0, 0.85, 11.0);
    col += layer(uv, 26.0, 0.50, 23.0);

    // 绿色光点：想亮起来，但亮度由外部控制，最终会熄灭
    if (uGreenTry > 0.001) {
        vec2 gp = vec2(0.22, 0.08);
        float d = length(uv - gp);
        col += vec3(0.35, 1.0, 0.45) * uGreenTry * (0.55 / (1.0 + 2600.0 * d * d) + 0.025 / (1.0 + 160.0 * d));
    }

    col *= (1.0 - uDim);
    col = pow(col, vec3(0.85));                               // 轻微提亮暗部
    fragColor = vec4(col, 1.0);
}
