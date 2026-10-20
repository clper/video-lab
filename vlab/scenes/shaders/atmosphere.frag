// 大气散射天空：按真实物理（单次散射，Nishita 模型）逐像素算天空颜色
// 瑞利散射系数用公认测量值（蓝光约是红光的 6 倍），米氏散射负责太阳周围的光晕。
// 只改太阳高度：高时算出蓝天、白云；低时同一套公式算出红日、橙色晚霞——不手工调色。
// 远山和云的颜色也按"阳光穿过多少大气"来算。由 videos/003-sunset-red/shader/render_clips.py 调用（vlab/render/glsl.py）。
#version 330

uniform vec2 iResolution;
uniform float iTime;
uniform float uSunElev;      // 太阳高度角（弧度）
uniform float uSunAzim;      // 太阳相对镜头朝向的方位角（弧度，0 = 正前方）
uniform float uPitch;        // 镜头仰角（弧度）
uniform float uExposure;     // 曝光
uniform float uCloudCover;   // 云量 0..1
out vec4 fragColor;

const float PI = 3.14159265;
const float RE = 6360e3;                                   // 地球半径（米）
const float RA = 6420e3;                                   // 大气层顶
const vec3 BETA_R = vec3(5.8e-6, 13.5e-6, 33.1e-6);        // 瑞利散射系数（红、绿、蓝），每米
const float BETA_M = 8e-6;                                 // 米氏散射系数（气溶胶，取晴朗天气的值）
const float HR = 7994.0;                                   // 空气分子标高
const float HM = 1200.0;                                   // 气溶胶标高
const float G = 0.76;                                      // 米氏散射的前向程度
const float SUN_I = 22.0;                                  // 太阳光强
const float HC = 4000.0;                                   // 云层高度（高积云）

uint hu(uint x) { x ^= x >> 16u; x *= 0x7feb352du; x ^= x >> 15u; x *= 0x846ca68bu; x ^= x >> 16u; return x; }
float h2(ivec2 p) { return float(hu(uint(p.x) ^ hu(uint(p.y) + 0x68e31da4u))) * (1.0 / 4294967295.0); }
float h1(float x) { return h2(ivec2(int(floor(x)), 91)); }
float n1(float x) { float i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f); return mix(h1(i), h1(i + 1.0), f); }
float n2(vec2 x) {
    ivec2 i = ivec2(floor(x)); vec2 f = fract(x); vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(h2(i), h2(i + ivec2(1, 0)), u.x), mix(h2(i + ivec2(0, 1)), h2(i + ivec2(1, 1)), u.x), u.y);
}
float fbm1(float x) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * n1(x); x *= 2.1; a *= 0.5; } return s; }
float fbm2(vec2 p) {
    float s = 0.0, a = 0.5;
    mat2 R = mat2(0.8, -0.6, 0.6, 0.8);
    for (int i = 0; i < 6; i++) { s += a * n2(p); p = R * p * 2.03; a *= 0.5; }
    return s;
}

vec2 raySphere(vec3 ro, vec3 rd, float r) {
    float b = dot(ro, rd), c = dot(ro, ro) - r * r, d = b * b - c;
    if (d < 0.0) return vec2(1e9, -1e9);
    d = sqrt(d);
    return vec2(-b - d, -b + d);
}

vec3 sunDir() { return vec3(sin(uSunAzim) * cos(uSunElev), sin(uSunElev), cos(uSunAzim) * cos(uSunElev)); }

// 从 p 点朝太阳方向穿过的大气"厚度"（瑞利、米氏各一个）；被地球挡住返回 -1
vec2 lightDepth(vec3 p, vec3 s) {
    vec2 e = raySphere(p, s, RE);
    if (e.x < e.y && e.x > 0.0) return vec2(-1.0);     // 只有真的在前方撞上地球才算被挡（没撞上不能算挡住）
    float tA = raySphere(p, s, RA).y;
    float ds = tA / 8.0;
    vec2 od = vec2(0.0);
    for (int i = 0; i < 8; i++) {
        float h = length(p + s * (float(i) + 0.5) * ds) - RE;
        od += exp(-vec2(h / HR, h / HM)) * ds;
    }
    return od;
}
vec3 transmit(vec2 od) { return exp(-(BETA_R * od.x + BETA_M * 1.1 * od.y)); }

// 视线 ro→ro+rd*tmax 上散射进来的光；T 返回这段路的透过率
vec3 scatter(vec3 ro, vec3 rd, float tmax, out vec3 T) {
    vec3 s = sunDir();
    tmax = min(tmax, raySphere(ro, rd, RA).y);
    float ds = tmax / 32.0;
    vec2 odView = vec2(0.0);
    vec3 sumR = vec3(0.0), sumM = vec3(0.0);
    for (int i = 0; i < 32; i++) {
        vec3 p = ro + rd * (float(i) + 0.5) * ds;
        float h = length(p) - RE;
        vec2 d = exp(-vec2(h / HR, h / HM)) * ds;
        odView += d;
        vec2 odL = lightDepth(p, s);
        if (odL.x < 0.0) continue;
        vec3 tr = transmit(odView + odL);
        sumR += tr * d.x;
        sumM += tr * d.y;
    }
    T = transmit(odView);
    float mu = dot(rd, s);
    float pR = 3.0 / (16.0 * PI) * (1.0 + mu * mu);
    float pM = 3.0 / (8.0 * PI) * ((1.0 - G * G) * (1.0 + mu * mu)) / ((2.0 + G * G) * pow(1.0 + G * G - 2.0 * G * mu, 1.5));
    return SUN_I * (sumR * BETA_R * pR + sumM * BETA_M * pM);
}

void main() {
    vec2 fc = gl_FragCoord.xy;
    vec2 uv = (fc - 0.5 * iResolution) / iResolution.y;
    vec3 fwd = vec3(0.0, sin(uPitch), cos(uPitch));
    vec3 up = vec3(0.0, cos(uPitch), -sin(uPitch));
    vec3 rd = normalize(uv.x * vec3(1.0, 0.0, 0.0) + uv.y * up + 0.9 * fwd);
    vec3 ro = vec3(0.0, RE + 2.0, 0.0);
    vec3 s = sunDir();

    float el = asin(rd.y);
    float az = atan(rd.x, rd.z);
    float ridgeFar = 0.020 + 0.040 * fbm1(az * 6.0 + 3.0);     // 远山轮廓（仰角，弧度）
    float ridgeNear = 0.004 + 0.045 * fbm1(az * 11.0 + 17.0);  // 近山轮廓

    vec3 T;
    vec3 col;
    if (el < max(ridgeFar, ridgeNear)) {
        // 山：颜色 = 人和山之间那段空气散射进来的光（大气透视）+ 透过来的山体本身（很暗）
        // 距离按俯角估算：山脊处最远，越往画面下方越近（雾越少、越暗），形成逆光剪影
        float below = (el < ridgeNear ? ridgeNear : ridgeFar) - el;
        float dist = el < ridgeNear ? clamp(60.0 / max(below, 0.01), 200.0, 4000.0) : 28000.0;
        vec3 hd = normalize(vec3(rd.x, max(rd.y, 0.002), rd.z));
        vec3 air = scatter(ro, hd, dist, T);
        vec2 odS = lightDepth(ro + vec3(0.0, 300.0, 0.0), s);
        vec3 sunAtHill = odS.x < 0.0 ? vec3(0.0) : transmit(odS) * SUN_I * max(s.y, 0.0) * 0.004;
        col = air + T * (vec3(0.003, 0.0035, 0.005) + sunAtHill);
    } else {
        col = scatter(ro, rd, 1e9, T);
        // 太阳圆盘：亮度乘上沿途透过率——太阳低时透过来的几乎只剩红橙光
        float mu = dot(rd, s);
        vec2 odSun = lightDepth(ro, s);
        if (odSun.x >= 0.0) col += transmit(odSun) * SUN_I * 0.6 * smoothstep(0.99994, 0.99997, mu);

        // 云：一层高 2500 米的云，被"穿过大气后剩下的阳光"照亮
        if (rd.y > 0.0) {
            float tc = raySphere(ro, rd, RE + HC).y;
            vec3 pc = ro + rd * tc;
            vec2 q = pc.xz / vec2(5200.0, 2600.0) + vec2(iTime * 0.04, 0.0);   // 横向拉长的晚霞云
            float n = fbm2(q);
            float a = smoothstep(1.0 - uCloudCover, 1.0 - uCloudCover + 0.22, n) * (1.0 - smoothstep(60e3, 160e3, tc));
            if (a > 0.0) {
                vec3 T1;
                vec3 inAir = scatter(ro, rd, tc, T1);
                vec2 odC = lightDepth(pc, s);
                vec3 sunAtCloud = odC.x < 0.0 ? vec3(0.0) : transmit(odC) * SUN_I;
                vec3 Tz;
                vec3 skyAmb = scatter(pc, vec3(0.0, 1.0, 0.0), 1e9, Tz);
                float thick = smoothstep(0.0, 0.35, n - (1.0 - uCloudCover));
                vec3 cloudCol = sunAtCloud * (0.030 + 0.05 * pow(max(mu, 0.0), 8.0)) * mix(1.0, 0.55, thick) + skyAmb * 0.9;
                col = mix(col, inAir + T1 * cloudCol, a);
            }
        }
    }

    col = 1.0 - exp(-col * uExposure);
    col = pow(col, vec3(1.0 / 2.2));
    vec2 qv = fc / iResolution;
    col *= 0.82 + 0.18 * pow(16.0 * qv.x * qv.y * (1.0 - qv.x) * (1.0 - qv.y), 0.2);
    col += (h2(ivec2(fc) + ivec2(5, 9)) - 0.5) / 255.0;
    fragColor = vec4(col, 1.0);
}
