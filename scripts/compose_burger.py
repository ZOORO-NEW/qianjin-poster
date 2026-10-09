"""商业美食海报文字层合成器（极简高级版）。

与 `compose_guochao_food.py` 的分工：
  · 国潮美食版 → 满装饰（木牌/印章/弧形框），适合小吃铺物料
  · 本脚本   → 极简高级（只有标题 + 品牌），适合高端快餐/连锁品牌广告

设计原则（对齐国际快餐连锁 VI）：
  · full-bleed 满版，不加任何边框与外留白
  · 文字克制：主标题 + 品牌名，不堆装饰
  · 文字必须「三重保障」：底衬 + 描边（或阴影）+ 足够字号
  · 品牌名底部居中 + 细分割线，低调不抢主体
"""

import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 极简高级配色：暖白 + 深炭 + 描金
WHITE = "#F5F1E8"
GOLD = "#C9A227"        # 描金，用于分割线
SHADOW = "#0A0806"



# 字体目录定位：优先本技能同级 assets/fonts，其次 ~/.workbuddy/skills/qianjin-poster/assets/fonts
# 说明：assets/fonts/ 是本地缓存（由 setup_fonts.py 生成），不进发布包，
# 但运行时字体路径仍需可解析 —— 故做多路探测，不硬编码单机绝对路径。
def _font_dir():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.normpath(os.path.join(here, "..", "assets", "fonts")),
        os.path.normpath(os.path.join(here, "..", "..", "qianjin-poster", "assets", "fonts")),
        os.path.join(os.path.expanduser("~"), ".workbuddy", "skills",
                     "qianjin-poster", "assets", "fonts"),
    ]
    for c in cands:
        if os.path.isdir(c):
            return c
    return cands[0]

def _tf(af, *names):
    for n in names:
        p = os.path.join(af, n)
        if os.path.exists(p):
            return p
    return None


def _font(af, names, size):
    p = _tf(af, *names)
    return ImageFont.truetype(p, size) if p else ImageFont.load_default()


def _shadow_text(im, d, xy, text, font, fill, blur=18, alpha=170, off=(0, 3)):
    """投影文字：先画模糊阴影层，再叠实心字。
    深色背景上白字必须有投影才够「高级」，否则会糊进背景。

    注意：ImageDraw 对象没有 alpha_composite（它只是绘图上下文），
    合成必须走画布 Image 对象 —— 踩过这个坑。
    """
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    a = f"{alpha:02x}"
    ld.text((xy[0] + off[0], xy[1] + off[1]), text, font=font,
            fill=SHADOW + a, stroke_width=max(2, blur // 3),
            stroke_fill=SHADOW + a)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(layer)
    d.text(xy, text, font=font, fill=fill)


def compose(bg, out, title, brand, tagline=None,
            af=None, title_size=76, brand_size=38, tag_size=22,
            target_ratio=None):
    af = af or _font_dir()
    im = Image.open(bg).convert("RGBA")
    # --- 比例适配：优先「扩边」而非拉伸变形 ---
    # 生图给的底图比例常与目标不符（如底图 2:3 vs 目标 3:4）。
    # 直接 resize 会把汉堡压扁；裁切会切掉上下留白与分层结构。
    # 故按目标比例扩展画布，用边缘模糊采样填充新区域 —— 保持 full-bleed 无边框。
    if target_ratio:
        W0, H0 = im.size
        cur = W0 / H0
        if abs(cur - target_ratio) > 1e-4:
            if cur < target_ratio:               # 太窄 → 左右加宽
                newW = int(H0 * target_ratio)
                canvas = Image.new("RGBA", (newW, H0), (0, 0, 0, 255))
                # 用横向拉伸的边缘模糊条填充左右
                pad = (newW - W0) // 2
                strip = im.crop((0, 0, max(1, int(W0 * 0.06)), H0)) \
                          .resize((pad, H0), Image.LANCZOS) \
                          .filter(ImageFilter.GaussianBlur(int(pad * 0.12)))
                canvas.paste(strip, (0, 0))
                canvas.paste(strip, (newW - pad, 0))
                canvas.paste(im, (pad, 0))
                im = canvas
            else:                                  # 太宽 → 上下加高
                newH = int(W0 / target_ratio)
                canvas = Image.new("RGBA", (W0, newH), (0, 0, 0, 255))
                pad = (newH - H0) // 2
                strip = im.crop((0, 0, W0, max(1, int(H0 * 0.06)))) \
                          .resize((W0, pad), Image.LANCZOS) \
                          .filter(ImageFilter.GaussianBlur(int(pad * 0.12)))
                canvas.paste(strip, (0, 0))
                canvas.paste(strip, (0, newH - pad))
                canvas.paste(im, (0, pad))
                im = canvas
    W, H = im.size
    sc = H / 1536.0
    d = ImageDraw.Draw(im, "RGBA")

    # --- 主标题：BEEF BURGER，居中大字 ---
    if title:
        f_t = _font(af, ["Montserrat.ttf", "NotoSansSC-Bold.otf"],
                    int(title_size * sc))
        # 字间距：高级感靠「加宽字距」，不用描边堆砌
        track = int(f_t.size * 0.16)
        tw = d.textlength(title, font=f_t)
        total = tw + track * (len(title) - 1)
        x = (W - total) / 2
        y = int(H * 0.035)   # 顶部留白区（底图汉堡从 ~0.22H 开始）
        for ch in title:
            # 细描边（1px 深色）+ 投影：让白字在深背景上有「印刷感」而非发光感
            _shadow_text(im, d, (x, y), ch, f_t, WHITE + "FF", blur=22, alpha=185)
            d.text((x, y), ch, font=f_t, fill=WHITE + "FF",
                   stroke_width=max(1, int(1.2 * sc)), stroke_fill=SHADOW + "B0")
            x += d.textlength(ch, font=f_t) + track

    # --- 副标语（可选）---
    if tagline:
        f_g = _font(af, ["NotoSansSC-Medium.otf", "NotoSansSC-Regular.otf"],
                    int(tag_size * sc))
        gw = d.textlength(tagline, font=f_g)
        gx = (W - gw) / 2
        gy = y + int(f_t.size * 1.62) if title else int(H * 0.10)
        _shadow_text(im, d, (gx, gy), tagline, f_g, WHITE + "D8", blur=12, alpha=150)

    # --- 底部压暗：垫出文字对比，同时压掉底图可能存在的桌面高光 ---
    if brand or tagline:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        _top = int(H * 0.80)
        for i in range(_top, H):
            k = int(170 * ((i - _top) / (H - _top)) ** 0.85)
            gd.line([(0, i), (W, i)], fill=(8, 6, 4, k))
        im.alpha_composite(g)
        d = ImageDraw.Draw(im, "RGBA")

    # --- 品牌名：底部居中 + 细分割线 ---
    if brand:
        f_b = _font(af, ["Montserrat.ttf", "NotoSansSC-Medium.otf"],
                    int(brand_size * sc))
        btrack = int(f_b.size * 0.30)
        bw = d.textlength(brand, font=f_b)
        btotal = bw + btrack * (len(brand) - 1)
        bx = (W - btotal) / 2
        by = int(H * 0.895)
        # 品牌名上方细分割线（描金，居中）
        line_y = by - int(26 * sc)
        line_w = int(W * 0.20)
        d.line([(W / 2 - line_w / 2, line_y), (W / 2 + line_w / 2, line_y)],
               fill=GOLD + "FF", width=max(1, int(2 * sc)))
        for ch in brand:
            _shadow_text(im, d, (bx, by), ch, f_b, WHITE + "FF", blur=18, alpha=190)
            d.text((bx, by), ch, font=f_b, fill=WHITE + "FF",
                   stroke_width=max(1, int(1.0 * sc)), stroke_fill=SHADOW + "A0")
            bx += d.textlength(ch, font=f_b) + btrack

    im.convert("RGB").save(out, quality=96)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="BEEF BURGER")
    ap.add_argument("--brand", default="ZHAPU CREATIVE")
    ap.add_argument("--tagline", default="")
    ap.add_argument("--title-size", type=int, default=76)
    ap.add_argument("--brand-size", type=int, default=38)
    ap.add_argument("--tag-size", type=int, default=22)
    ap.add_argument("--ratio", type=float, default=None,
                    help="目标宽高比（如 0.75 = 3:4）。给了就扩边适配而非拉伸")
    ap.add_argument("--save-size", default=None,
                    help="最终导出尺寸，如 1086x1448")
    a = ap.parse_args()
    out = compose(a.bg, a.out, a.title, a.brand, a.tagline,
                  title_size=a.title_size, brand_size=a.brand_size,
                  tag_size=a.tag_size, target_ratio=a.ratio)
    if a.save_size:      # 导出到指定尺寸（比例已一致，等比缩放即可）
        w, h = (int(v) for v in a.save_size.lower().split("x"))
        Image.open(out).resize((w, h), Image.LANCZOS).save(out, quality=96)
    print("[OK]", out)


if __name__ == "__main__":
    main()
