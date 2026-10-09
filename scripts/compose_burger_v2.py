"""商业美食海报合成器 v2 —— 手写笔刷标题 + 品牌信息矩阵。

参考对标：高端快餐连锁品牌广告（如 ZHAPU CREATIVE 系列）。
相比 v1（compose_burger.py）的升级：
  · 主标题支持「生图生成的毛笔笔刷字 PNG」—— 字体库无英文手写体，生图补齐
  · 品牌信息矩阵：副标语 / 侧栏文案 / 圆形徽章 / 底部双栏
  · 保留 v1 的极简底子，信息量按需增补

用法：
  python compose_burger_v2.py --bg base.png --out final.png \
      --title-img title.png \
      --brand "ZHAPU CREATIVE" --tagline "TASTE A BRIGHTER TOMORROW" \
      --left-head "JUICY\nBOLD\nSATISFYING" \
      --left-sub "MORE THAN A BURGER\nA BETTER DAY" \
      --right-head "Real Ingredients\nReal Happiness" \
      --right-sub "SIMPLE INGREDIENTS\nEXTRAORDINARY FLAVOR" \
      --badge-top "PREMIUM BEEF" --badge-sub "ALWAYS GOOD TASTE" \
      --left-foot "GREAT FOOD\nBRINGS PEOPLE\nCLOSER" \
      --ratio 0.75 --save-size 1086x1448
"""

import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WHITE = "#F5F1E8"
GOLD = "#C9A227"
GOLD_L = "#E0BC5A"
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


def _shadow(im, d, xy, text, font, fill, blur=16, alpha=175, stroke=0):
    """投影 + 可选细描边的文字。合成必须走 Image 对象（ImageDraw 没有 alpha_composite）。"""
    if blur > 0:
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        a = f"{alpha:02x}"
        ld.text((xy[0], xy[1] + max(2, blur // 6)), text, font=font,
                fill=SHADOW + a, stroke_width=stroke + max(2, blur // 3),
                stroke_fill=SHADOW + a)
        im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    if stroke:
        d.text(xy, text, font=font, fill=fill,
               stroke_width=stroke, stroke_fill=SHADOW + "A0")
    else:
        d.text(xy, text, font=font, fill=fill)


def _fit_ratio(im, target_ratio):
    """扩边适配比例（不拉伸变形、不裁切内容）"""
    W0, H0 = im.size
    cur = W0 / H0
    if abs(cur - target_ratio) <= 1e-4:
        return im
    # 目标更宽（如 3:4 = 0.75 > 底图 2:3 = 0.667）→ 左右扩宽，保住上下留白
    if cur < target_ratio:
        newW = int(H0 * target_ratio)
        pad = newW - W0
        canvas = Image.new("RGBA", (newW, H0), (0, 0, 0, 255))
        side = pad // 2
        strip = im.crop((0, 0, max(1, int(W0 * 0.05)), H0)) \
                  .resize((side + 2, H0), Image.LANCZOS) \
                  .filter(ImageFilter.GaussianBlur(int(side * 0.10)))
        canvas.paste(strip, (0, 0))
        canvas.paste(strip, (newW - side - 2, 0))
        canvas.paste(im, (side, 0))
        return canvas
    # 目标更高（如底图 3:4 → 目标 2:3）→ 上下扩宽
    newH = int(W0 / target_ratio)
    pad = newH - H0
    if pad > 0:
        canvas = Image.new("RGBA", (W0, newH), (0, 0, 0, 255))
        top = pad // 2
        strip = im.crop((0, 0, W0, max(1, int(H0 * 0.05)))) \
                  .resize((W0, top + 2), Image.LANCZOS) \
                  .filter(ImageFilter.GaussianBlur(int(top * 0.10)))
        canvas.paste(strip, (0, 0))
        canvas.paste(strip, (0, newH - top - 2))
        canvas.paste(im, (0, top))
        return canvas
    return canvas
    newH = int(W0 / target_ratio)                 # 太宽 → 上下加高
    canvas = Image.new("RGBA", (W0, newH), (0, 0, 0, 255))
    pad = (newH - H0) // 2
    strip = im.crop((0, 0, W0, max(1, int(H0 * 0.06)))) \
              .resize((W0, pad), Image.LANCZOS) \
              .filter(ImageFilter.GaussianBlur(int(pad * 0.12)))
    canvas.paste(strip, (0, 0))
    canvas.paste(strip, (0, newH - pad))
    canvas.paste(im, (0, pad))
    return canvas


def _paste_title(im, d, title_img, y_frac, W, H, scale_w,
                 shadow_blur=4.0, shadow_alpha=90, shadow_dy=3):
    """把笔刷标题 PNG 贴到顶部区域（可与主体穿插叠压）。

    投影必须「克制」：叠压时投影只用来分出层次，不是营造氛围。
    实测过重参数（blur 14 / alpha D8 / 偏移 6）会把下层面包糊成黑块，
    主体完全看不见 —— 反而失去了叠压的意义。
    默认 blur=4 / alpha=90(35%) / dy=3px，只留一层淡淡的分离感。
    """
    t = Image.open(title_img).convert("RGBA")
    bb = t.getchannel("A").getbbox()
    if bb:
        t = t.crop(bb)
    tw = int(W * scale_w)
    th = int(t.height * tw / t.width)
    t = t.resize((tw, th), Image.LANCZOS)
    tx, ty = int((W - tw) / 2), int(H * y_frac)
    if shadow_alpha > 0 and shadow_blur > 0:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", t.size, SHADOW + f"{shadow_alpha:02x}"),
                 (tx, ty + int(shadow_dy * H / 1536)))
        im.alpha_composite(sh.filter(
            ImageFilter.GaussianBlur(int(shadow_blur * H / 1536))))
    im.alpha_composite(t, (tx, ty))


def compose(bg, out, title_img=None, brand="ZHAPU CREATIVE", tagline=None,
            left_head=None, left_sub=None, right_head=None, right_sub=None,
            badge_top=None, badge_sub=None, left_foot=None,
            af=None, ratio=None, save_size=None,
            ts_blur=4.0, ts_alpha=90, ts_dy=3):
    af = af or _font_dir()
    im = Image.open(bg).convert("RGBA")
    if ratio:
        im = _fit_ratio(im, ratio)
    W, H = im.size
    sc = H / 1536.0
    m = int(W * 0.055)                          # 安全边距
    d = ImageDraw.Draw(im, "RGBA")

    # --- 顶部与底部压暗：垫出文字对比 ---
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    for i in range(int(H * 0.20)):              # 顶部
        gd.line([(0, i), (W, i)],
                fill=(8, 6, 4, int(135 * (1 - i / (H * 0.20)) ** 1.2)))
    for i in range(int(H * 0.20)):              # 底部
        gd.line([(0, H - 1 - i), (W, H - 1 - i)],
                fill=(8, 6, 4, int(165 * (i / (H * 0.20)) ** 0.85)))
    im.alpha_composite(g)
    d = ImageDraw.Draw(im, "RGBA")

    # --- 主标题：笔刷 PNG（优先）或字体渲染 ---
    if title_img and os.path.exists(title_img):
        _paste_title(im, d, title_img, 0.020, W, H, 0.60,
                      shadow_blur=ts_blur, shadow_alpha=ts_alpha,
                      shadow_dy=ts_dy)
    f_s = _font(af, ["NotoSansSC-Medium.otf", "NotoSansSC-Regular.otf"],
                int(20 * sc))

    # --- 侧栏文案：左（窄体大写三行）/ 右（细体） ---
    if left_head:
        f_lh = _font(af, ["NotoSansSC-Bold.otf"], int(34 * sc))
        y = int(H * 0.300)
        for ln in left_head.split("\n"):
            d.text((m, y), ln, font=f_lh, fill=WHITE + "FF",
                   stroke_width=max(1, int(1 * sc)), stroke_fill=SHADOW + "A0")
            y += int(f_lh.size * 1.30)
        # 左侧竖分割线
        d.line([(m, y + int(14 * sc)), (m, y + int(14 * sc) + int(56 * sc))],
               fill=WHITE + "90", width=max(2, int(3 * sc)))
        if left_sub:
            y2 = y + int(30 * sc)
            f_ls = _font(af, ["NotoSansSC-Regular.otf"], int(19 * sc))
            for ln in left_sub.split("\n"):
                d.text((m, y2), ln, font=f_ls, fill=WHITE + "C0")
                y2 += int(f_ls.size * 1.42)

    if right_head:
        f_rh = _font(af, ["ZCOOLXiaoWei.ttf", "NotoSansSC-Medium.otf"],
                     int(40 * sc))
        lines = right_head.split("\n")
        y = int(H * 0.300)
        for ln in lines:
            d.text((W - m - d.textlength(ln, font=f_rh), y), ln,
                   font=f_rh, fill=GOLD_L + "FF",
                   stroke_width=max(1, int(1 * sc)), stroke_fill=SHADOW + "A0")
            y += int(f_rh.size * 1.34)

    if right_sub:
        f_rs = _font(af, ["NotoSansSC-Medium.otf"], int(20 * sc))
        lines = right_sub.split("\n")
        y = int(H * 0.570)
        for ln in lines:
            d.text((W - m - d.textlength(ln, font=f_rs), y), ln,
                   font=f_rs, fill=WHITE + "D8",
                   stroke_width=max(1, int(1 * sc)), stroke_fill=SHADOW + "90")
            y += int(f_rs.size * 1.42)

    # --- 圆形徽章（左侧中部）---
    if badge_top:
        r = int(W * 0.105)
        cx, cy = m + r + int(6 * sc), int(H * 0.520)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=GOLD_L + "FF", width=max(2, int(3 * sc)))
        d.ellipse([cx - r + int(8 * sc), cy - r + int(8 * sc),
                   cx + r - int(8 * sc), cy + r - int(8 * sc)],
                  outline=GOLD_L + "80", width=max(1, int(2 * sc)))
        f_bt = _font(af, ["NotoSansSC-Bold.otf"], int(21 * sc))
        f_bs = _font(af, ["NotoSansSC-Regular.otf"], int(15 * sc))
        # 顶部弧形文字（用旋转的窄条模拟，简单可靠）
        _arc_text(im, d, cx, cy, r * 0.74, badge_top, f_bt, GOLD_L + "FF", -90)
        if badge_sub:
            tw = d.textlength(badge_sub, font=f_bs)
            d.text((cx - tw / 2, cy + r * 0.46), badge_sub,
                   font=f_bs, fill=GOLD_L + "D0")

    # --- 底部：左脚注 + 品牌名 + 标语 ---
    if left_foot:
        f_lf = _font(af, ["NotoSansSC-Medium.otf"], int(16 * sc))
        y = H - m - int(26 * sc)
        for ln in reversed(left_foot.split("\n")):
            tw = d.textlength(ln, font=f_lf)
            d.text((m, y), ln, font=f_lf, fill=WHITE + "B0")
            y -= int(f_lf.size * 1.34)

    if brand:
        f_b = _font(af, ["Montserrat.ttf", "NotoSansSC-Medium.otf"],
                    int(36 * sc))
        track = int(f_b.size * 0.30)
        bw = d.textlength(brand, font=f_b)
        bx = (W - (bw + track * (len(brand) - 1))) / 2
        by = H - m - int(44 * sc)
        for ch in brand:
            _shadow(im, d, (bx, by), ch, f_b, WHITE + "FF", blur=16, alpha=185)
            bx += d.textlength(ch, font=f_b) + track
    if tagline:
        f_t = _font(af, ["NotoSansSC-Regular.otf"], int(17 * sc))
        track2 = int(f_t.size * 0.22)
        tw = d.textlength(tagline, font=f_t)
        tx = (W - (tw + track2 * (len(tagline) - 1))) / 2
        ty = H - m - int(14 * sc)
        for ch in tagline:
            d.text((tx, ty), ch, font=f_t, fill=WHITE + "B0")
            tx += d.textlength(ch, font=f_t) + track2

    im.convert("RGB").save(out, quality=96)
    if save_size:
        w, h = (int(v) for v in save_size.lower().split("x"))
        Image.open(out).resize((w, h), Image.LANCZOS).save(out, quality=96)
    return out


def _arc_text(im, d, cx, cy, r, text, font, fill, start_deg):
    """沿圆弧排布文字（逐字旋转绘制）"""
    total = sum(d.textlength(c, font=font) for c in text) / r
    ang = start_deg + (total / 2) * 57.2958        # 度
    step = (total * 57.2958) / max(len(text), 1)
    for ch in text:
        wch = d.textlength(ch, font=font)
        sub = Image.new("RGBA", (int(font.size * 2), int(font.size * 2)),
                        (0, 0, 0, 0))
        sd = ImageDraw.Draw(sub)
        sd.text((sub.width / 2 - wch / 2, sub.height / 2 - font.size * 0.62),
                ch, font=font, fill=fill)
        sub = sub.rotate(-(ang - 90), expand=True, resample=Image.BICUBIC)
        px = cx + r * _cos(ang) - sub.width / 2
        py = cy - r * _sin(ang) - sub.height / 2
        im.alpha_composite(sub, (int(px), int(py)))
        d = ImageDraw.Draw(im, "RGBA")
        ang -= step


def _cos(deg):
    import math
    return math.cos(math.radians(deg))


def _sin(deg):
    import math
    return math.sin(math.radians(deg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title-img", default=None, help="笔刷标题 PNG（透明）")
    ap.add_argument("--brand", default="ZHAPU CREATIVE")
    ap.add_argument("--tagline", default=None)
    ap.add_argument("--left-head", default=None)
    ap.add_argument("--left-sub", default=None)
    ap.add_argument("--right-head", default=None)
    ap.add_argument("--right-sub", default=None)
    ap.add_argument("--badge-top", default=None)
    ap.add_argument("--badge-sub", default=None)
    ap.add_argument("--left-foot", default=None)
    ap.add_argument("--title-shadow-blur", type=float, default=4.0,
                    help="标题投影模糊半径（基准画布高1536），0=不投影")
    ap.add_argument("--title-shadow-alpha", type=int, default=90,
                    help="标题投影透明度 0-255")
    ap.add_argument("--title-shadow-dy", type=int, default=3,
                    help="标题投影垂直偏移像素")
    ap.add_argument("--ratio", type=float, default=None)
    ap.add_argument("--save-size", default=None)
    a = ap.parse_args()
    print("[OK]", compose(a.bg, a.out, a.title_img, a.brand, a.tagline,
                          a.left_head, a.left_sub, a.right_head, a.right_sub,
                          a.badge_top, a.badge_sub, a.left_foot,
                          ratio=a.ratio, save_size=a.save_size,
                          ts_blur=a.title_shadow_blur,
                          ts_alpha=a.title_shadow_alpha,
                          ts_dy=a.title_shadow_dy))


if __name__ == "__main__":
    main()
