#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qianjin-poster · 字体获取与索引构建（1 字体不进技能包）

职责
----
1. 扫描系统已装免费商用中文字体（思源/阿里普惠等）与 assets/fonts 已有文件。
2. 从 OFL 官方直链下载本技能推荐的增强字体（站酷系列 / 得意黑 / Montserrat /
   Playfair / Bebas Neue），含 GitHub Release 的 zip 解包。
3. 写入 assets/fonts/font_index.json，供 compose_poster.py 按「角色+风格」取字。

重要：assets/fonts/ 下的 .ttf/.otf 与 font_index.json 均为「本地缓存」，
      发布 SkillHub / GitHub 时被 .gitignore 排除，技能包保持轻量。
      用户首次使用前跑一次本脚本即可自动补全字体。

用法
----
  python scripts/setup_fonts.py                # 扫描 + 下载 + 建索引
  python scripts/setup_fonts.py --check        # 仅报告缺失，不下载
  python scripts/setup_fonts.py --no-download  # 只扫描本地，不联网
"""
import os
import sys
import shutil
import zipfile
import io
import urllib.request
import argparse
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "assets", "fonts")
os.makedirs(FONT_DIR, exist_ok=True)

sys.path.insert(0, HERE)
import fontlib  # noqa: E402

SYS_DIRS = [
    "C:/Windows/Fonts",
    "/System/Library/Fonts", "/Library/Fonts",
    "/usr/share/fonts", "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts"),
]


def download(url, dest, timeout=60):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "qianjin-poster"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if len(data) < 2000:
            sys.stderr.write("  [跳过] 文件过小(%dB)\n" % len(data))
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        sys.stderr.write("  [失败] %s: %s\n" % (os.path.basename(dest), e))
        return False


def download_zip_inner(url, inner_name, dest_dir, timeout=90):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "qianjin-poster"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        # 只认 ttf/otf，排除 woff/woff2
        preferred = [n for n in names if n.lower().endswith((".ttf", ".otf"))]
        hit = next((n for n in preferred if n.endswith(inner_name)), None)
        if not hit:
            stem = inner_name[:-4] if inner_name.lower().endswith(".ttf") else inner_name
            hit = next((n for n in preferred if stem in n), None)
        if not hit:
            sys.stderr.write("  [跳过] zip 内未找到 %s\n" % inner_name)
            return None
        out_name = os.path.basename(hit)
        with open(os.path.join(dest_dir, out_name), "wb") as f:
            f.write(z.read(hit))
        return out_name
    except Exception as e:
        sys.stderr.write("  [失败] zip 解包 %s: %s\n" % (inner_name, e))
        return None


def scan_system():
    copied = []
    seen = set()
    # 已存在于 assets/fonts 的家族不再从系统复制，避免重复/混乱命名
    existing_fams = set()
    for f in os.listdir(FONT_DIR):
        fam = fontlib.guess_family(f)
        if fam:
            existing_fams.add(fam.lower())
    for d in SYS_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                low = f.lower()
                if not low.endswith((".ttf", ".otf", ".ttc")):
                    continue
                if "vf" in low or "variable" in low:
                    continue  # 跳过可变字体，静态实例优先
                fam = fontlib.guess_family(f)
                if not fam or fam in ("simhei", "simsun"):
                    continue
                if fam.lower() in existing_fams:
                    continue
                dest = os.path.join(FONT_DIR, f)
                if os.path.exists(dest) or f in seen:
                    continue
                seen.add(f)
                try:
                    shutil.copy2(os.path.join(root, f), dest)
                    existing_fams.add(fam.lower())
                    copied.append(f)
                except Exception:
                    pass
    return copied


def main():
    ap = argparse.ArgumentParser(description="qianjin-poster 字体获取")
    ap.add_argument("--check", action="store_true", help="仅报告，不下载")
    ap.add_argument("--no-download", action="store_true", help="不联网，仅本地扫描")
    args = ap.parse_args()

    print("== qianjin-poster 字体获取 ==")
    print("字体缓存目录：%s\n" % FONT_DIR)

    print("[1/3] 扫描系统免费商用字体…")
    copied = scan_system()
    if copied:
        print("  本地已整理 %d 个字体文件。" % len(copied))
    else:
        print("  未发现新的系统字体（assets/fonts 已有或系统无免费中文字体）。")

    print("\n[2/3] 检查并获取推荐增强字体…")
    have_files = [os.path.basename(p) for p in glob.glob(os.path.join(FONT_DIR, "*"))]
    have_families = set()
    for f in have_files:
        fam = fontlib.guess_family(f)
        if fam:
            have_families.add(fam.lower())

    missing = []
    for c in fontlib.FONT_CATALOG:
        fam = c["family"]
        if fam.lower() in have_families:
            print("  [已有] %s" % fam)
            continue
        if args.no_download or args.check:
            if args.check:
                print("  [缺失] %s -> %s" % (fam, c.get("manual", c.get("url"))))
            missing.append(c)
            continue
        if not c.get("url"):
            print("  [缺失·手动] %s -> %s" % (fam, c.get("manual", "见 font-guide.md")))
            missing.append(c)
            continue
        print("  [获取] %s ..." % fam)
        if c.get("zip_inner"):
            out = download_zip_inner(c["url"], c["zip_inner"], FONT_DIR)
            if out:
                print("      OK %s" % out)
            else:
                missing.append(c)
        else:
            dest = os.path.join(FONT_DIR, fam + ".ttf")
            ok = download(c["url"], dest)
            print("      %s %s" % ("OK" if ok else "FAIL", os.path.basename(dest)))
            if not ok:
                missing.append(c)

    print("\n[3/3] 构建 font_index.json …")
    entries = fontlib.build_index(FONT_DIR)
    fontlib.save_index(FONT_DIR, entries)
    print("  索引共 %d 个字体文件。" % len(entries))

    resolved_all = {}
    for st in fontlib.STYLE_TITLE_CAT:
        r = fontlib.resolve(entries, st)
        for role, e in r.items():
            resolved_all.setdefault(role, set()).add(e["family"] if e else None)
    print("\n== 角色覆盖 ==")
    for role in ["body_cn", "title_cn", "emphasis_cn", "display_number",
                 "latin_sans", "latin_serif", "handwriting"]:
        fams = sorted(x for x in resolved_all.get(role, set()) if x)
        print("  %-14s: %s" % (role, ", ".join(fams) if fams else "（缺失·回退中）"))

    if missing:
        print("\n[提示] 以下字体未自动获取（不影响运行，将回退到已有字体）：")
        for c in missing:
            tgt = c.get("manual") or c.get("url")
            print("  - %s: %s" % (c["family"], tgt))

    print("\n完成。运行 compose_poster.py 即可按风格取字。")
    print("（发布前请确认 assets/fonts/ 已被 .gitignore 排除，字体不进包。）")


if __name__ == "__main__":
    main()
