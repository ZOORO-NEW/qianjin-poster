#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qianjin-poster · 海报提示词生成器 v2（概念驱动）
根据用户 Concept / Style 生成适配元宝/即梦/豆包的中文生图提示词。

用法：
  python gen_prompt.py --style S1 --concept "足底暖流看得见" \
      --subject "白色经络理疗足部按摩仪悬浮于画面中央" \
      --title "暖流从脚底升起" --subtitle "寒从足底起 温热护足" \
      --platform jimeng

  # 也可不用风格，纯手动拼装
  python gen_prompt.py --ratio "竖版3:4" --style "未来科技" \
      --subject "..." --scene "..." --light "..." --color "..." \
      --title "..." --subtitle "..." --quality "..." --platform all
"""
import argparse

# 风格视觉语言（与 references/styles.md 同步，供提示词注入专业设计语境）
STYLE_VISUAL = {
    "S1": {"name": "新中式养生",
           "visual": "暖米色宣纸质感背景，朱红印章点缀，足底经络发光线条，水墨笔触晕染，东方留白意境",
           "palette": "暖米#F4EBE0 + 浅褐#E3C9A8 + 朱红#C0392B",
           "decor": "朱红印章、经络发光线、足底穴位线稿、水墨笔触"},
    "S2": {"name": "国潮",
           "visual": "深紫黑底，描金祥云回纹，霓虹国潮红，传统符号现代化重构",
           "palette": "深紫黑#1A1423 + 描金米#F5E6C8 + 国潮红#E63946",
           "decor": "祥云回纹、描金描边、霓虹外发光"},
    "S3": {"name": "极简科技",
           "visual": "深空蓝极简背景，冷光晕，细网格线，精密工业感，产品即主角",
           "palette": "深空蓝#0B1E3F + 冷白#F5F7FA + 霓虹蓝#3A6FF7",
           "decor": "细网格、几何圆、冷光晕、技术参数小字"},
    "S4": {"name": "暖心家居",
           "visual": "奶油色温暖背景，柔和暖光晕，圆角色块，松弛居家氛围",
           "palette": "奶油#FDF6EC + 浅橙#F6E2C8 + 暖橙#E08E45",
           "decor": "暖光晕、圆角色块、生活化线条插画"},
    "S5": {"name": "美食诱惑",
           "visual": "深巧色满版背景，水珠蒸汽，材质高光特写，食欲感强",
           "palette": "深巧#2B1A12 + 暖白#FFF3E6 + 橙红#FF7A3D",
           "decor": "水珠、蒸汽线、材质高光"},
    "S6": {"name": "促销炸裂",
           "visual": "高饱和促销红满版，金黄价格爆炸贴，动感色带，信息密集分区清晰",
           "palette": "促销红#FF4D2E + 白#FFFFFF + 金黄#FFD400",
           "decor": "价格爆炸贴、胶囊标签、斜向箭头色带"},
    "S7": {"name": "杂志封面",
           "visual": "米白纸张质感，巨型字体带拖影，刊号条码辅助小字，瑞士极简排版",
           "palette": "米白#F2EFE9 + 墨黑#1A1A1A + 钴蓝#2B50E0",
           "decor": "刊号、条码、四角星芒、纸张颗粒、字体拖影"},
}

PLATFORM_NOTE = {
    "jimeng": "即梦：原生支持中文提示词；电商促销/中文文案准确；比例优先竖版9:16；文案保持简短避免乱码。",
    "doubao": "豆包：中文理解好；适合写实摄影与氛围感；可给参考图反推；长文案建议生图后用设计软件二次合成。",
    "yuanbao": "元宝：中文原生；擅长国潮/新中式语义；可多轮微调风格；文案主标≤10字。",
    "all": "三平台均原生中文。跨平台铁律：文案主标≤10字，长句必乱码；精确品牌字建议生图后PIL二次合成。",
}


def main():
    ap = argparse.ArgumentParser(description="qianjin-poster 提示词生成器")
    ap.add_argument("--concept", default="", help="设计概念（一句话：这张海报想让人记住什么）")
    ap.add_argument("--style", default=None, help="风格代码 S1-S7，自动注入视觉语言与配色")
    ap.add_argument("--style-name", default="", help="手动风格名（不用 --style 时）")
    ap.add_argument("--ratio", default="竖版3:4满版")
    ap.add_argument("--subject", default="", help="产品主体描述")
    ap.add_argument("--scene", default="", help="场景/背景")
    ap.add_argument("--light", default="柔和自然光，产品表面有真实高光与投影")
    ap.add_argument("--color", default="", help="配色（用 --style 时自动注入）")
    ap.add_argument("--title", default="", help="主标题≤10字")
    ap.add_argument("--subtitle", default="", help="副标题/英文SLOGAN")
    ap.add_argument("--quality", default="商业产品摄影质感，8K，细节清晰，高端电商海报")
    ap.add_argument("--platform", default="all", choices=["jimeng", "doubao", "yuanbao", "all"])
    args = ap.parse_args()

    sv = STYLE_VISUAL.get(args.style) if args.style else None
    style_label = sv["name"] if sv else (args.style_name or "自定义")
    palette = args.color or (sv["palette"] if sv else "")
    visual = sv["visual"] if sv else ""

    parts = [f"{args.ratio}构图；{style_label}风格产品海报"]
    if args.concept:
        parts.append(f"设计概念：{args.concept}")
    if args.subject:
        parts.append(args.subject)
    if args.scene:
        parts.append(args.scene)
    elif visual:
        parts.append(visual)
    parts.append(f"光影：{args.light}")
    if palette:
        parts.append(f"配色：{palette}")
    if sv:
        parts.append(f"装饰元素：{sv['decor']}")
    if args.title:
        cap = f"标题“{args.title}”"
        if args.subtitle:
            cap += f"，小字“{args.subtitle}”"
        parts.append(cap)
    parts.append(args.quality)

    prompt = "；".join(p for p in parts if p)
    negative = ("文字乱码、变形、低分辨率、模糊、水印、廉价拼贴感、"
                "卡通CG、重复元素、不需要的Logo、杂乱背景、无意义光斑")

    print("=" * 60)
    print("【海报提示词】")
    print("-" * 60)
    print(prompt)
    print("-" * 60)
    print("【负面词 negative】")
    print(negative)
    print("-" * 60)
    print("【平台备注】")
    print(PLATFORM_NOTE.get(args.platform, PLATFORM_NOTE["all"]))
    print("=" * 60)


if __name__ == "__main__":
    main()
