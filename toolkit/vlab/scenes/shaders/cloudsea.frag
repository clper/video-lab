// 云海飞越雪山：光线步进（raymarching）片元着色器
// 每个像素发出一条视线：先步进求与山地高度场的交点，再在云层里分步积分体积云，最后叠天空和大气雾。
// 全部是程序化噪声，不用任何贴图和模型。由 research/visual/07 的 render_shader.py 和 003 的开场用 toolkit/vlab/render/glsl.py 逐帧调用。
#version 330

uniform vec2 iResolution;
uniform float iTime;
out vec4 fragColor;

const vec3 SUN = normalize(vec3(0.22, 0.11, 1.0));   // 低空夕阳，在前方偏一侧：侧逆光让云有明暗面
const vec3 SUNCOL = vec3(1.0, 0.62, 0.32) * 3.0;
const float CL0 = 0.35;    // 云层底
const float CL1 = 1.45;    // 云层顶
const float FAR = 70.0;

// ---------- 哈希与值噪声（整数哈希，不依赖 sin，跨显卡结果一致） ----------
uint hu(uint x) {
    x ^= x >> 16u; x *= 0x7feb352du;
    x ^= x >> 15u; x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}
float h2(ivec2 p) { return float(hu(uint(p.x) ^ hu(uint(p.y) + 0x68e31da4u))) * (1.0 / 4294967295.0); }
float h3(ivec3 p) { return float(hu(uint(p.x) ^ hu(uint(p.y) ^ hu(uint(p.z) + 0x9e3779b9u)))) * (1.0 / 4294967295.0); }

float n2(vec2 x) {
    ivec2 i = ivec2(floor(x));
    vec2 f = fract(x);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(h2(i), h2(i + ivec2(1, 0)), u.x), mix(h2(i + ivec2(0, 1)), h2(i + ivec2(1, 1)), u.x), u.y);
}

float n3(vec3 x) {
    ivec3 i = ivec3(floor(x));
    vec3 f = fract(x);
    vec3 u = f * f * (3.0 - 2.0 * f);
    float a = h3(i), b = h3(i + ivec3(1, 0, 0)), c = h3(i + ivec3(0, 1, 0)), d = h3(i + ivec3(1, 1, 0));
    float e = h3(i + ivec3(0, 0, 1)), g = h3(i + ivec3(1, 0, 1)), k = h3(i + ivec3(0, 1, 1)), m = h3(i + ivec3(1, 1, 1));
    return mix(mix(mix(a, b, u.x), mix(c, d, u.x), u.y), mix(mix(e, g, u.x), mix(k, m, u.x), u.y), u.z);
}

// ---------- 航线与山地 ----------
float pathX(float z) { return 3.0 * sin(z * 0.045) + 1.2 * sin(z * 0.11 + 1.3); }

float terrain(vec2 p) {
    float h = 0.0, a = 0.5;
    vec2 q = p * 0.16;
    mat2 R = mat2(0.80, -0.60, 0.60, 0.80);          // 每层旋转一下，避免网格感
    for (int i = 0; i < 8; i++) {
        float n = 1.0 - abs(2.0 * n2(q) - 1.0);       // 脊状噪声：尖峰、锐利山脊
        h += a * n * n;
        a *= 0.48;
        q = R * q * 2.05;
    }
    // 山脉沿航线两侧排开（像穿行在峡谷里），航线正下方压低，镜头不撞山
    float side = abs(p.x - pathX(p.y));
    float mask = smoothstep(2.5, 9.0, side) * (0.55 + 0.45 * n2(p * 0.05 + 7.3));
    return h * (0.8 + 9.0 * mask) - 0.6;
}

float marchTerrain(vec3 ro, vec3 rd) {
    float t = 0.1;
    for (int i = 0; i < 300; i++) {
        vec3 p = ro + rd * t;
        float d = p.y - terrain(p.xz);
        if (d < 0.0015 * t) return t;
        if (t > FAR || (p.y > 5.5 && rd.y > 0.0)) break;
        t += 0.4 * d;
    }
    return -1.0;
}

vec3 terrainNormal(vec3 p, float t) {
    float e = 0.002 + 0.0015 * t;
    return normalize(vec3(terrain(p.xz - vec2(e, 0.0)) - terrain(p.xz + vec2(e, 0.0)), 2.0 * e,
                          terrain(p.xz - vec2(0.0, e)) - terrain(p.xz + vec2(0.0, e))));
}

float softShadow(vec3 ro) {
    float res = 1.0, t = 0.05;
    for (int i = 0; i < 40; i++) {
        vec3 p = ro + SUN * t;
        float h = p.y - terrain(p.xz);
        res = min(res, 12.0 * h / t);
        if (res < 0.01 || p.y > 5.0) break;
        t += clamp(h, 0.05, 0.6);
    }
    return clamp(res, 0.0, 1.0);
}

// ---------- 天空与大气 ----------
vec3 skyCol(vec3 rd) {
    float mu = max(dot(rd, SUN), 0.0);
    float y = max(rd.y, 0.0);
    vec3 hor = mix(vec3(0.55, 0.35, 0.45), vec3(1.0, 0.50, 0.20), pow(mu, 6.0));   // 地平线：背光处偏紫，近太阳偏橙
    vec3 col = mix(hor, vec3(0.05, 0.08, 0.24), pow(y + 0.02, 0.3));
    col += vec3(1.0, 0.50, 0.20) * 0.4 * pow(mu, 18.0);
    col += vec3(1.0, 0.75, 0.45) * 0.9 * pow(mu, 64.0);
    col += vec3(1.3, 1.0, 0.7) * 10.0 * smoothstep(0.99986, 0.99993, mu);   // 太阳圆盘
    return col;
}
vec3 fogCol(vec3 rd) { return mix(vec3(0.35, 0.30, 0.42), vec3(1.0, 0.55, 0.28), pow(max(dot(rd, SUN), 0.0), 6.0)); }
float fogAmt(float t) { return 1.0 - exp(-t * 0.012); }

vec3 shadeTerrain(vec3 p, float t) {
    vec3 n = terrainNormal(p, t);
    float snow = smoothstep(0.55, 0.85, n.y + 0.25 * (n2(p.xz * 3.0) - 0.5))
               * smoothstep(1.9, 2.9, p.y + 0.5 * n2(p.xz * 0.7));
    vec3 rock = mix(vec3(0.20, 0.17, 0.16), vec3(0.36, 0.31, 0.28), n2(p.xz * 2.0));
    vec3 alb = mix(rock, vec3(0.92, 0.94, 0.98), snow);
    float dif = max(dot(n, SUN), 0.0) * softShadow(p + n * 0.01);
    vec3 amb = mix(vec3(0.08, 0.09, 0.18), vec3(0.30, 0.32, 0.50), 0.5 + 0.5 * n.y);
    vec3 col = alb * (SUNCOL * dif * 1.2 + amb * 0.8);
    col += alb * vec3(0.55, 0.50, 0.50) * 0.12 * (1.0 - smoothstep(CL1, CL1 + 1.0, p.y));   // 云海反光照亮山脚
    return col;
}

// ---------- 体积云 ----------
float cloudDensity(vec3 p) {
    float hf = (p.y - CL0) / (CL1 - CL0);
    if (hf < 0.0 || hf > 1.0) return 0.0;
    vec3 q = p * vec3(0.6, 1.1, 0.6) + vec3(0.06 * iTime, 0.0, 0.03 * iTime);   // 云缓慢流动
    float n = 0.0, a = 0.55;
    for (int i = 0; i < 5; i++) {
        n += a * n3(q);
        q = q * 2.07 + vec3(3.1, 1.7, 7.3);
        a *= 0.5;
    }
    float shape = smoothstep(0.0, 0.3, hf) * (1.0 - smoothstep(0.45, 1.0, hf));   // 底平、顶部翻滚
    return clamp((n * shape - 0.25) * 2.5, 0.0, 1.0);
}

vec4 clouds(vec3 ro, vec3 rd, float tEnd, float jitter) {
    if (abs(rd.y) < 1e-4) return vec4(0.0, 0.0, 0.0, 1.0);
    float ta = (CL1 - ro.y) / rd.y, tb = (CL0 - ro.y) / rd.y;
    float t0 = max(min(ta, tb), 0.0);
    float t1 = min(min(max(ta, tb), tEnd), FAR);
    vec3 acc = vec3(0.0);
    float T = 1.0;
    if (t1 <= t0) return vec4(acc, T);
    float mu = max(dot(rd, SUN), 0.0);
    float phase = 0.55 + 1.6 * pow(mu, 20.0);        // 前向散射：只在太阳附近方向让云边发亮
    vec3 fogc = fogCol(rd);
    float dt = clamp((t1 - t0) / 64.0, 0.05, 0.6);
    float t = t0 + dt * jitter;
    for (int i = 0; i < 96; i++) {
        if (t > t1 || T < 0.02) break;
        vec3 p = ro + rd * t;
        float d = cloudDensity(p);
        if (d > 0.001) {
            float dl = cloudDensity(p + SUN * 0.12) + 0.7 * cloudDensity(p + SUN * 0.4);
            float sh = exp(-dl * 2.4);                        // 朝太阳方向被挡住多少
            float hf = clamp((p.y - CL0) / (CL1 - CL0), 0.0, 1.0);
            vec3 amb = mix(vec3(0.06, 0.07, 0.14), vec3(0.42, 0.38, 0.55), hf * hf);   // 天光：底部冷暗，顶部蓝紫
            vec3 lit = SUNCOL * sh * phase + amb * 0.6;
            lit = mix(lit, fogc, fogAmt(t));
            float a = 1.0 - exp(-d * dt * 6.0);
            acc += T * a * lit;
            T *= 1.0 - a;
        }
        t += dt;
    }
    return vec4(acc, T);
}

vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }

void main() {
    vec2 fc = gl_FragCoord.xy;
    vec2 uv = (fc - 0.5 * iResolution) / iResolution.y;

    // 镜头：沿蜿蜒航线前进，略低头，转弯时侧倾
    float z = 2.2 * iTime;
    vec3 ro = vec3(pathX(z), 3.0 + 0.15 * sin(iTime * 0.4), z);
    float zt = z + 3.0;
    vec3 ta = vec3(pathX(zt), ro.y - 0.28, zt);
    float roll = -0.35 * (pathX(z + 1.0) - pathX(z));
    vec3 cw = normalize(ta - ro);
    vec3 cu = normalize(cross(cw, vec3(sin(roll), cos(roll), 0.0)));
    vec3 cv = cross(cu, cw);
    vec3 rd = normalize(uv.x * cu + uv.y * cv + 0.9 * cw);

    float tt = marchTerrain(ro, rd);
    vec3 col;
    if (tt > 0.0) {
        col = shadeTerrain(ro + rd * tt, tt);
        col = mix(col, fogCol(rd), fogAmt(tt));
    } else {
        col = skyCol(rd);
    }
    vec4 cl = clouds(ro, rd, tt > 0.0 ? tt : FAR, h2(ivec2(fc)));
    col = col * cl.a + cl.rgb;

    col = aces(col * 0.8);
    col = pow(col, vec3(1.0 / 2.2));
    col = mix(col, col * col * (3.0 - 2.0 * col), 0.4);   // S 形对比曲线
    vec2 q = fc / iResolution;
    col *= 0.78 + 0.22 * pow(16.0 * q.x * q.y * (1.0 - q.x) * (1.0 - q.y), 0.15);
    col += (h2(ivec2(fc) + ivec2(7, 3)) - 0.5) / 255.0;    // 抖动，避免天空色带
    fragColor = vec4(col, 1.0);
}
