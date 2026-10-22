"""《为什么没有绿色的恒星》数字自验：维恩位移定律 + 普朗克定律

片子里出现的每个物理数字都在这里算一遍，改稿子前先跑这个。
    uv run python videos/004-green-star/content/verify.py
"""

import math

B_WIEN = 2.897771955e-3          # 维恩位移常数 m·K（CODATA 定义值）
H, C, K = 6.62607015e-34, 2.99792458e8, 1.380649e-23
SUN_T = 5772                     # 太阳有效温度 K


def peak_nm(T):
    """维恩位移定律：峰值波长（纳米）"""
    return B_WIEN / T * 1e9


def planck(lam_nm, T):
    """普朗克定律：该波长的辐射强度（相对值即可）"""
    l = lam_nm * 1e-9
    return (2 * H * C ** 2) / l ** 5 / (math.exp(H * C / (l * K * T)) - 1)


def rgb_ratio(T, blue=450, green=550, red=650):
    """蓝绿红三段的相对强度，归一化到绿 = 1"""
    g = planck(green, T)
    return planck(blue, T) / g, 1.0, planck(red, T) / g


def main():
    print(f"太阳 {SUN_T} K 的峰值波长：{peak_nm(SUN_T):.1f} nm（绿色区间 500–565 nm）")
    print(f"峰值落在绿色需要的温度：{B_WIEN / 565e-9:.0f} – {B_WIEN / 500e-9:.0f} K\n")
    print("温度       峰值      蓝450 : 绿550 : 红650     看起来")
    for T, name in ((3600, "参宿四(约)"), (5772, "太阳"), (7000, "F型"), (12100, "参宿七")):
        b, g, r = rgb_ratio(T)
        print(f"{T:6d} K  {peak_nm(T):6.1f} nm   {b:.2f} : {g:.2f} : {r:.2f}   {name}")
    print("\n关键结论：太阳三段强度几乎相等（0.99 : 1.00 : 0.88），所以看起来是白的。")


if __name__ == "__main__":
    main()
