#version 330
// 太阳特写：盘面颜色按色温算（黑体辐射近似），不是手工涂的。
// uTint 控制"在大气外看"还是"在地面看"：地面那一版把蓝光按瑞利散射的比例扣掉，
// 所以同一颗太阳会自己变黄，不用改颜色常数。
out vec4 fragColor;

uniform vec2  iResolution;
uniform float iTime;
uniform float uTemp;        // 色温（K）：5772 就是太阳
uniform float uRadius;      // 盘面半径（按画面高度的比例）
uniform float uGround;      // 0 = 大气外（白），1 = 地面看（偏黄）
uniform float uGlow;        // 外围光晕强度
uniform float uBright;      // 整体亮度，用来做淡入淡出
uniform float uGreenRing;   // 绿色峰值环的强度（用来点出"峰值在绿色"）
uniform vec2  uCenter;      // 盘心偏移（画面高度为 1 的单位），用来给文字让位

const float PI = 3.14159265;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x),
               mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}

// 色温 → 线性 RGB，白点约 6500K，和 starfield.frag 同一套。
// 注意 004 的 scene.py 里光谱型色块故意以 A 型（8500K）为白点，那是天文学惯例（G 型叫"黄"）；
// 这里保持 6500K，因为太阳在大气外看就是白的，两者的差距正是那条片子要讲的。
vec3 blackbody(float t) {
    t = clamp(t, 1500.0, 15000.0) / 100.0;
    float r, g, b;
    r = t <= 66.0 ? 255.0 : 329.698727446 * pow(t - 60.0, -0.1332047592);
    g = t <= 66.0 ? 99.4708025861 * log(t) - 161.1195681661
                  : 288.1221695283 * pow(t - 60.0, -0.0755148492);
    b = t >= 66.0 ? 255.0 : (t <= 19.0 ? 0.0 : 138.5177312231 * log(t - 10.0) - 305.0447927307);
    return clamp(vec3(r, g, b) / 255.0, 0.0, 1.0);
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * iResolution.xy) / iResolution.y - uCenter;
    float d = length(uv);
    float R = uRadius;

    vec3 base = blackbody(uTemp);
    // 地面看：蓝光被瑞利散射带走一部分（波长四次方关系的近似），太阳就显黄
    vec3 ground = base * vec3(1.0, 0.93, 0.70);
    vec3 col_sun = mix(base, ground, clamp(uGround, 0.0, 1.0));

    vec3 col = vec3(0.012, 0.015, 0.032);

    // 盘面：边缘稍暗（临边昏暗），表面有缓慢翻动的米粒组织
    float disk = smoothstep(R, R * 0.975, d);
    if (disk > 0.001) {
        float limb = sqrt(max(0.0, 1.0 - pow(d / R, 2.0)));
        float gran = noise(uv * 42.0 + iTime * 0.08) * 0.10 + noise(uv * 110.0 - iTime * 0.05) * 0.05;
        col = mix(col, col_sun * (0.86 + 0.26 * limb + gran), disk);
    }

    // 光晕：两层，近处紧实、远处柔和
    float g1 = exp(-max(0.0, d - R) * 11.0);
    float g2 = exp(-max(0.0, d - R) * 2.6);
    col += col_sun * uGlow * (0.55 * g1 + 0.22 * g2);

    // 绿色峰值环：用来点出"发光最强的波长在绿色"
    if (uGreenRing > 0.001) {
        float ring = exp(-pow((d - R * 1.22) / (R * 0.075), 2.0));
        col += vec3(0.30, 1.0, 0.42) * ring * uGreenRing * 0.85;
    }

    col *= uBright;
    col = pow(col, vec3(0.88));
    fragColor = vec4(col, 1.0);
}
