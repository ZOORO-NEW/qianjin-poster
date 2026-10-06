# 免费商用字体 · font-guide（角色化取字）

> 本文件是 qianjin-poster 的字体授权基准 + 取字机制说明。
> **所有海报文字必须来自本清单或由 `scripts/setup_fonts.py` 自动获取的字体。**
> 禁止任何未确认授权的商业字体。

---

## 一、红线

- ❌ 严禁：方正系列、汉仪系列、造字工房、华康、文鼎、蒙纳(Monotype) 等需授权字库。
- ❌ 严禁把「系统默认字体」直接商用：Windows 自带「微软雅黑」「宋体」「黑体」**不可**商用。
  （`setup_fonts.py` 只把它们当运行时兜底，绝不主动复制进缓存。）
- ✅ 只允许：SIL OFL 协议字体、厂商明确「免费商用」的字体、公共领域字体。

---

## 二、取字机制：角色 + 风格（fontlib）

`compose_poster.py` 不直接指定某个字体文件，而是按**角色(role)** + **风格(style)** 自动取字。
好处：字体缺失自动回退、每种风格有专属标题字体、换字体不改代码。

| 角色 | 用途 | 默认来源 | 缺失回退 |
|------|------|----------|----------|
| `body_cn` | 正文/副标题/卖点 | 思源黑体 Regular | 任意中文黑体 |
| `title_cn` | 大标题（**按风格切换**） | 见下方风格映射 | 黑体粗 |
| `emphasis_cn` | 印章/强调/最强锚点 | 思源宋 Black | 黑体黑 |
| `display_number` | 价格/数字爆炸贴 | 得意黑 Smiley Sans | 黑体粗 |
| `latin_serif` | 英文 slogan（`--en`） | Playfair Display | 回退西文黑体 |
| `latin_sans` | 英文标签 | Montserrat | 回退西文黑体 |
| `handwriting` | 手写/创意点缀 | 站酷小薇 | 回退强调体 |

### 风格 → 标题字体映射（风格辨识度核心）

| 风格 | 标题字体类别 | 实际字体 | 气质 |
|------|--------------|----------|------|
| S1 新中式养生 | 衬线 serif | 思源宋 | 书卷、雅致 |
| S2 国潮 | 展示 display | 得意黑 | 厚实、有力 |
| S3 极简科技 | 黑体 sans | 思源黑粗 | 简洁、克制 |
| S4 暖心家居 | 圆体 round | 站酷快乐体 | 亲和、柔软 |
| S5 美食诱惑 | 圆体 round | 站酷快乐体 | 活泼、诱人 |
| S6 促销炸裂 | 展示 display | 得意黑 | 冲击、抢眼 |
| S7 杂志封面 | 衬线 serif | 思源宋 | 高级、克制 |

> 可变字体（思源宋 / Montserrat / Playfair）按角色自动实例化字重：标题→粗，正文→常规。

---

## 三、推荐字体清单（均可商用）

### 中文 · 正文 / 通用

| 字体 | 授权 | 风格 | 适用 |
|------|------|------|------|
| 思源黑体 (Source Han Sans / Noto Sans SC) | SIL OFL | 严谨、专业 | 正文、标题 |
| 阿里巴巴普惠体 (Alibaba PuHuiTi) | 阿里免费授权 | 现代、中性 | 正文、全场景 |
| 思源宋体 (Source Han Serif / Noto Serif SC) | SIL OFL | 传统、人文 | 国风、高端标题 |

### 中文 · 展示 / 圆体 / 手写（OFL，自动下载）

| 字体 | 授权 | 风格 | 适用 |
|------|------|------|------|
| 得意黑 (Smiley Sans) | SIL OFL | 窄体、展示、力量 | 大促标题、价格数字 |
| 站酷快乐体 (ZCOOL KuaiLe) | 站酷免费授权 | 活泼可爱 | 节日/亲子/美食标题 |
| 站酷庆科黄油体 (ZCOOL QingKe HuangYou) | 站酷免费授权 | 圆润 Q | 暖心/轻食标题 |
| 站酷小薇 LOGO 体 (ZCOOL XiaoWei) | 站酷免费授权 | 手写、温暖 | logo 感标题、创意点缀 |

### 西文 / 数字（OFL，自动下载）

| 字体 | 授权 | 风格 | 适用 |
|------|------|------|------|
| Playfair Display | SIL OFL | 衬线、高雅 | 英文 slogan、杂志标题 |
| Montserrat | SIL OFL | 几何、现代 | 英文标签、价格 |
| Bebas Neue | SIL OFL | 窄体、大写 | 英文大数字、slogan |

---

## 四、获取方式

### 方式一：自动脚本（推荐，首次使用必跑）

```bash
python scripts/setup_fonts.py              # 扫描 + 下载 + 建索引
python scripts/setup_fonts.py --check      # 仅报告缺失，不下载
python scripts/setup_fonts.py --no-download# 只扫本地，不联网
```

脚本会：
1. **扫描系统**已装的免费商用中文字体（思源黑/宋、阿里普惠等），跳过 VF 可变字体与风险字体；
2. 从 **OFL 官方直链（jsDelivr）** 下载推荐增强字体：站酷三款、得意黑（GitHub Release zip 解包）、
   Montserrat、Playfair Display、Bebas Neue；
3. 写入 `assets/fonts/font_index.json`（字体元数据索引），供 `compose_poster.py` 按角色取字。

> **字体是本地缓存**：`.gitignore` 已排除 `assets/fonts/`，发布 SkillHub / GitHub 时字体不进包，
> 包体保持轻量；用户首次使用跑一次 setup 即可自动补全。

### 方式二：手动补充

把 `.ttf/.otf` 放进 `assets/fonts/`，**重命名带家族名**（如 `MyTitle-Bold.ttf`），
再跑一次 `setup_fonts.py` 重建索引。不在目录里的字体会被 `classify()` 启发式分类。

### 授权与获取链接（手动下载用）

- 得意黑：https://github.com/atelier-anchor/smiley-sans
- 站酷系列：https://www.zcool.com.cn/special/fonts/
- 思源黑/宋：https://github.com/adobe-fonts/source-han-sans/releases
- 阿里巴巴普惠体：https://github.com/AlibabaPuHuiTi/AlibabaPuHuiTi

---

## 五、如何继续丰富字体

1. 在 `fontlib.py` 的 `FONT_CATALOG` 增加条目（family / script / category / weight / url / manual）。
2. 跑 `setup_fonts.py` 下载并重建索引。
3. 需要让某款字体成为某风格标题：在 `fontlib.STYLE_TITLE_CAT` 调整该风格的 `category`
   （`serif` / `sans` / `round` / `display`），并在 `select_role()` 补该类别的匹配。

---

## 六、授权声明模板（交付时附上）

> 本海报使用字体：**思源黑体 / 思源宋体**（SIL Open Font License）、**得意黑 Smiley Sans**
> （SIL OFL）、**Playfair Display**（SIL OFL）等，均为免费商用授权，无版权风险。

如使用其他清单字体，按实际替换名称与授权说明即可。
