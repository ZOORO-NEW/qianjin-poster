"""国潮美食插画海报合成器（螺蛳粉等）。

背景板由生图模型产出，本脚本负责「装饰 + 文字」层：
  · 左上角书法艺术大字 + 拼音小字
  · 右上角木质挂牌
  · 底部弧形木框内的卖点标注

设计约束（对齐专业国潮海报）：
  · 文字必须有「底衬」或「描边」，否则压在 busy 的插画背景上读不清
  · 书法大字用 ZCOOLKuaiLe（站酷快乐体，书法感），正文用思源宋体 Heavy
  · 三个卖点等距排布在弧形木框内，弧度随框走

用法：
  python compose_guochao.py --bg base.png --out final.png \
      --title 螺蛳粉 --pinyin LUO SI FEN \
      --s1 骨汤慢熬 鲜爽够味 --s2 配料丰富 分量十足 --s3 地道风味 一口上头
"""

import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 配色 —— 取自「暗夜暖金」国潮体系（参照 v2.x S2 国潮配色但更贴合美食暖调）
INK = "#2B1408"          # 焦糖墨（主文字）
INK_DEEP = "#1A0C04"     # 深墨（描边）
GOLD = "#E8B65A"         # 描金
RED = "#C63B3B"          # 朱红
CREAM = "#FFF4DC"        # 米白（文字底衬）
WOOD_D = "#6B4423"       # 木牌深
WOOD_L = "#A5713C"       # 木牌浅
WOOD_E = "#4A2D14"       # 木牌描边




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

def C(color):
    """把任意颜色写法规范成 RGBA 四元组（Pillow RGBA 模式只接受四元组/整数）。"""
    if isinstance(color, (list, tuple)):
        # 嵌套写法 (("#RRGGBB", alpha), ...) → 解包后递归
        if len(color) == 1:
            return C(color[0])
        if len(color) == 2 and isinstance(color[0], str):
            return C(color[0])[:3] + (int(color[1]),)
        if len(color) == 4 and all(isinstance(x, int) for x in color):
            return tuple(color)
        if len(color) == 3:
            return (color[0], color[1], color[2], 255)
        return color
    if isinstance(color, int):
        return (color, color, color, 255)
    h = color.lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    if len(h) == 8:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
    raise ValueError(f"bad color: {color}")


def _font(af, *names):
    """按名称列表取第一个存在的字体文件"""
    for n in names:
        p = os.path.join(af, n)
        if os.path.exists(p):
            return p
    return None


def _tf(af, names, size):
    p = _font(af, *names)
    return ImageFont.truetype(p, size) if p else ImageFont.load_default()


def draw_glow_text(d, xy, text, font, fill, glow, radius=14, passes=3):
    """带外发光的文字（先画多层模糊光晕，再画实心字）"""
    layer = Image.new("RGBA", d.im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for i in range(passes, 0, -1):
        r = int(radius * i / passes)
        ga = int(90 / i)
        ld.text(xy, text, font=font, fill=C(glow + f"{ga}"),
                stroke_width=r, stroke_fill=glow + f"{ga}")
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    im = d._image
    im.alpha_composite(layer)
    d._image = im
    d.text(xy, text, font=font, fill=C(fill))


def stroke_text(d, xy, text, font, fill, stroke, width=6):
    d.text(xy, text, font=font, fill=C(fill),
           stroke_width=width, stroke_fill=stroke)


def wood_pendant(d, x, y, w, h, af):
    """右上角木质挂牌：木纹 + 描边 + 挂绳 + 挂牌文字"""
    im = d.im
    # 挂绳
    rope = _tf(af, ["NotoSansSC-Regular.otf"], max(8, w // 18))
    d.line([(x + w // 2, 0), (x + w // 2, y + h // 6)],
           fill=C(("#8A6534", 255)), width=max(4, w // 26))
    # 木牌主体
    r = max(6, w // 22)
    d.rounded_rectangle([x, y, x + w, y + h], radius=r,
                        fill=C(WOOD_D + "FF"), outline=WOOD_E + "FF", width=max(3, w // 30))
    # 木纹（横条深浅）
    for i in range(1, 5):
        yy = y + int(h * i / 5)
        d.line([(x + int(w * 0.08), yy), (x + int(w * 0.92), yy)],
               fill=C(("#7A5028", 150)), width=max(2, w // 60))
    # 内描边
    m = max(8, w // 12)
    d.rounded_rectangle([x + m, y + m, x + w - m, y + h - m],
                        radius=max(3, r // 2),
                        outline=GOLD + "FF", width=max(2, w // 50))
    return x + w / 2, y + h / 2


def arc_frame(d, cx, cy, rx, ry, color, width, inner=True):
    """底部弧形木框：用多段椭圆弧拼出（上半缺口式，即「开口向上的弧」）"""
    # 画下半椭圆弧，形成「托住内容」的弧形木框
    steps = 120
    for i in range(steps):
        a0 = math.pi * i / steps
        a1 = math.pi * (i + 1) / steps
        x0, y0 = cx + rx * math.cos(a0), cy + ry * math.sin(a0)
        x1, y1 = cx + rx * math.cos(a1), cy + ry * math.sin(a1)
        d.line([(x0, y0), (x1, y1)], fill=color, width=width)
    # 内圈金色细线沿木框内缘（不穿过文字区）
    if not inner:
        return
    irx, iry = rx - width * 1.5, ry - width * 1.5
    for i in range(steps):
        a0 = math.pi * i / steps
        a1 = math.pi * (i + 1) / steps
        d.line([(cx + irx * math.cos(a0), cy + iry * math.sin(a0)),
                (cx + irx * math.cos(a1), cy + iry * math.sin(a1))],
               fill=C(GOLD + "66"), width=max(2, int(width * 0.28)))


def compose(bg, out, title, pinyin, s1, s2, s3, plaque,
            af, title_size=168, dark=0.30, vignette=True, frame_y=0.125):
    im = Image.open(bg).convert("RGBA")
    W, H = im.size
    sc = H / 1536.0

    # --- 暗角 + 上下压暗，给文字让出可读底 ---
    if dark > 0:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        # 上方压暗（标题区）
        for i in range(int(H * 0.42)):
            k = int(150 * dark * (1 - i / (H * 0.42)) ** 1.4)
            od.line([(0, i), (W, i)], fill=(14, 6, 2, k))
        # 下方压暗（卖点区）
        for i in range(int(H * 0.30)):
            k = int(165 * dark * (i / (H * 0.30)) ** 1.3)
            yy = H - 1 - i
            od.line([(0, yy), (W, yy)], fill=(14, 6, 2, k))
        im.alpha_composite(ov)

    d = ImageDraw.Draw(im, "RGBA")

    # --- 顶部书法大字 + 拼音 ---
    f_t = _tf(af, ["ZCOOLKuaiLe.ttf", "SourceHanSerifSC-Black.ttf"], int(title_size * sc))
    f_p = _tf(af, ["PlayfairDisplay.ttf", "BebasNeue.ttf"], int(34 * sc))
    tx, ty = int(W * 0.075), int(H * 0.055)
    # 朱红印章底衬
    # 印章框高度按「大字实际视觉高度」估算，不要用字号的倍数（会压到拼音）
    seal_w = int(f_t.size * 1.98)
    seal_h = int(f_t.size * 1.08)
    d.rounded_rectangle(
        [tx - int(14 * sc), ty - int(10 * sc),
         tx - int(14 * sc) + seal_w, ty - int(10 * sc) + seal_h],
        radius=int(10 * sc), fill=(RED + "22"), outline=RED + "FF", width=max(2, int(3 * sc)))
    # 大字：外发光 + 深墨描边 + 描金渐层
    draw_glow_text(d, (tx, ty), title, f_t, CREAM, GOLD,
                   radius=int(16 * sc))
    stroke_text(d, (tx, ty), title, f_t, CREAM, INK_DEEP, width=int(7 * sc))
    # 拼音「竖排」置于大字右侧 —— 横排会被大字墨迹压糊，
    # 竖排既避开重叠，也是国潮海报的常见做法（右轴竖题）
    ppx = tx + seal_w + int(46 * sc)   # 拉开间距，避免底衬压住大字末笔
    _cy = ty + int(30 * sc)
    _cy_step = int(f_p.size * 1.18)
    _n_ch = len([1 for c in pinyin if c != " "])
    _bar_h = _n_ch * _cy_step + int(18 * sc)
    # 深色竖条底衬：拼音落在 busy 的筷子上时，靠它保证可读
    d.rounded_rectangle([ppx - int(14 * sc), ty + int(16 * sc),
                         ppx + f_p.size + int(14 * sc), ty + int(16 * sc) + _bar_h],
                        radius=int(8 * sc), fill=C(INK_DEEP + "A6"))
    for _ch in pinyin:
        if _ch == " ":
            continue
        d.text((ppx, _cy), _ch, font=f_p, fill=C(GOLD + "FF"))
        _cy += _cy_step
    # 竖排拼音左侧的朱红细线
    d.line([(ppx - int(13 * sc), ty + int(22 * sc)),
            (ppx - int(13 * sc), _cy)],
           fill=C(RED + "FF"), width=max(2, int(3 * sc)))

    # --- 右上角木质挂牌 ---
    pw, ph = int(300 * sc), int(120 * sc)
    px, py = W - pw - int(70 * sc), int(58 * sc)
    pcx, pcy = wood_pendant(d, px, py, pw, ph, af)
    if plaque:
        f_pl = _tf(af, ["NotoSansSC-Bold.otf", "NotoSansSC (TrueType).otf"],
                   int(46 * sc))
        tw = d.textlength(plaque, font=f_pl)
        stroke_text(d, (pcx - tw / 2, pcy - f_pl.size * 0.58), plaque, f_pl,
                    CREAM, INK_DEEP, width=int(4 * sc))

    # --- 底部弧形木框 + 三卖点 ---
    # 卖点用思源黑体 Bold —— SourceHanSerifSC-Black 缺 ASCII 空格与中点，
    # 渲染成空心方框（实测「骨汤慢熬 鲜爽够味」中间出方块）。
    f_s = _tf(af, ["NotoSansSC-Bold.otf", "NotoSansSC (TrueType).otf"],
              int(46 * sc))
    f_k = _tf(af, ["ZCOOLKuaiLe.ttf", "NotoSansSC-Bold.otf"], int(52 * sc))
    selling = [x for x in (s1, s2, s3) if x]
    cx = W / 2
    cy = H - int(H * frame_y)              # 弧底基准（上移，保证弧线完整入画）
    rx = W * 0.40
    ry = H * 0.055
    fw = max(20, int(17 * sc))
    # 三层描金木框：外描金细线 + 深木主框 + 内描金细线。
    # 单层深木框贴在深色背景上看不见 —— 必须靠描金高光勾出轮廓。
    arc_frame(d, cx, cy, rx + fw * 0.85, ry + fw * 0.85,
              C(GOLD + "FF"), max(4, int(fw * 0.26)), inner=False)
    arc_frame(d, cx, cy, rx, ry, C(WOOD_E + "FF"), fw, inner=False)
    arc_frame(d, cx, cy, rx - fw * 0.95, ry - fw * 0.95,
              C(GOLD + "DD"), max(3, int(fw * 0.20)), inner=False)

    # 卖点：一行横排，置于弧框内侧。
    # 不用「沿弧摆放」—— 弧线两端上翘区会互相挤压导致文字重叠
    # （实测三条卖点在弧上必然叠字）；横排一行更稳，也更符合国潮物料实际版式。
    # 若总宽超画布，等比缩小字号直到放得下。
    _gap = int(40 * sc)
    _pad = int(16 * sc)

    def _layout(scale_):
        fs = _tf(af, ["NotoSansSC-Bold.otf", "NotoSansSC (TrueType).otf"],
                 max(int(20 * sc), int(f_s.size * scale_)))
        widths = [d.textlength(x, font=fs) for x in selling]
        return fs, widths, sum(widths) + _gap * (len(selling) - 1)

    _k = 1.0
    fs, widths, tot = _layout(1.0)
    while tot + _pad * 2 > W * 0.94 and _k > 0.55:
        _k -= 0.06
        fs, widths, tot = _layout(_k)

    x_now = cx - tot / 2
    # 竖直位置：弧框内侧上方
    row_y = cy - int(ry * 0.12) - fs.size
    for i, txt in enumerate(selling):
        tw = widths[i]
        # 底衬用「深墨 + 描金边」而非半透明米白 —— 背景是 busy 配料堆时
        # 半透明底衬不够，米白字会与橙黄配料混在一起
        d.rounded_rectangle([x_now - _pad, row_y - _pad * 0.7,
                             x_now + tw + _pad, row_y + fs.size + _pad * 0.7],
                            radius=int(10 * sc), fill=C(INK_DEEP + "D8"),
                            outline=C(GOLD + "AA"), width=max(2, int(2 * sc)))
        stroke_text(d, (x_now, row_y), txt, fs, CREAM, INK_DEEP, width=int(4 * sc))
        # 卖点之间用金色小菱形分隔（国潮常见装饰）
        if i < len(selling) - 1:
            mx = x_now + tw + _gap / 2
            my = row_y + fs.size * 0.5
            r = int(7 * sc)
            d.polygon([(mx, my - r), (mx + r, my), (mx, my + r), (mx - r, my)],
                      fill=C(GOLD + "FF"))
        x_now += tw + _gap

    # 整体轻微暗角
    if vignette:
        vg = Image.new("L", (W, H), 0)
        vd = ImageDraw.Draw(vg)
        vd.ellipse([-W * 0.28, -H * 0.20, W * 1.28, H * 1.20], fill=255)
        vg = vg.filter(ImageFilter.GaussianBlur(int(W * 0.10)))
        dark_layer = Image.new("RGBA", (W, H), (10, 4, 2, 118))
        inv = vg.point(lambda p: 255 - p)
        dark_layer.putalpha(inv)
        im.alpha_composite(dark_layer)

    im.convert("RGB").save(out, quality=96)
    return out


def main():
    af = _font_dir()
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="螺蛳粉")
    ap.add_argument("--pinyin", default="LUO SI FEN")
    ap.add_argument("--s1", default="骨汤慢熬 鲜爽够味")
    ap.add_argument("--s2", default="配料丰富 分量十足")
    ap.add_argument("--s3", default="地道风味 一口上头")
    ap.add_argument("--plaque", default="古法秘制")
    ap.add_argument("--title-size", type=int, default=168)
    ap.add_argument("--dark", type=float, default=0.30)
    ap.add_argument("--frame-y", type=float, default=0.125,
                    help="弧形木框基准位置（距底边的比例），按底图内容微调")
    a = ap.parse_args()
    p = compose(a.bg, a.out, a.title, a.pinyin, a.s1, a.s2, a.s3, a.plaque,
                af, a.title_size, a.dark, frame_y=a.frame_y)
    print(f"[OK] {p}")


if __name__ == "__main__":
    main()