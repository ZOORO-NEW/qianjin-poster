#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qianjin-poster · v2 设计引擎
基于 design-system.md 的专业海报合成：风格 Token + 构图模式 + 装饰语言 + 字阶 + 质感背景。
所有字体必须来自免费商用清单（见 references/font-guide.md）。

用法示例：
  python compose_poster.py --style S1 --layout L1 \
      --product "p.png@0.5,0.5,0.6" \
      --title "暖流从脚底升起" --subtitle "寒从足底起，温热护足" \
      --points "3档温控|15分钟回暖|静音不扰眠" \
      --badge "新品" --seal "暖" --price "¥299" \
      --ratio vertical --out poster.png

  # 促销炸裂
  python compose_poster.py --style S6 --layout L4 \
      --product "p.png" --title "立省200" --subtitle "足底理疗仪 大促" \
      --points "直降¥200|第二件半价|限时3天" --price "¥299" --badge "限时" \
      --ratio vertical --out promo.png
"""
import argparse
import os
import sys
import glob
import random

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.stderr.write("[ERROR] 缺少 Pillow。请先安装：pip install Pillow\n")
    sys.exit(2)

try:
    import fontlib
    HAS_LIB = True
except Exception:
    HAS_LIB = False

# ---------------------------------------------------------------------------
# 设计系统：风格 Token（与 references/styles.md 同步）
#
# 配色方法论（v2.3 重构）：
#   1) 底色低饱和（≤30%），退为"纸/底"的角色，不与内容抢注意力
#   2) 主强调色负责跳脱，与底色形成明度或色相的明确反差
#   3) 次强调色 accent2 用于第二个视觉锚点（印章/点缀），拉开层次
#   4) 文字层级靠"明度阶梯"制造：ink(最深) > ink_soft(中) > 底色(浅)
#   5) 饱和度纪律：除 S6 促销（唯一允许爆色），强调色饱和控制在 45-80%
# 详细配色策略见 references/color-system.md
# ---------------------------------------------------------------------------
STYLES = {
    "S1": {"name": "新中式养生",
           "bg": "#EFEAE1", "bg2": "#DCD2C0",
           "ink": "#1B2434", "ink_soft": "#667080",
           "accent": "#2E4A7D", "accent2": "#B23A2E",
           "surface": "#FAF7F1", "decor": ["seal", "meridian"], "layout": "L1",
           "palette_note": "宣纸白 × 鸢尾蓝，冷调主强调 + 朱红点缀；传统暖米改冷调才有现代张力"},
    "S2": {"name": "国潮",
           "bg": "#1C1526", "bg2": "#33254A",
           "ink": "#F3E4C4", "ink_soft": "#9A8256",
           "accent": "#E8B65A", "accent2": "#C63B3B",
           "surface": "#2A1F3A", "decor": ["rule", "glow"], "layout": "L3",
           "palette_note": "深紫底 × 描金，冷暗底衬暖金，133° 色相反差"},
    "S3": {"name": "极简科技",
           "bg": "#12141A", "bg2": "#1E222C",
           "ink": "#F2F5F8", "ink_soft": "#767F8E",
           "accent": "#4AE3A4", "accent2": "#4A9EFF",
           "surface": "#1A1D25", "decor": ["glow", "geo"], "layout": "L1",
           "palette_note": "近黑底 × 荧光青，原蓝撞蓝改为 71° 跨色域"},
    "S4": {"name": "暖心家居",
           "bg": "#F2EDE4", "bg2": "#E0D6C6",
           "ink": "#223028", "ink_soft": "#6E7D75",
           "accent": "#B85C3A", "accent2": "#3D5A50",
           "surface": "#FCFAF5", "decor": ["glow"], "layout": "L2",
           "palette_note": "奶白 × 陶土橘，墨绿次强调拉开 121°"},
    "S5": {"name": "美食诱惑",
           "bg": "#1F1712", "bg2": "#382519",
           "ink": "#FAF0E2", "ink_soft": "#BC9C7C",
           "accent": "#E39B1F", "accent2": "#C0452A",
           "surface": "#2E2018", "decor": ["glow"], "layout": "L3",
           "palette_note": "深巧克力 × 明黄，同色域内靠明度阶梯拉开层次"},
    "S6": {"name": "促销炸裂",
           "bg": "#C81E1E", "bg2": "#9E1414",
           "ink": "#FFFFFF", "ink_soft": "#FFE0D6",
           "accent": "#FFC72C", "accent2": "#7A1410",
           "surface": "#FFFFFF", "decor": ["burst", "rule"], "layout": "L4",
           "palette_note": "正红 × 亮黄，全系统唯一允许高饱和的爆色风格"},
    "S7": {"name": "杂志封面",
           "bg": "#F1EEE7", "bg2": "#E2DDD1",
           "ink": "#12141A", "ink_soft": "#6B7078",
           "accent": "#2B4C8C", "accent2": "#B23A2E",
           "surface": "#FFFFFF", "decor": ["rule", "grain"], "layout": "L5",
           "palette_note": "宣纸白 × 鸢尾蓝，178° 强对比，编辑风标准配色"},
}

RATIOS = {
    "vertical": (750, 1000), "horizontal": (1920, 1080),
    "square": (1080, 1080), "story": (1080, 1920), "wechat": (1242, 2208),
    # 常见比例别名（用户可直接写 4:5 / 16:9 等）
    "3:4": (750, 1000), "4:5": (800, 1000), "1:1": (1080, 1080),
    "4:3": (1200, 900), "3:2": (1200, 800), "2:3": (800, 1200),
    "16:9": (1920, 1080), "9:16": (1080, 1920), "5:4": (1000, 800),
}

# 免费商用中文字体（OFL / 思源 / 阿里普惠 / 站酷），按文件名关键字识别。
# 优先使用思源/阿里/站酷等明确免费商用字体；系统自带黑体(simhei)商用需授权，仅作兜底。
CN_SANS_KEYS = ["noto sans sc", "notosanssc", "source han sans", "sourcehansans",
                "alibabapuhuiti", "notosanscjksc", "zcool", "simhei"]
CN_SERIF_KEYS = ["noto serif sc", "notoserifsc", "source han serif", "sourcehanserif",
                 "simsun", "song", "kaiti"]
WEIGHT_KEYS = {
    "thin":    ["thin", "hairline", "100", "extralight", "200"],
    "light":   ["light", "300"],
    "regular": ["regular", "normal", "book", "roman", "400", "r-"],
    "medium":  ["medium", "med", "500", "m-"],
    "bold":    ["bold", "600", "700", "semibold", "bd", "b-"],
    "black":   ["black", "heavy", "800", "900", "extrabold", "hg", "h-"],
}
EN_FONT_HINTS = ["Montserrat", "Barlow", "Roboto", "Oswald"]
SYS_FONT_DIRS = ["C:/Windows/Fonts", "/System/Library/Fonts",
                 "/Library/Fonts", os.path.expanduser("~/.fonts"),
                 os.path.expanduser("~/.local/share/fonts")]


# ---------------------------------------------------------------------------
# 字体与工具
# ---------------------------------------------------------------------------
def find_font(explicit, hints, assets_dir):
    """显式路径 / 旧式 hint 解析，仍用于 --font-cn 等手动覆盖。"""
    if explicit:
        if os.path.exists(explicit):
            return explicit
        sys.stderr.write(f"[WARN] 指定字体不存在：{explicit}\n")
    if assets_dir and os.path.isdir(assets_dir):
        for h in hints:
            p = os.path.join(assets_dir, h)
            if os.path.exists(p):
                return p
    for d in SYS_FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for h in hints:
            key = h.lower().replace(".ttf", "").replace(".otf", "").replace(".ttc", "")
            for f in glob.glob(os.path.join(d, "*")):
                base = os.path.basename(f).lower()
                if key in base and base.endswith((".ttf", ".otf", ".ttc")):
                    return f
    return None


def discover_fonts(search_dirs):
    """扫描目录，按 sans/serif + 字重自动分类，返回 {'sans':{w:path},'serif':{w:path}}。

    静态实例优先；可变字体(VF)仅在对应字重缺失时补缺。
    """
    result = {"sans": {}, "serif": {}}
    vf_pool = []  # (cat, w, path) 候选可变字体
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(os.path.join(d, "*"))):
            base = os.path.basename(f).lower()
            if not base.endswith((".ttf", ".otf", ".ttc")):
                continue
            is_serif = any(k in base for k in CN_SERIF_KEYS)
            is_sans = any(k in base for k in CN_SANS_KEYS)
            if not (is_sans or is_serif):
                continue
            cat = "serif" if is_serif else "sans"
            w = "regular"
            for weight, keys in WEIGHT_KEYS.items():
                if any(k in base for k in keys):
                    w = weight
                    break
            is_vf = ("vf" in base) or ("variable" in base)
            if is_vf:
                vf_pool.append((cat, w, f))
            elif w not in result[cat]:
                result[cat][w] = f
    # 可变字体补缺：仅当 (cat, w) 仍缺失
    for cat, w, f in vf_pool:
        if w not in result[cat]:
            result[cat][w] = f
    return result


def pick_cn(discovery, explicit_reg=None, explicit_disp=None, explicit_heavy=None):
    """自动挑选 正文 / 标题(display) / 强调(heavy) 三档，实现真正字阶层级。

    默认：正文=黑体 regular，标题=黑体 bold，强调=黑体 black 或衬线 heavy（制造混搭高级感）。
    """
    sans = discovery.get("sans", {})
    serif = discovery.get("serif", {})
    def first(d, *ws):
        for w in ws:
            if w in d:
                return d[w]
        return None
    cn = (explicit_reg or first(sans, "regular", "light", "medium")
          or first(sans, "bold", "black") or first(serif, "regular"))
    cn_d = (explicit_disp or first(sans, "bold", "black", "medium") or cn)
    cn_h = (explicit_heavy or first(sans, "black", "heavy")
            or first(serif, "black", "heavy", "bold")
            or first(serif, "regular") or cn_d)
    return cn, cn_d, cn_h


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype(path, int(size * 0.92))
        except Exception:
            return ImageFont.load_default()


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_gradient(w, h, c1, c2):
    img = Image.new("RGB", (w, h), c1)
    px = img.load()
    r1, g1, b1 = hex2rgb(c1)
    r2, g2, b2 = hex2rgb(c2)
    for y in range(h):
        t = y / max(1, h - 1)
        for x in range(w):
            px[x, y] = (int(r1 + (r2 - r1) * t),
                        int(g1 + (g2 - g1) * t),
                        int(b1 + (b2 - b1) * t))
    return img


def wrap_text(draw, text, font, max_width):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= max_width:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_spaced(draw, xy, text, font, fill, spacing=0):
    """带字距绘制（caption/小标拉开字距用）。"""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def add_shadow(rgba, scale=1.0, blur=22, offset=(0, 16), alpha=0.30):
    a = rgba.split()[-1]
    shadow = Image.new("L", rgba.size, 0)
    shadow.paste(a, (0, 0), rgba)
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(blur * scale)))
    sh = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    sh.putalpha(shadow)
    sh = sh.point(lambda v: int(v * alpha))
    off = (int(offset[0] * scale), int(offset[1] * scale))
    cv = Image.new("RGBA", (rgba.size[0] + abs(off[0]) + blur,
                             rgba.size[1] + abs(off[1]) + blur), (0, 0, 0, 0))
    cv.paste(sh, (blur + max(0, off[0]), blur + max(0, off[1])), sh)
    cv.paste(rgba, (blur, blur), rgba)
    return cv


def parse_ratio(spec):
    """解析画幅比例。支持三种写法：
       命名   vertical / square / story / wechat ...
       比例   4:5 / 16:9 / 1:1（命中 RATIOS 别名则用标准像素，否则按基准宽 1080 推算）
       自定义 custom:800x1000
    """
    s = (spec or "vertical").strip()
    if s in RATIOS:
        return RATIOS[s]
    if s.startswith("custom:"):
        body = s.split(":", 1)[1].replace("*", "x")
        w, h = body.split("x")[:2]
        return int(w), int(h)
    if ":" in s:                      # 形如 4:5 的比例
        try:
            a, b = s.split(":")[:2]
            a, b = float(a), float(b)
            if b <= 0:
                raise ValueError
            base = 1080 if a <= b else 1920
            w = base
            h = int(round(base * b / a))
            if max(w, h) > 2400:      # 防止超大画布
                k = 2400 / max(w, h)
                w, h = int(w * k), int(h * k)
            return w, h
        except Exception:
            sys.stderr.write(f"[WARN] 无法解析比例 {spec}，回退 vertical\n")
    return RATIOS["vertical"]


def parse_product(spec):
    if "@" in spec:
        path, rest = spec.split("@", 1)
        parts = rest.split(",")
        try:
            cx = float(parts[0]) if len(parts) > 0 else 0.5
        except (ValueError, IndexError):
            cx = 0.5
        try:
            cy = float(parts[1]) if len(parts) > 1 else 0.5
        except (ValueError, IndexError):
            cy = 0.5
        try:
            sc = float(parts[2]) if len(parts) > 2 else 0.55
        except (ValueError, IndexError):
            sc = 0.55
    else:
        path, cx, cy, sc = spec, 0.5, 0.5, 0.55
    return path.strip(), cx, cy, sc


# ---------------------------------------------------------------------------
# 背景质感
# ---------------------------------------------------------------------------
def add_glow(canvas, color, cx, cy, radius, alpha):
    w, h = canvas.size
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r, g, b = hex2rgb(color)
    steps = 6
    for i in range(steps, 0, -1):
        rr = int(radius * i / steps)
        a = int(alpha * (1 - (i - 1) / steps) / steps * 255)
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(r, g, b, a))
    return Image.alpha_composite(canvas, glow)


def add_grain(canvas, alpha=10):
    w, h = canvas.size
    px = canvas.load()
    for _ in range((w * h) // 30):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        r, g, b = px[x, y][:3]
        d = random.randint(-alpha, alpha)
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)),
                    max(0, min(255, b + d), ), 255) if len(px[x, y]) == 3 else (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)), px[x, y][3])
    return canvas


def draw_block(draw, box, color):
    draw.rectangle(box, fill=color)


# ---------------------------------------------------------------------------
# 装饰元素
# ---------------------------------------------------------------------------
def decor_seal(canvas, text, pos, color, font, frac=None):
    w, h = canvas.size
    d = ImageDraw.Draw(canvas)
    # 横屏时印章按短边缩小，避免宽画布上角标过大压住标题（与排版引擎估算一致）
    s = int(min(w, h) * (frac if frac else (0.11 if h >= w else 0.085)))
    pad = int(w * 0.06)
    if pos == "tl":
        xy = (pad, pad)
    elif pos == "bl":
        xy = (pad, h - s - pad)
    else:  # tr
        xy = (w - s - pad, pad)
    # 印章底（圆角方 + 描边）
    d.rounded_rectangle([xy, (xy[0] + s, xy[1] + s)], radius=s * 0.12,
                        fill=color)
    # 内白字
    f = load_font(font, int(s * 0.62))
    tw = d.textlength(text, font=f)
    d.text((xy[0] + (s - tw) / 2, xy[1] + (s - s * 0.62) / 2 - s * 0.02),
           text, font=f, fill="#FFFFFF")
    return canvas


def decor_meridian(canvas, color, base_y, base_x, scale, height=None, top_limit=None):
    """足底经络发光线：从 base_y 向上发散，穴位点在顶端。

    top_limit 给定时，线条被截断在该 y 之上 —— 用于「只露出产品上缘之外的能量感」，
    避免线条伸进文字区。线条应画在产品下层（调用前产品已绘制，故只画露出的部分）。
    """
    d = ImageDraw.Draw(canvas)
    r, g, b = hex2rgb(color)
    H = height or int(300 * scale)
    for i in range(5):
        x0 = base_x + (i - 2) * int(40 * scale)
        x1 = x0 + int((i - 2) * 18 * scale)
        y0 = base_y
        y1 = base_y - H
        # 截断：顶端不得越过 top_limit
        if top_limit is not None and y1 < top_limit:
            y1 = top_limit
        if y1 >= y0 - int(8 * scale):
            continue
        d.line([(x0, y0), (x0 + (x1 - x0) // 2, (y0 + y1) // 2 - 30 * scale),
                (x1, y1)], fill=(r, g, b, 55), width=max(1, int(2 * scale)),
               joint="curve")
        d.ellipse([x1 - 4 * scale, y1 - 4 * scale, x1 + 4 * scale, y1 + 4 * scale],
                  fill=(r, g, b, 95))
    return canvas


def decor_pill(canvas, text, xy, color, font, fill_bg=True):
    d = ImageDraw.Draw(canvas)
    f = load_font(font, int(26 * (canvas.size[0] / 750.0)))
    tw = d.textlength(text, font=f) + 36 * (canvas.size[0] / 750.0)
    h = int(40 * (canvas.size[0] / 750.0))
    box = [xy[0], xy[1], xy[0] + tw, xy[1] + h]
    if fill_bg:
        d.rounded_rectangle(box, radius=h / 2, fill=color)
        d.text((xy[0] + 18 * (canvas.size[0] / 750.0),
                xy[1] + (h - f.size) / 2), text, font=f, fill="#FFFFFF")
    else:
        d.rounded_rectangle(box, radius=h / 2, outline=color, width=2)
        d.text((xy[0] + 18 * (canvas.size[0] / 750.0),
                xy[1] + (h - f.size) / 2), text, font=f, fill=color)
    return canvas


def decor_burst(canvas, text, center, color, ink, font):
    w, h = canvas.size
    d = ImageDraw.Draw(canvas)
    R = int(min(w, h) * 0.13)
    pts = []
    import math
    for i in range(20):
        ang = math.pi * 2 * i / 20
        rr = R if i % 2 == 0 else R * 0.78
        pts.append((center[0] + rr * math.cos(ang),
                    center[1] + rr * math.sin(ang)))
    d.polygon(pts, fill=color)
    f = load_font(font, int(R * 0.5))
    tw = d.textlength(text, font=f)
    d.text((center[0] - tw / 2, center[1] - f.size / 2), text, font=f, fill=ink)
    return canvas


def decor_rule(canvas, x1, y1, x2, y2, color, width=3):
    ImageDraw.Draw(canvas).line([x1, y1, x2, y2], fill=color, width=width)
    return canvas


# ---------------------------------------------------------------------------
# 文案块布局（按构图模式）
# ---------------------------------------------------------------------------
def text_zones(layout, W, H, has_product_cy):
    m = int(W * 0.06)
    if layout == "L1":  # 对称聚焦：标题顶部居中，产品居中，利益点底部居中
        return {
            "title": (W / 2, H * 0.07, "center", W - 2 * m),
            "subtitle": (W / 2, H * 0.185, "center", W - 2 * m),
            "points": (W / 2, H * 0.84, "center", W - 2 * m),
            "product": (0.5, 0.50, 0.60),
        }
    if layout == "L2":  # 非对称对角线：文字左上，产品右下
        return {
            "title": (m, H * 0.10, "left", W * 0.62),
            "subtitle": (m, H * 0.235, "left", W * 0.62),
            "points": (m, H * 0.82, "left", W * 0.6),
            "product": (0.64, 0.58, 0.62),
        }
    if layout == "L3":  # 满版前景：产品放大居中，文字压上(带色块)
        return {
            "title": (W / 2, H * 0.06, "center", W - 2 * m),
            "subtitle": (W / 2, H * 0.165, "center", W - 2 * m),
            "points": (W / 2, H * 0.88, "center", W - 2 * m),
            "product": (0.5, 0.50, 0.74),
        }
    if layout == "L4":  # 三分法：左栏文字，右栏产品
        # 标题上移到 0.22H、产品缩到 0.52：原 0.30H + 0.58 尺寸下，
        # 标题 2 行就占满文字区，副标题被挤出画面
        return {
            "title": (m, H * 0.20, "left", W * 0.44),
            "subtitle": (m, H * 0.44, "left", W * 0.44),
            "points": (m, H * 0.74, "left", W * 0.44),
            "product": (0.71, 0.52, 0.50),
        }
    # L5 色块切割：左侧深底色块放文字，右侧产品
    return {
        "title": (m + 20, H * 0.21, "left", W * 0.36),
        "subtitle": (m + 20, H * 0.45, "left", W * 0.36),
        "points": (m + 20, H * 0.76, "left", W * 0.36),
        "product": (0.72, 0.50, 0.52),
        "block": (0, H * 0.16, W * 0.44, H * 0.86),
    }


def place_text(draw, zone, text, font, fill, align):
    x, y, _, maxw = zone
    for ln in wrap_text(draw, text, font, maxw):
        tw = draw.textlength(ln, font=font)
        tx = x - tw / 2 if align == "center" else x
        draw.text((tx, y), ln, font=font, fill=fill)
        y += int(font.size * 1.2)
    return y


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="qianjin-poster v2 设计引擎")
    ap.add_argument("--style", default="S1", choices=list(STYLES))
    ap.add_argument("--layout", default=None, choices=["L1", "L2", "L3", "L4", "L5"])
    ap.add_argument("--layer", action="append", default=[],
                help="透明部件 PNG：path@cx,cy,scale（可多次）")
    ap.add_argument("--callout", action="append", default=[],
                    help="分层标签：文字@cx,cy,关联产品序号(从1起),方向(l|r),如 '航空铝中框@0.22,0.42,1,l'")
    ap.add_argument("--callout-style", default="leader",
                    help="引导线样式：leader(折线) / horizontal(水平线，标签自动对齐层中心) "
                         "/ dot(点线) / none(仅文字)")
    ap.add_argument("--callout-align", default="auto",
                    help="标签纵向对齐：auto(自动均分，与层中心对齐) / free(用 @cy 自由定位)")
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--points", default="")
    ap.add_argument("--price", default="")
    ap.add_argument("--badge", default="")
    ap.add_argument("--seal", default="")
    ap.add_argument("--logo", default=None)
    ap.add_argument("--logo-pos", default="bottom-right")
    ap.add_argument("--en", default="", help="英文 slogan/tagline，用西文字体（Playfair/Montserrat）排")
    ap.add_argument("--ratio", default="vertical")
    ap.add_argument("--out", default="poster.png")
    ap.add_argument("--font-cn", default=None)
    ap.add_argument("--font-cn-display", default=None)
    ap.add_argument("--font-cn-heavy", default=None)
    ap.add_argument("--font-en", default=None)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--assets", default=None)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    random.seed(args.seed)

    W, H = parse_ratio(args.ratio)
    # scale 以宽度为基准，但横屏(w>h)时高度才是约束：按短边封顶，
    # 否则 16:9 下 scale=2.56 会把标题字号撑到 200+px，垂直空间直接爆掉
    scale = W / 750.0
    if H < W:
        scale = min(scale, (H / 1000.0) * 1.15)
    st = STYLES[args.style]
    layout = args.layout or st["layout"]

    here = os.path.dirname(os.path.abspath(__file__))
    af = args.assets or os.path.join(os.path.dirname(here), "assets", "fonts")

    # ---- 角色化取字（fontlib + font_index.json）----
    entries = fontlib.load_index(af) if HAS_LIB else None
    resolved = None
    if entries:
        resolved = fontlib.resolve(entries, args.style)

        def rpath(role):
            e = resolved.get(role)
            return os.path.join(af, e["file"]) if e else None

        def rfamily(role):
            e = resolved.get(role)
            return e["family"] if e else "None"

        title_path = args.font_cn_display or rpath("title_cn") or rpath("body_cn")
        body_path = args.font_cn or rpath("body_cn")
        emph_path = args.font_cn_heavy or rpath("emphasis_cn") or rpath("body_cn")
        price_path = rpath("display_number") or rpath("body_cn")
        latin_serif_path = rpath("latin_serif") or rpath("body_cn")
        latin_sans_path = rpath("latin_sans") or rpath("body_cn")
        hand_path = rpath("handwriting") or emph_path
    else:
        # 旧逻辑兜底（无索引/无 fontlib 时）
        search_dirs = ([af] if af and os.path.isdir(af) else []) + SYS_FONT_DIRS
        disc = discover_fonts(search_dirs)
        cn, cn_d, cn_h = pick_cn(disc, args.font_cn, args.font_cn_display, args.font_cn_heavy)
        body_path, title_path, emph_path = cn, cn_d, cn_h
        price_path, latin_serif_path, latin_sans_path, hand_path = cn_d, cn, cn, cn_h
        rfamily = lambda r: "legacy"

    if not body_path or not os.path.exists(body_path):
        sys.stderr.write("[ERROR] 未找到免费商用中文字体，请先运行 scripts/setup_fonts.py。\n")
        sys.exit(3)

    sys.stderr.write(
        f"[FONT] 风格={args.style} 正文={os.path.basename(body_path)} | "
        f"标题={os.path.basename(title_path)} | 强调={os.path.basename(emph_path)} | "
        f"价格={os.path.basename(price_path)}\n")

    def _load_role(role, size, wght=None):
        """按角色加载字体；可变字体按 wght 实例化，保证标题足够重。"""
        if entries and resolved:
            e = resolved.get(role)
            if e:
                f = fontlib.load_font(entries, af, e, int(size), wght)
                if f is not None:
                    return f
        p = {"title_cn": title_path, "body_cn": body_path, "emphasis_cn": emph_path,
             "display_number": price_path, "latin_serif": latin_serif_path,
             "latin_sans": latin_sans_path, "handwriting": hand_path}.get(role, body_path)
        return load_font(p, int(size))

    # 背景：渐变 + 光晕 + (L5 色块)
    canvas = make_gradient(W, H, st["bg"], st["bg2"]).convert("RGBA")
    canvas = add_glow(canvas, st["bg2"], int(W * 0.5), int(H * 0.4),
                      int(min(W, H) * 0.6), 0.22)
    canvas = add_glow(canvas, st["accent"], int(W * 0.82), int(H * 0.2),
                      int(min(W, H) * 0.28), 0.10)

    zones = text_zones(layout, W, H, 0.5)
    if "block" in zones:  # L5 色块切割
        decor_block_xy = [int(zones["block"][0] * 1), int(zones["block"][1]),
                          int(zones["block"][2]), int(zones["block"][3])]
        draw_block(ImageDraw.Draw(canvas), decor_block_xy, st["surface"])

    # 装饰：经络线（在放产品前画于底层）
    if "meridian" in st["decor"] and args.layer:
        pass  # 产品放置后补画

    # 产品放置（带阴影）
    # 两阶段：① 解析几何与初判位置 ② 文字块需要更多空间时，产品自动下移让位
    prod_bottom = None
    prod_top = None
    prod_cx = None
    prod_geo = []          # [(img_rgba, shadow_rgba, left, top, tw, th, cx, cy)]
    for spec in args.layer:
        path, cx, cy, sc = parse_product(spec)
        if not os.path.exists(path):
            sys.stderr.write(f"[WARN] 产品图不存在：{path}\n")
            continue
        prod = Image.open(path).convert("RGBA")
        target = int(min(W, H) * sc)
        r = target / max(prod.width, prod.height)
        tw, th = int(prod.width * r), int(prod.height * r)
        prod = prod.resize((tw, th), Image.LANCZOS)
        sh = add_shadow(prod, scale=scale)
        sw, shh = sh.size
        left = int(cx * W - tw / 2) - (sw - tw) // 2
        top = int(cy * H - th / 2) - (shh - th) // 2
        prod_geo.append([prod, sh, left, top, tw, th, cx, cy])

    # 预估文字块总高（标题2行 + 副标题 + 英文 + 段间距），用于给产品定让位量
    # 文字块估算：标题2行 + 分割线 + 副标 + 英文 + 段距（对齐 v2.3 字阶，按栏宽分档）
    _r = zones["title"][3] / max(W, 1)
    _tt = (112 if _r >= 0.50 else 84 if _r >= 0.34 else 66) * scale
    _ts = (28 if _r >= 0.50 else 30) * scale
    # 英文不计入必要高度 —— 降级优先级：标题 > 副标题 > 卖点 > 英文
    # 英文进估算会挤掉副标题（曾经的问题）
    # 末尾 +30px 安全余量：实际流排会累积 rule(22) + gap(16) + 行高舍入误差，
    # 估算不留余量会导致副标题刚好差十几像素放不下（原 467 vs 478 的根因）
    _est = (int(2 * _tt * 1.18) + int(18 * scale) + int(16 * scale)
            + int(_ts * 1.25) + int(20 * scale) + int(30 * scale))
    # 先把每个产品的落点补算完整（left 可能为 None），保证后续几何一致
    for g in prod_geo:
        if g[2] is None:
            g[2] = int(g[6] * W - g[4] / 2) - (g[1].width - g[4]) // 2

    if prod_geo:
        # 起点须与「眉标让位后的实际标题 y」一致 —— 角标在顶部时标题会下移到
        # corner_bottom+18，若仍按 H*0.10 估算会低估 50~80px，导致让位量不足
        _start = zones["title"][1]
        _corner_bottom = 0
        if args.badge:
            _corner_bottom = max(_corner_bottom, int(H * 0.06) + int(40 * scale))
        if args.seal:
            _sfrac = 0.11 if H >= W else 0.085
            _corner_bottom = max(_corner_bottom,
                                 int(H * 0.06) + int(min(W, H) * _sfrac))
        if _corner_bottom and zones["title"][2] == "center" and _start < _corner_bottom:
            _start = _corner_bottom + int(18 * scale)
        _need_bottom = int(_start) + (_est if args.title else 0)
        _pts_h = int(len([p for p in args.points.split("|") if p.strip()])
                     * 20 * scale * 1.6) if args.points else 0
        _room = H - int(24 * scale) - _pts_h
    # 分层解构：所有与文字区水平重叠的产品都要让位（上层元素最易压字）
    # 但逐层悬浮海报里，层堆位置是刻意错位的（下移会破坏层间节奏），
    # 故 horizontal 样式下跳过让位 —— 改由调用方自行安排层位。
    _skip_push = (args.callout_style == "horizontal" and args.callout)
    for _g in ([] if _skip_push else prod_geo):
            _t = int(_g[7] * H - _g[5] / 2)
            _b = int(_g[7] * H + _g[5] / 2)
            _ov = abs(_g[6] - 0.5) < 0.42
            if not _ov or _t >= _need_bottom:
                continue
            push = min(_need_bottom - _t, int(H * 0.22))
            if _pts_h == 0 or (_b + push) <= _room:
                _g[3] += push
                _g.append(("pushed", push))
            else:
                # 下移会挤掉卖点 → 缩小产品保文字完整
                _still = _need_bottom - _t - int(H * 0.22)
                if _still > 0:
                    _k = max(0.70, 1.0 - _still / max(_g[5], 1))
                    if _k < 0.995:
                        _nw, _nh = int(_g[4] * _k), int(_g[5] * _k)
                        _cx0 = _g[6] * W
                        _g[0] = _g[0].resize((_nw, _nh), Image.LANCZOS)
                        _g[1] = add_shadow(_g[0], scale=scale)
                        _g[2] = int(_cx0 - _nw / 2) - (_g[1].width - _nw) // 2
                        _g[3] = int(_g[7] * H - _nh / 2) - (_g[1].height - _nh) // 2
                        _g[4], _g[5] = _nw, _nh
                        _g.append(("shrunk", _k))
                        _t2 = int(_g[7] * H - _nh / 2)
                        if _t2 < _need_bottom:
                            _add = min(_need_bottom - _t2, int(H * 0.12))
                            if _pts_h == 0 or (_t2 + _nh + _add) <= _room:
                                _g[3] += _add
    # 多产品时取「全局并集」作为视觉主体：
    # prod_top = 最高产品的上缘（决定文字天花板）
    # prod_bottom = 最低产品的下缘（决定卖点/标签避让）
    # prod_cx = 主体中心 x（居中轴用）
    # 若只取最后一个产品的几何，分层场景的上层元素会压掉文字（曾导致副标题消失）
    prod_bottom = prod_top = prod_cx = None
    for g in prod_geo:
        _t = g[3]
        _b = _t + g[5]
        if prod_top is None:
            prod_top, prod_bottom, prod_cx = _t, _b, g[6] * W
        else:
            prod_top = min(prod_top, _t)
            prod_bottom = max(prod_bottom, _b)
            # 主体中心取最靠近画面中心的那个（视觉重心更准）
            if abs(g[6] - 0.5) < abs(prod_cx / W - 0.5):
                prod_cx = g[6] * W

    # 经络线：画在产品**下层**（本段在贴产品之前执行，故线条被产品遮挡）。
    # 从产品下缘向上发散，只露出产品上缘以上、角标带以下的一段 —— 用固定比例带，
    # 不依赖文字变量（此时 title_y/TS_* 尚未定义）。
    if "meridian" in st["decor"] and prod_top is not None and prod_bottom is not None:
        # 顶端取「画面上方 34%」处：介于角标带与产品上缘之间的典型位置
        _tb = int(H * 0.34)
        if prod_top > _tb + int(40 * scale):
            decor_meridian(canvas, st.get("accent2", st["accent"]),
                            prod_bottom, prod_cx, scale,
                            height=(prod_bottom - _tb),
                            top_limit=_tb)

    for g in prod_geo:
        prod, sh, left, top, tw, th, cx, cy = g[:8]
        if top is None:                      # 未经下移循环时的兜底
            top = int(cy * H - th / 2) - (sh.height - th) // 2
            g[3] = top
        canvas.paste(sh, (left, top), sh)

    # --- 分层解构标签（悬浮分层海报的核心信息层）---
    # 每条 --callout 形如 "文字@cx,cy,产品序号,方向"，
    # 绘制「折线引导 + 端点圆点 + 标签文字」，把部件与卖点对应起来。
    # 收集每个产品的包围盒，供引导线指向
    _boxes = []
    for g in prod_geo:
        _p, _s, _l, _t, _w, _h, _cx0, _cy0 = g[:8]
        # 包围盒必须用「最终落点」：left/top 可能为 None（贴图时才补算），
        # 而产品下移会改写 g[3]，故此处按 cx/cy + 实际 top 重新推导 left
        _tt = g[3]
        _ll = int(_cx0 * W - _w / 2)
        _boxes.append((_ll, _tt, _ll + _w, _tt + _h))

    callout_boxes = []          # 标签包围盒，供价格贴/卖点避让
    if args.callout:
        _cd = ImageDraw.Draw(canvas)
        _cf = _load_role("body_cn", 19 * scale, 500)
        _acc = st.get("accent2", st["accent"])
        _gap_line = int(26 * scale)
        # 预解析所有标签，按「指向的产品序号」分组 ——
        # 用于给同产品的多条线分配不同的纵向锚点，避免重叠
        _parsed = []            # [(txt, cx, cy, idx, side), ...]
        for sp in args.callout:
            sp = sp.strip()
            if not sp or "@" not in sp:
                _parsed.append(None)
                continue
            _t_, _r_ = sp.rsplit("@", 1)
            _ps_ = _r_.split(",")
            _parsed.append((
                _t_,
                float(_ps_[0]) if len(_ps_) > 0 else 0.5,
                float(_ps_[1]) if len(_ps_) > 1 else 0.5,
                int(float(_ps_[2])) if len(_ps_) > 2 else 1,
                _ps_[3].strip().lower() if len(_ps_) > 3 else "l",
            ))
        _by_prod = {}
        for _i, _pp in enumerate(_parsed):
            if _pp:
                _by_prod.setdefault(_pp[3], []).append(_i)
        # --callout-align auto：标签纵向自动对齐到目标层的垂直中心。
        # 这是「垂直逐层悬浮 + 左侧标签列」类海报的关键 —— 标签与层一一对齐，
        # 水平引线才成立（对齐不上的话引线会斜着走，视觉杂乱）。
        if args.callout_align == "auto" and args.callout_style == "horizontal":
            for _i, _pp in enumerate(_parsed):
                if not _pp:
                    continue
                _txt_, _cx_, _cy_, _idx_, _side_ = _pp
                if 1 <= _idx_ <= len(_boxes):
                    _bl, _bt, _br, _bb = _boxes[_idx_ - 1]
                    _parsed[_i] = (_txt_, _cx_, (_bt + _bb) / 2 / H, _idx_, _side_)
        for _pi, _pp in enumerate(_parsed):
            if not _pp:
                continue
            txt, cxx, cyy, idx, side = _pp
            # 标签文字锚点：cx,cy 表示文字**右缘**(side=l) / **左缘**(side=r) 的位置
            # 越界保护：文字必须在画布内，否则会被裁切
            tw = _cd.textlength(txt, font=_cf)
            tx, ty = cxx * W, cyy * H
            m_pad = int(18 * scale)
            if side == "l":
                tx = min(tx, W - m_pad)          # 右缘不越界
                tx = max(tx, tw + m_pad)         # 左缘不越界
            else:
                tx = max(tx, m_pad)              # 左缘不越界
                tx = min(tx, W - tw - m_pad)     # 右缘不越界
            ty = min(max(ty, _cf.size), H - m_pad)
            # 引导线指向的产品边缘：取该侧轮廓，按「标签纵向顺序」在产品高度上分点。
            # 多条线指同一产品时若都取中点会重叠成一坨，按序分配不同锚点才清晰。
            if 1 <= idx <= len(_boxes):
                bl, bt, br, bb = _boxes[idx - 1]
                tgt_x = bl if side == "l" else br
                if args.callout_style == "horizontal":
                    tgt_y = (bt + bb) / 2               # 水平引线：取层中心
                else:
                    _same = _by_prod.get(idx, [])       # 指向同一产品的标签序号
                    _rank = _same.index(_pi) if _pi in _same else 0
                    _n = max(len(_same), 1)
                    tgt_y = bt + (bb - bt) * (0.22 + 0.56 * (_rank / (_n - 1) if _n > 1 else 0))
            else:                                  # 无对应产品时指向画面中心
                tgt_x, tgt_y = W / 2, H / 2
            if args.callout_style == "horizontal":
                # 水平引线：标签 → 该层边缘，端点小圆点。
                # 前提是 auto 对齐已把标签 ty 校准到层中心，故 ty ≈ tgt_y。
                if args.callout_style != "none":
                    _cd.line([(tx, ty), (tgt_x, tgt_y)],
                             fill=_acc, width=max(1, int(2 * scale)))
                    _r_ = 4 * scale
                    _cd.ellipse([tgt_x - _r_, tgt_y - _r_, tgt_x + _r_, tgt_y + _r_],
                                fill=_acc)
            else:
                # 折线：标签 → 中继点 → 产品目标点
                # 中继点取「标签与产品之间的中点」：先水平离开标签，再折向产品。
                mid_x = (tx + tgt_x) / 2
                if args.callout_style != "none":
                    _cd.line([(tx, ty), (mid_x, ty), (tgt_x, tgt_y)],
                             fill=_acc, width=max(1, int(2 * scale)), joint="curve")
                    _cd.ellipse([tgt_x - 4 * scale, tgt_y - 4 * scale,
                                 tgt_x + 4 * scale, tgt_y + 4 * scale], fill=_acc)
            if side == "l":
                _cd.text((tx - tw, ty - _cf.size * 0.62), txt, font=_cf,
                         fill=st["ink"])
                callout_boxes.append((tx - tw, ty - _cf.size * 0.62,
                                       tx, ty + _cf.size * 0.62))
            else:
                _cd.text((tx, ty - _cf.size * 0.62), txt, font=_cf,
                         fill=st["ink"])
                callout_boxes.append((tx, ty - _cf.size * 0.62,
                                       tx + tw, ty + _cf.size * 0.62))

    def _hit_callout(x0, y0, x1, y1):
        """区域是否与任一标签重叠"""
        for a, b, c, d in callout_boxes:
            if not (x1 < a or x0 > c or y1 < b or y0 > d):
                return True
        return False

    # 文字
    draw = ImageDraw.Draw(canvas)
    # --- 字阶 Type Scale（v2.3）---
    # 层级感来自「字阶落差」：主标 : 副标 : 正文 : 角标 ≥ 4:1 / 1.5:1 / 1.2:1
    # 旧版 84:38:27:19 = 2.2:1 层级扁平；现 112:28:20:16 = 4:1 大字压场
    #
    # 窄栏适配：L5 文字栏宽仅画布 36%，沿用 112px 会把标题挤成三行碎块。
    # 故按栏宽分三档 —— 宽栏(≥50%)用 Display 大字压场，
    # 中栏(36-50%)用 H1，L4/L5 极窄栏(<36%)再降到 H2 保住完整行数与可读性。
    _zone = text_zones(layout, W, H, 0.5)
    _title_zone_w = _zone["title"][3]
    _ratio = _title_zone_w / max(W, 1)
    if _ratio >= 0.50:
        TS_TITLE, TS_SUB = int(112 * scale), int(28 * scale)   # 宽栏 Display
    elif _ratio >= 0.34:
        TS_TITLE, TS_SUB = int(84 * scale), int(30 * scale)    # 中栏 H1
    else:
        TS_TITLE, TS_SUB = int(66 * scale), int(28 * scale)    # 极窄栏 H2
    TS_POINT = int(20 * scale)        # 正文/卖点
    TS_CAP = int(16 * scale)          # 角标 Caption
    TS_EN = int(24 * scale)           # 英文点缀
    f_sub = _load_role("body_cn", TS_SUB, 400)
    f_pt = _load_role("body_cn", TS_POINT, 400)
    f_cap = _load_role("body_cn", TS_CAP, 400)
    f_en = _load_role("latin_serif", TS_EN, 400)

    # --- 标题区自适应（三级策略，优先保字号与全宽张力） ---
    # ① 眉标让位：角标(badge/印章)与居中大标题同处顶部一个水平带时，
    #    优先把标题整体下移到角标之下，而不是把标题挤窄（挤窄会毁掉居中大标题的视觉张力）
    # ② 宽度避让：下移后空间仍不足时，才退化为收窄 maxw 让开左右角标，并留足安全边距
    # ③ 字号自适应：自动缩字号，控行数 ≤2、避免孤字行
    m_ = int(W * 0.06)
    tz = zones["title"]
    title_y = tz[1]
    title_maxw = tz[3]

    # 产品包围盒（水平范围用于判断是否需要垂直避让）
    prod_box = None
    if prod_top is not None and prod_bottom is not None:
        # 多产品：水平区间取并集（任一产品与文字重叠即判重叠），避免漏判上层元素
        lo_all, hi_all = None, None
        for spec in args.layer:
            p_, cx_, cy_, sc_ = parse_product(spec)
            if not os.path.exists(p_):
                continue
            with Image.open(p_) as im_:
                r = int(min(W, H) * sc_) / max(im_.width, im_.height)
                pw = im_.width * r
            plo, phi = cx_ * W - pw / 2, cx_ * W + pw / 2
            lo_all = plo if lo_all is None else min(lo_all, plo)
            hi_all = phi if hi_all is None else max(hi_all, phi)
        if lo_all is not None:
            prod_box = (lo_all, hi_all, prod_top, prod_bottom)

    def _h_overlap(lo, hi):
        """文字水平区间 [lo,hi] 是否与产品水平区间重叠"""
        if prod_box is None:
            return True          # 无产品信息时保守处理
        return not (hi < prod_box[0] or lo > prod_box[1])

    # 角标实际包围盒（与 decor_pill / decor_seal 的几何保持一致）
    # corner_box 记录每个角标的水平区间，只让与标题水平冲突的那部分生效
    # 横屏（宽>高）时角标按短边缩放：否则 0.11*min 边长在宽画布上过大，
    # 角标底边会高到把标题挤进产品区，导致让位/避让双双失效。
    corner_bottom = 0
    corner_spans = []          # [(lo, hi)] 角标水平覆盖区间
    seal_frac = 0.11 if H >= W else 0.085
    if args.badge:
        bf = load_font(body_path, int(26 * scale))
        bw = draw.textlength(args.badge, font=bf) + 36 * scale
        corner_spans.append((m_, m_ + bw))
        corner_bottom = max(corner_bottom, int(H * 0.06) + int(40 * scale))
    if args.seal:
        ss = int(min(W, H) * seal_frac)
        s_pad = int(W * 0.06)
        corner_spans.append((W - s_pad - ss, W - s_pad))
        corner_bottom = max(corner_bottom, int(H * 0.06) + ss)

    def _corner_conflict(lo, hi):
        """标题水平区间是否与任一角标水平重叠（留安全边距）"""
        pad_ = int(18 * scale)
        for clo, chi in corner_spans:
            if not (hi + pad_ <= clo or lo - pad_ >= chi):
                return True
        return False

    # ① 眉标让位：标题与角标同处顶部一个水平带时，把标题下移到角标之下。
    #    判据是「让位后能否容纳完整文字块」——若让位会挤掉副标题/英文，则不让位。
    #    对居中标题：任一角标冲突即让位；对左/右对齐：只让与该侧冲突的角标生效。
    dropped = False
    if corner_bottom > 0 and title_y < corner_bottom:
        if tz[2] == "center":
            t_lo_e, t_hi_e = 0, W
        else:
            t_lo_e, t_hi_e = tz[0], tz[0] + title_maxw
        if _corner_conflict(t_lo_e, t_hi_e):
            need_y = corner_bottom + int(18 * scale)
            _r2 = tz[3] / max(W, 1)
            _tt2 = (112 if _r2 >= 0.50 else 84 if _r2 >= 0.34 else 66) * scale
            _ts2 = (28 if _r2 >= 0.50 else 30) * scale
            est_block = (int(2 * _tt2 * 1.18) + int(18 * scale) + int(16 * scale)
                         + int(_ts2 * 1.25) + int(20 * scale) + int(24 * scale * 1.25))
            if prod_top is None or need_y + est_block <= prod_top:
                title_y = need_y
                dropped = True
            elif prod_top is None or need_y + int(90 * scale) < prod_top:
                title_y = corner_bottom + int(6 * scale)
                dropped = True
    # ② 宽度避让（仅居中标题需要）：让开左右角标并留足安全边距
    if not dropped and tz[2] == "center" and tz[1] < 0.20 * H and corner_spans:
        if _corner_conflict(W / 2 - title_maxw / 2, W / 2 + title_maxw / 2):
            safe = 30 * scale
            # 左边界：胶囊右缘（无胶囊则用页边距）；右边界：印章左缘（无印章则用页边距）
            left_edge = (corner_spans[0][1] if args.badge else m_) + safe
            right_edge = (W - int(W * 0.06) - int(min(W, H) * seal_frac) - safe
                          if args.seal else W - m_ - safe)
            gap = right_edge - left_edge
            if gap > 200 * scale:
                title_maxw = int(min(tz[3], gap))

    # ③ 垂直天花板：仅在文字水平范围与产品重叠时生效（左右分栏构图不受此限）
    #    用「实际渲染宽度」而非 maxw 判定重叠，避免窄栏文字被误判为压到产品
    if args.title:
        probe = _load_role("title_cn", int(84 * scale), 700)
        probe_lines = wrap_text(draw, args.title, probe, title_maxw)
        t_w = (max(draw.textlength(l, font=probe) for l in probe_lines)
               if probe_lines else 0)
    else:
        t_w = title_maxw
    if tz[2] == "center":
        t_lo, t_hi = tz[0] - t_w / 2, tz[0] + t_w / 2
    else:
        t_lo, t_hi = tz[0], tz[0] + t_w
    text_ceiling = ((prod_top - int(16 * scale))
                    if (_h_overlap(t_lo, t_hi) and prod_top is not None) else H)
    # 分层解构模式：文字区必须让开层堆顶部（最上层产品之上才允许放字）。
    # 层堆位置是刻意错位的，不能靠「产品下移」解决 —— 只能压文字天花板。
    if args.callout_style == "horizontal" and args.callout and prod_geo:
        _min_layer_top = min(g[3] for g in prod_geo if g[3] is not None)
        if _min_layer_top < text_ceiling:
            text_ceiling = _min_layer_top - int(34 * scale)

    # --- 视觉轴贯穿（v2.4）---
    # 问题：文字各自居中/贴边，产品孤立居中，缺少贯穿画面的对位关系 → 版式散。
    # 做法：文字锚点与产品视觉重心对齐，形成一条隐含的垂直轴。
    #   左对齐构图（L2/L4/L5）：锚点吸到产品左缘，形成左轴
    #   居中构图（L1/L3）：保持中轴，但文字块宽度收窄到与产品等宽，
    #                     使「文字块 + 产品」在视觉上成为一组而非两块
    axis_mode = "center"
    axis_x = tz[0]                      # 锚点直接取自 title zone
    axis_align = tz[2]
    axis_maxw = title_maxw
    if axis_align == "center":
        if prod_box is not None:
            p_w = prod_box[1] - prod_box[0]
            # 文字块宽度与产品建立视觉组：宽度 = 产品宽 + 两侧余量，但不小于 0.62W。
            # 下限很重要 —— 收窄过多会让长标题被迫多行，高度暴涨后挤掉副标题
            # （曾因收到 0.42W 导致标题 2 行变 3 行，副标题直接消失）
            pad = int(40 * scale)
            _floor = 0.62 if not args.callout else 0.86   # 有分层标签时放宽：
            # 标签本就占据两侧，文字块可接近全宽（标签与文字不在同一水平带）
            axis_maxw = int(min(title_maxw, max(p_w + pad * 2, W * _floor)))
    elif prod_box is not None:
        p_lo, p_hi = prod_box[0], prod_box[1]
        # 文字栏在左、产品在右 → 锚点吸到产品左缘形成左轴
        axis_x = p_lo + int(8 * scale)
        axis_mode = "left-axis"

    f_title = None
    if args.title:
        base_pt = TS_TITLE                     # 宽栏 112 / 中栏 84 / 极窄栏 66
        floor_pt = max(int(30 * scale), int(base_pt * 0.62))
        # 行数上限：宽栏 2 行保张力；窄栏放宽到 3 行（杂志/分栏排版本就是多行），
        # 否则 15 字标题在 330px 栏宽下物理上放不进 2 行，只能被压成碎块
        max_lines = 3 if _ratio < 0.50 else 2
        # 副标题预留：标题不得把副标题挤出画面（有副标题时至少留 1 行高度）
        # 预留从最小必要值起步（副标 1 行 + 段距），英文不预留 ——
        # 英文是锦上添花，让位于副标题是正确取舍
        _sub_reserve = (int(TS_SUB * 1.25) + int(20 * scale)) if args.subtitle else 0
        _need_tail = _sub_reserve
        s = base_pt
        best = None
        best_fallback = None
        while s >= floor_pt:
            ff = _load_role("title_cn", s, 700)
            lines_try = wrap_text(draw, args.title, ff, axis_maxw)
            orphan = len(lines_try) > 1 and len(lines_try[-1].strip()) == 1
            fits = (title_y + int(len(lines_try) * s * 1.18) + _need_tail
                    <= text_ceiling)
            n_lines = len(lines_try)
            if n_lines <= max_lines and not orphan and fits:
                best = ff
                break
            # 备选：行数少（≤2 行）且为副标题留位 ——
            # 窄栏下「小字 2 行 + 完整副标」优于「大字 3 行 + 副标被挤掉」
            if (n_lines <= 2 and not orphan and fits and best_fallback is None):
                best_fallback = ff
            s -= 3
        if best is None:
            best = best_fallback
        if best is not None:
            f_title = best
        else:
            f_title = _load_role("title_cn", floor_pt, 700)
            if len(args.title) > 8 and _ratio < 0.50:
                sys.stderr.write(
                    f"[WARN] 窄栏（{_ratio*100:.0f}%）下 {len(args.title)} 字标题无法排进 "
                    f"{max_lines} 行且不压产品，建议改用更短标题或改用宽栏构图 L1/L2\n")
    else:
        f_title = _load_role("title_cn", TS_TITLE, 700)

    # 动态流排：标题/副标题/英文按实际渲染高度依次堆叠，杜绝换行重叠
    anchor_x, anchor_align = axis_x, axis_align
    GAP = int(18 * scale)
    y_cur = title_y
    dropped_flow = []

    def _flow(text, role, base_pt, wght, color, maxw, rule=False, gap=None,
              tag="", shrink=True, min_ratio=0.62, must_keep=False):
        """渲染一段文字并推进 y_cur。

        天花板按「本段实际渲染宽度」独立判定是否与产品水平重叠：
        窄栏文字即使纵向进入产品区，只要横向不重叠就允许渲染（左右分栏构图常见）。
        空间不足时先按 min_ratio 渐进缩字号（保留内容），仍放不下才整段省略。
        must_keep=True 用于主标题：缩到绝对下限也要渲染，绝不丢弃。
        """
        nonlocal y_cur
        if not text:
            return
        maxw = int(maxw)
        extra = int(22 * scale) if (rule and "rule" in st["decor"]) else 0
        floor_px = max(int(base_pt * min_ratio), int(16 * scale))

        def seg_range(seg_font, seg_lines):
            sw = max(draw.textlength(l, font=seg_font) for l in seg_lines)
            if anchor_align == "center":
                return anchor_x - sw / 2, anchor_x + sw / 2
            return anchor_x, anchor_x + sw

        def try_size(pt):
            f = _load_role(role, pt, wght)
            ls = wrap_text(draw, text, f, maxw)
            if not ls:
                return None, None
            lo, hi = seg_range(f, ls)
            lh = 1.18 if pt > 40 * scale else 1.25
            need = y_cur + int(len(ls) * pt * lh) + extra
            ok = (need <= text_ceiling) or (text_ceiling >= H) or (not _h_overlap(lo, hi))
            return (f, ls) if ok else (None, None)

        font = lines = None
        pt = int(base_pt)
        f0, l0 = try_size(pt)
        if f0 is not None:
            font, lines = f0, l0
        elif shrink or must_keep:
            # must_keep（标题）：一路缩到绝对下限也要渲染出来，绝不丢弃主标题
            bottom = int(16 * scale) if must_keep else floor_px
            while pt > bottom:
                pt = max(int(pt * 0.92), bottom)
                f1, l1 = try_size(pt)
                if f1 is not None:
                    font, lines = f1, l1
                    break
                if pt <= bottom:
                    break
            if font is None and must_keep and pt > int(12 * scale):
                # 仍放不下：无视天花板强制渲染，绝不让主标题消失
                font = _load_role(role, pt, wght)
                lines = wrap_text(draw, text, font, maxw)
        if font is None:
            dropped_flow.append(tag or text[:8])
            return

        for ln in lines:
            tw = draw.textlength(ln, font=font)
            tx = anchor_x - tw / 2 if anchor_align == "center" else anchor_x
            draw.text((tx, y_cur), ln, font=font, fill=color)
            y_cur += int(font.size * (1.18 if font.size > 40 * scale else 1.25))
        if rule and "rule" in st["decor"] and lines:
            yy = y_cur + int(8 * scale)  # 画在标题最后一行的下方，避免压字
            w_rule = max(draw.textlength(l, font=font) for l in lines)
            # 分割线以「标题实际渲染宽度」为基准，居中于该宽度中心 —— 
            # 而非画布中心，视觉轴才成立
            if anchor_align == "center":
                first_w = draw.textlength(lines[0], font=font)
                first_x = anchor_x - first_w / 2
                decor_rule(canvas, first_x, yy, first_x + w_rule, yy,
                           st["accent"], max(2, int(3 * scale)))
            else:
                decor_rule(canvas, anchor_x, yy, anchor_x + w_rule, yy,
                           st["accent"], max(2, int(3 * scale)))
            y_cur += int(22 * scale)
        y_cur += GAP if gap is None else int(gap)

    # 疏密节奏（紧-松-紧）：
    #   标题→分割线→副标题  = 紧（同一信息组，16px）
    #   副标题→英文          = 较松（语言切换需要呼吸，20px）
    #   英文→产品            = 最松（交给流排后的大留白）
    # 宽度统一走 axis_maxw：标题/副标/英文共用一个视觉宽度，轴才贯穿到底
    _flow(args.title, "title_cn", f_title.size, 700, st["ink"], axis_maxw,
          rule=True, gap=int(16 * scale), shrink=False, must_keep=True)
    _flow(args.subtitle, "body_cn", TS_SUB, 400, st["ink_soft"],
          axis_maxw, gap=int(20 * scale), tag="subtitle", min_ratio=0.68)
    _flow(args.en, "latin_serif", TS_EN, 400, st["ink_soft"],
          axis_maxw, tag="en", min_ratio=0.70)

    if args.points:
        pts = [p.strip() for p in args.points.split("|") if p.strip()]
        pz = zones["points"]
        p_align = pz[2]
        block_h = int(len(pts) * f_pt.size * 1.5)
        line_gap = int(f_pt.size * 1.6)
        block_h = int(len(pts) * line_gap)
        widest = max((draw.textlength("· " + p, font=f_pt) for p in pts),
                     default=0)
        # 卖点与视觉轴对齐（左轴构图下与标题同左缘，形成贯穿竖线）
        px = anchor_x if (axis_mode == "left-axis" and p_align == "left") else pz[0]
        if p_align == "center":
            p_lo, p_hi = W / 2 - widest / 2, W / 2 + widest / 2
        else:
            p_lo, p_hi = px, px + widest
        gap_need = int(24 * scale)
        # --- 大留白呼吸（v2.4）---
        # 旧逻辑：卖点紧贴上方文字流（y = max(zone_y, y_cur)），画面被切碎、无呼吸区。
        # 新逻辑：卖点「贴底锚定」——优先贴近画面下缘，与文字流之间留出大片空白。
        bottom_anchor = H - int(56 * scale) - block_h
        cands = [bottom_anchor, max(pz[1], y_cur)]
        if prod_bottom is not None and _h_overlap(p_lo, p_hi):
            cands.append(prod_bottom + gap_need)     # 产品正下方
        cands.append(y_cur + int(24 * scale))         # 文字流正下方（最后兜底）

        def _pts_ok(y_):
            """卖点块放在 y_ 是否安全：不压产品、不压上方文字、不压分层标签、不出血"""
            if y_ + block_h > H - int(24 * scale):
                return False
            if y_ < y_cur - 1:                     # 与上方文字重叠
                return False
            if (prod_bottom is not None and _h_overlap(p_lo, p_hi)
                    and y_ < prod_bottom + gap_need):
                return False                        # 压到产品
            if _hit_callout(p_lo, y_, p_hi, y_ + block_h):
                return False                        # 压到分层标签
            return True

        placed = next((c_ for c_ in cands if _pts_ok(c_)), None)
        # 贴底位被标签占住时，尝试整体上移找空位（分层海报标签常在两侧中段）
        if placed is None:
            for _dy in range(int(30 * scale), int(H * 0.22), int(26 * scale)):
                if _pts_ok(bottom_anchor - _dy):
                    placed = bottom_anchor - _dy
                    break
        if placed is None:
            dropped_flow.append("points")
        else:
            y = placed
            for p in pts:
                if p_align == "center":
                    tw = draw.textlength("· " + p, font=f_pt)
                    draw.text((W / 2 - tw / 2, y), "· " + p, font=f_pt,
                              fill=st["ink"])
                else:
                    draw.text((px, y), "· " + p, font=f_pt, fill=st["ink"])
                y += line_gap

    # 胶囊标签
    if args.badge:
        decor_pill(canvas, args.badge, (int(W * 0.06), int(H * 0.06)),
                   st["accent"], body_path, fill_bg=(args.style in ("S6", "S1")))

    # 印章（强调字体：衬线黑/黑体黑）；frac 与排版引擎的角标估算保持一致
    if args.seal:
        decor_seal(canvas, args.seal, "tr", st.get("accent2", st["accent"]), emph_path,
                   frac=seal_frac)

    # 价格爆炸贴：用展示数字体（得意黑），¥ + 中文 + 数字统一有张力
    # 位置按画幅自适应 + 自动避让分层标签与产品层（悬浮分层海报里标签/层常在两侧）
    if args.price:
        _R = int(min(W, H) * 0.13)          # 爆炸贴外接半径
        # 候选位按「视觉权重」排序：右下 → 左下 → 右上 → 左上 → 右中
        # 分层解构场景：层堆占中间竖带，标签占左侧列，右侧与四角是仅有的空区
        _cands = ([(0.86, 0.88), (0.86, 0.50), (0.88, 0.16), (0.14, 0.90), (0.14, 0.50)]
                  if H >= W else
                  [(0.90, 0.72), (0.90, 0.30), (0.12, 0.72), (0.12, 0.30)])

        def _price_ok(box):
            """价格贴候选位是否安全：不压分层标签、不压产品层、不压文字区"""
            if _hit_callout(*box):
                return False
            for a, b, c, d in _boxes:
                if not (box[2] < a or box[0] > c or box[3] < b or box[1] > d):
                    return False
            # 避让文字流（标题/副标题/英文所占的纵向区间与轴宽）
            if box[1] < y_cur + int(20 * scale):
                return False
            if anchor_align == "center":
                if not (box[2] < anchor_x - axis_maxw / 2
                        or box[0] > anchor_x + axis_maxw / 2):
                    return False
            return True

        bp = None
        for fx, fy in _cands:
            cx0, cy0 = int(W * fx), int(H * fy)
            box = (cx0 - _R, cy0 - _R, cx0 + _R, cy0 + _R)
            if _price_ok(box):
                bp = (cx0, cy0)
                break
        if bp is None:                        # 全被占则用首选位（标签优先）
            bp = (int(W * _cands[0][0]), int(H * _cands[0][1]))
        decor_burst(canvas, args.price, bp, st["accent"], st["surface"], price_path)

    # logo
    if args.logo and os.path.exists(args.logo):
        logo = Image.open(args.logo).convert("RGBA")
        lh = int(H * 0.06)
        logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
        pad = int(W * 0.05)
        pos = {"top-left": (pad, pad), "bottom-left": (pad, H - lh - pad),
               "bottom-center": ((W - logo.width) // 2, H - lh - pad),
               "bottom-right": (W - logo.width - pad, H - lh - pad)}[args.logo_pos]
        canvas.paste(logo, pos, logo)

    # 颗粒质感（最后叠，极淡）
    if "grain" in st["decor"]:
        canvas = add_grain(canvas, 8)

    canvas.convert("RGB").save(args.out, dpi=(args.dpi, args.dpi))
    if args.title:
        tl = wrap_text(draw, args.title, f_title, axis_maxw)
        sys.stderr.write(
            f"[TITLE] 字号={f_title.size} 行数={len(tl)} y={int(title_y)} "
            f"maxw={int(axis_maxw)} 让位={'Y' if dropped else 'N'} "
            f"省略={dropped_flow or '无'} {tl}\n")
    # 信息超载提示：静默丢弃是坏体验，明确告知用户如何取舍
    if dropped_flow:
        _tips = {
            "subtitle": "副标题位置不足 —— 可删减副标题字数，或改用宽栏构图 L1/L2",
            "en": "英文 slogan 位置不足 —— 可省略 --en，或改用宽栏构图",
            "points": "卖点位置不足 —— 可减少卖点条数，或缩小 --product 的 scale",
        }
        for _d in dropped_flow:
            sys.stderr.write(f"[HINT] 已省略「{_d}」：{_tips.get(_d, '空间不足')}\n")
    sys.stderr.write(f"[OK] {args.out} ({W}x{H}) 风格={st['name']} 构图={layout}\n")


if __name__ == "__main__":
    main()
