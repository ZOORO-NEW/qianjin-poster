#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qianjin-poster · fontlib — 角色化字体引擎（①②③④ 共用）

设计原则
--------
1. 字体不进技能包：assets/fonts/ 是「本地缓存」，由 setup_fonts.py 从系统扫描 +
   OFL 直链下载生成 font_index.json。发布 SkillHub / GitHub 时整个 assets/fonts/
   二进制都被排除，包体保持轻量。
2. 角色抽象：compose 不直接指定某个字体文件，而是按「角色(role) + 风格(style)」
   取字。某款字体缺失时自动回退，绝不静默落到不可商用字体。
3. 风格签名字体：每个 S1–S7 风格有偏好的标题字体类别（衬线 / 黑体 / 圆体 /
   展示体），让海报「一看就对味」。

角色(role)定义
--------------
  body_cn          中文正文（黑体 regular/medium）
  title_cn         中文大标题（按风格偏好选类别，默认粗）
  emphasis_cn      强调/印章/标语（衬线黑或黑体黑）
  display_number   价格/数字（得意黑：¥+中文+数字统一有张力；缺失回退黑体粗）
  latin_sans       西文无衬线（Montserrat 可变，按权重实例化）
  latin_serif      西文衬线（Playfair Display 可变，杂志/优雅感）
  handwriting      手写/创意体（站酷小薇，双关/创意标题点缀）

字体清单见 references/font-guide.md（全部 SIL OFL 或厂商免费商用授权）。
"""
import os
import json
import glob

# ---------------------------------------------------------------------------
# 字体目录（setup 据此扫描系统 + 下载；compose 据此取字）
# script: cn/en | category: sans/serif/round/display/handwriting
# weight: 提示字重 | variable: 是否为可变字体（需按轴实例化）
# url=None 表示「系统/已捆绑优先，缺失给手动链接」
# ---------------------------------------------------------------------------
FONT_CATALOG = [
    # 中文核心（系统常见，优先扫描；缺失给手动链接，不强制下载大文件）
    {"family": "NotoSansSC", "script": "cn", "category": "sans", "weight": "auto",
     "variable": False, "url": None,
     "manual": "https://github.com/adobe-fonts/source-han-sans/releases"},
    {"family": "SourceHanSerifSC", "script": "cn", "category": "serif", "weight": "auto",
     "variable": False, "url": None,
     "manual": "https://github.com/adobe-fonts/source-han-serif/releases"},
    {"family": "NotoSerifSC", "script": "cn", "category": "serif", "weight": "auto",
     "variable": False, "url": None,
     "manual": "https://github.com/notofonts/noto-cjk/releases"},
    {"family": "AlibabaPuHuiTi", "script": "cn", "category": "sans", "weight": "auto",
     "variable": False, "url": None,
     "manual": "https://fonts.alibabausercontent.com/"},

    # 中文展示 / 圆体 / 手写（OFL，自动下载）
    {"family": "ZCOOLKuaiLe", "script": "cn", "category": "round", "weight": "regular",
     "variable": False,
     "url": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/zcoolkuaile/ZCOOLKuaiLe-Regular.ttf"},
    {"family": "ZCOOLQingKeHuangYou", "script": "cn", "category": "round", "weight": "regular",
     "variable": False,
     "url": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/zcoolqingkehuangyou/ZCOOLQingKeHuangYou-Regular.ttf"},
    {"family": "ZCOOLXiaoWei", "script": "cn", "category": "handwriting", "weight": "regular",
     "variable": False,
     "url": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/zcoolxiaowei/ZCOOLXiaoWei-Regular.ttf"},
    {"family": "SmileySans", "script": "cn", "category": "display", "weight": "black",
     "variable": False,
     "url": "https://github.com/atelier-anchor/smiley-sans/releases/download/v2.0.1/smiley-sans-v2.0.1.zip",
     "zip_inner": "SmileySans-Oblique.ttf"},

    # 西文（OFL；Montserrat / Playfair 现为可变字体，按权重实例化）
    {"family": "Montserrat", "script": "en", "category": "sans", "weight": "variable",
     "variable": True, "default_wght": 400,
     "url": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"},
    {"family": "PlayfairDisplay", "script": "en", "category": "serif", "weight": "variable",
     "variable": True, "default_wght": 400,
     "url": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"},
    {"family": "BebasNeue", "script": "en", "category": "display", "weight": "regular",
     "variable": False,
     "url": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/bebasneue/BebasNeue-Regular.ttf"},
]

# 每个风格偏好的「标题字体类别」——风格辨识度的核心
STYLE_TITLE_CAT = {
    "S1": "serif",      # 新中式养生 → 衬线（书卷气）
    "S2": "display",    # 国潮 → 展示体（力量）
    "S3": "sans",       # 极简科技 → 黑体粗
    "S4": "round",      # 暖心家居 → 圆体（亲和）
    "S5": "round",      # 美食诱惑 → 圆体（诱人）
    "S6": "display",    # 促销炸裂 → 展示体（冲击）
    "S7": "serif",      # 杂志封面 → 衬线（高级）
}

WEIGHT_KEYS = {
    "thin":    ["thin", "hairline", "100", "extralight", "200"],
    "light":   ["light", "300"],
    "regular": ["regular", "normal", "book", "roman", "400"],
    "medium":  ["medium", "med", "500"],
    "bold":    ["bold", "600", "700", "semibold"],
    "black":   ["black", "heavy", "800", "900", "extrabold"],
}
WEIGHT_RANK = {"thin": 0, "light": 1, "regular": 2, "medium": 3, "bold": 4, "black": 5}


def guess_family(base):
    low = base.lower()
    for c in FONT_CATALOG:
        if c["family"].lower() in low:
            return c["family"]
    for key in ("noto sans sc", "notosanssc", "source han sans", "sourcehansans",
                "noto serif sc", "notoserifsc", "source han serif", "sourcehanserif",
                "alibabapuhuiti", "zcool", "smiley", "bebas", "montserrat",
                "playfair", "lxgw", "huxiaobo", "puhui", "simhei", "simsun", "kaiti"):
        if key.replace(" ", "") in low.replace(" ", ""):
            return key
    return None


def classify(base):
    """启发式分类（仅用于目录里不在 FONT_CATALOG 的字体）。"""
    low = base.lower()
    script = "cn" if any(k in low for k in (
        "noto", "sourcehan", "source han", "zcool", "smiley", "alibaba",
        "simhei", "simsun", "song", "kaiti", "lxgw", "huxiaobo", "puhui")) else "en"
    category = "sans"
    if any(k in low for k in ("serif", "song", "kaiti")):
        category = "serif"
    elif any(k in low for k in ("kuai", "huangyou", "happy", "黄油", "round")):
        category = "round"
    elif any(k in low for k in ("xiaowei", "huxiaobo", "logo", "hand")):
        category = "handwriting"
    elif any(k in low for k in ("smiley", "bebas", "kuhei", "display", "black", "heavy")):
        category = "display"
    weight = "regular"
    for w, keys in WEIGHT_KEYS.items():
        if any(k in low for k in keys):
            weight = w
            break
    variable = ("[" in base) or ("vf" in low) or ("variable" in low)
    return {"script": script, "category": category, "weight": weight, "variable": variable}


def build_index(fonts_dir, catalog=FONT_CATALOG):
    """扫描 fonts_dir，返回字体条目列表（含相对路径与元数据）。"""
    entries = []
    seen = set()
    files = sorted(glob.glob(os.path.join(fonts_dir, "*")))
    for f in files:
        base = os.path.basename(f)
        low = base.lower()
        if not low.endswith((".ttf", ".otf", ".ttc")):
            continue
        meta = None
        for c in catalog:
            if c["family"].lower() in low.replace(" ", ""):
                meta = c
                break
        if meta:
            e = {"family": meta["family"], "file": base,
                 "script": meta["script"], "category": meta["category"],
                 "weight": meta["weight"], "variable": meta["variable"]}
            if meta.get("default_wght"):
                e["default_wght"] = meta["default_wght"]
        else:
            cl = classify(base)
            fam = guess_family(base) or "Custom"
            e = {"family": fam, "file": base, **cl}
        key = (e["family"], e["category"], e["weight"], e["variable"], base)
        if key in seen:
            continue
        seen.add(key)
        entries.append(e)
    return entries


def save_index(fonts_dir, entries, path=None):
    path = path or os.path.join(fonts_dir, "font_index.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "fonts": entries}, fh, ensure_ascii=False, indent=2)
    return path


def load_index(fonts_dir):
    p = os.path.join(fonts_dir, "font_index.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("fonts", [])
    except Exception:
        return None


def _candidates(entries, script=None, category=None):
    out = []
    for e in entries:
        if script and e.get("script") != script:
            continue
        if category and e.get("category") != category:
            continue
        out.append(e)
    return out


def _best(entries, weight_order):
    """在候选里按权重偏好取一个；无则按权重 rank 取最接近。"""
    if not entries:
        return None
    for w in weight_order:
        for e in entries:
            if e.get("weight") == w:
                return e
    # 退而取权重 rank 最高（最粗）的
    return max(entries, key=lambda e: WEIGHT_RANK.get(e.get("weight"), 2))


def select_role(entries, role, style="S1"):
    """按角色 + 风格返回最佳字体条目（找不到返回 None，由调用方回退）。"""
    cn = _candidates(entries, script="cn")
    en = _candidates(entries, script="en")

    if role == "body_cn":
        return _best(_candidates(cn, category="sans"),
                     ["regular", "light", "medium", "bold"])

    if role == "title_cn":
        cat = STYLE_TITLE_CAT.get(style, "sans")
        # 优先该风格的偏好类别（取最粗），否则黑体粗，否则任意中文
        pref = _candidates(cn, category=cat)
        if pref:
            return _best(pref, ["black", "bold", "heavy", "regular"])
        return _best(_candidates(cn, category="sans"),
                     ["bold", "black", "medium", "regular"]) or (cn[0] if cn else None)

    if role == "emphasis_cn":
        serif = _candidates(cn, category="serif")
        if serif:
            return _best(serif, ["black", "heavy", "bold", "regular"])
        return _best(_candidates(cn, category="sans"),
                     ["black", "heavy", "bold"]) or (cn[0] if cn else None)

    if role == "display_number":
        # 价格/数字：得意黑（含 ¥ 与数字统一张力）；缺失回退黑体粗
        disp = _candidates(cn, category="display")
        if disp:
            return disp[0]
        return _best(_candidates(cn, category="sans"),
                     ["black", "bold", "heavy"]) or (cn[0] if cn else None)

    if role == "latin_sans":
        return _best(_candidates(en, category="sans"),
                     ["regular", "medium", "bold"]) or (en[0] if en else None)

    if role == "latin_serif":
        return _best(_candidates(en, category="serif"),
                     ["regular", "bold", "medium"]) or (en[0] if en else None)

    if role == "handwriting":
        hw = _candidates(cn, category="handwriting")
        if hw:
            return hw[0]
        return select_role(entries, "emphasis_cn", style)

    return None


def resolve(entries, style):
    """一次性解析某风格下的全部角色字体条目。"""
    return {
        "body_cn": select_role(entries, "body_cn", style),
        "title_cn": select_role(entries, "title_cn", style),
        "emphasis_cn": select_role(entries, "emphasis_cn", style),
        "display_number": select_role(entries, "display_number", style),
        "latin_sans": select_role(entries, "latin_sans", style),
        "latin_serif": select_role(entries, "latin_serif", style),
        "handwriting": select_role(entries, "handwriting", style),
    }


def load_font(entries, fonts_dir, entry, size, weight=None):
    """按条目加载字体，可变字体按 weight 实例化。失败回退默认。"""
    from PIL import ImageFont
    if not entry:
        return None
    path = os.path.join(fonts_dir, entry["file"])
    if not os.path.exists(path):
        return None
    try:
        font = ImageFont.truetype(path, size)
        if entry.get("variable") and weight:
            try:
                font.set_variation_by_axes([weight])
            except Exception:
                try:
                    font.set_variation_by_name("Bold" if weight >= 600 else "Regular")
                except Exception:
                    pass
        return font
    except Exception:
        try:
            return ImageFont.truetype(path, int(size * 0.92))
        except Exception:
            return ImageFont.load_default()


def describe(resolved, fonts_dir):
    """日志用：把已解析的角色字体打印成可读行。"""
    lines = []
    for role, e in resolved.items():
        if not e:
            lines.append(f"  {role}: (缺失·回退)")
            continue
        path = os.path.join(fonts_dir, e["file"])
        tag = "fonts/" + e["file"] if ("assets" in path.replace("\\", "/").split("/")) else e["file"]
        lines.append(f"  {role}: {e['family']} [{e['category']}/{e.get('weight')}]")
    return lines
