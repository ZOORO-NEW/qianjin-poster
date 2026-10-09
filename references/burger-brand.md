# 品牌广告版商业美食海报

> `scripts/compose_burger_v2.py` —— 对标国际快餐连锁品牌广告（参考 ZHAPU CREATIVE 系列）。
> 相比 `compose_burger.py`（极简版）的升级：**笔刷标题 + 暖氛围底图 + 信息矩阵 + 叠压层次**。

| 脚本 | 风格 | 信息量 | 适用 |
|---|---|---|---|
| `compose_burger.py` | 极简高级 | 3 层文字 | 极简高端餐厅、菜单 |
| **`compose_burger_v2.py`** | **品牌广告** | **7 处信息** | **连锁快餐品牌、加盟物料** |

---

## 一、参考图拆解：对标海报的 5 个特征

以高端快餐连锁品牌海报为对标，拆出可复刻的 5 点：

| # | 特征 | 实现手段 |
|---|---|---|
| 1 | **手写毛笔标题**，带飞白与墨迹飞溅 | **生图生成 PNG**（字体库无英文手写体） |
| 2 | **暖棕氛围**：焦散光斑 + 蒸汽 + 芝麻飞溅 | 底图提示词写「暖棕橙色调，不是灰黑」 |
| 3 | **信息矩阵**：左右侧栏 + 圆形徽章 + 底部双栏 | 脚本 `--left-head`/`--right-*`/`--badge-*`/`--left-foot` |
| 4 | **标题与主体穿插叠压**，不是各占一块 | 标题贴图压在汉堡上部 + **强投影** |
| 5 | **金色轮廓光**勾食材边缘 | 底图提示词写「暖光侧逆光 + 金色轮廓光」 |

---

## 二、标准流程（三段式）

```bash
# ① 生图：暖氛围底图（含焦散光斑/蒸汽/飞溅）
#    提示词见第三节 → erase 去水印 → base_warm.png

# ② 生图：笔刷标题 PNG
#    提示词见第四节 → erase 去水印 → matting 抠透明 → 阈值裁飞溅 → title_trim.png

# ③ 合成：文字矩阵 + 比例适配 + 导出
python scripts/compose_burger_v2.py \
  --bg base_warm.png --out final.png --title-img title_trim.png \
  --brand "ZHAPU CREATIVE" --tagline "TASTE A BRIGHTER TOMORROW" \
  --left-head "JUICY\nBOLD\nSATISFYING" \
  --left-sub "MORE THAN A BURGER\nA BETTER DAY" \
  --right-head "Real Ingredients\nReal Happiness" \
  --right-sub "SIMPLE INGREDIENTS\nEXTRAORDINARY FLAVOR" \
  --badge-top "PREMIUM BEEF" --badge-sub "ALWAYS GOOD TASTE" \
  --left-foot "GREAT FOOD\nBRINGS PEOPLE\nCLOSER" \
  --ratio 0.75 --save-size 1086x1448
```

---

## 三、暖氛围底图提示词（关键）

```
【氛围】背景是暖棕橙色调（不是灰黑），有明显的暖色焦散光斑散景，
        空气中弥漫食物蒸汽升腾，面包与食材表面有细小的芝麻与面包屑飞溅，
        带有暖色轮廓光。整体是「刚出锅、热气腾腾」的温暖食物质感。
【光影】暖光侧逆光，食材边缘有金色轮廓光，油脂与酱汁高光明亮。
```

**为什么要强调「不是灰黑」**：混元/即梦默认会给「高级质感」配深灰影棚背景，
但**冷灰底会让食物显得像产品图而非食品广告**。食欲感来自暖色氛围。

---

## 四、笔刷标题生图法（绕过字体库限制）

字体库三款 ZCOOL 都是楷体/宋体风，**没有英文手写笔刷体**。解法是生图：

```
手写毛笔笔刷字体设计：「BEEF BURGER」两个单词，狂野张扬的手绘毛笔字，
带飞白与墨迹飞溅质感，粗细笔画变化强烈，倾斜排列有冲劲，
字体为米白色带金色描边，高端快餐品牌广告风格，纯黑背景，
字形清晰可辨，除这几个字母外没有任何其他文字，无水印
```

**后处理三步**（缺一步都会出问题）：

```python
# 1. erase 去右下角水印
# 2. matting 抠透明（黑底 → 透明 PNG）
# 3. ⚠️ 阈值裁飞溅边缘 —— 否则墨迹飞溅会撑大包围盒，导致标题压住主体
import numpy as np
a = np.array(Image.open("title.png").convert("RGBA").getchannel("A"))
ys, xs = np.where(a > 90)                      # 阈值滤掉淡墨飞溅
h, w = ys.max()-ys.min(), xs.max()-xs.min()
bbox = (int(xs.min()+w*0.03), int(ys.min()+h*0.06),
        int(xs.max()-w*0.03), int(ys.max()-h*0.04))
Image.open("title.png").crop(bbox).save("title_trim.png")
```

---

## 五、标题与主体的「叠压层次」（高级感的关键）

参考图的标题**不是独立占顶部**，而是**与主体穿插叠压** —— 这是它比普通海报高级的原因。

**做法**：
1. 标题贴图压在汉堡上部（`y_frac=0.020`，`scale_w=0.60`）
2. **克制的投影**：`blur=4 / alpha=90(35%) / dy=3px`（默认值）
3. 底图主体起始位置用**亮度阈值自动检测**（见下），确认标题不会盖住核心信息

**⚠️ 投影必须克制（实测踩坑）**
初版用「强投影」`blur=14 / alpha=D8(85%) / dy=6px`，结果**把下层面包糊成黑块、主体完全看不见** ——
投影本该只负责「分出层次」，一旦过重就变成「遮盖主体」，叠压的意义完全反了。

| 参数档 | blur | alpha | dy | 效果 |
|---|---|---|---|---|
| ❌ 过重 | 14 | 216 | 6 | 下层面包被糊成黑块 |
| ❌ 偏重 | 7 | 130 | 6 | 面包边缘发暗，仍可辨认 |
| ✅ **推荐** | **4** | **90** | **3** | **层次感在，面包完整可见** |
| ○ 无投影 | 0 | 0 | 0 | 标题与主体粘连，层次消失 |

命令行可调：`--title-shadow-blur` / `--title-shadow-alpha` / `--title-shadow-dy`。

**主体位置检测**（判断标题安全高度）：
```python
rows = [a[y:y+8].mean() for y in range(0, H, 8)]
thr = (max(rows) + sum(rows)/len(rows)) / 2
first = next(y for y, m in zip(range(0, H, 8), rows) if m > thr)
print(f"主体起始 {first/H*100:.1f}%H")     # 实测：冷底 22%，暖底 16.7%
```

---

## 六、比例适配方向（踩过的坑）

底图 2:3（0.667）→ 目标 3:4（0.75）：

| 做法 | 结果 |
|---|---|
| 直接 resize | ❌ 变形 |
| 居中裁切 | ❌ 切掉分层结构 |
| 左右对称扩宽 | ⚠️ 会等量挤压上下，把主体顶进标题区 |
| **左右扩宽（只加宽不加高）** | ✅ 上下留白保留，主体留在原位 |

```python
if cur < target_ratio:          # 目标更宽 → 左右扩宽
    newW = int(H0 * target_ratio)
    side = (newW - W0) // 2
    strip = im.crop((0, 0, int(W0*0.05), H0)).resize((side+2, H0)) \
              .filter(GaussianBlur(int(side*0.10)))
    canvas.paste(strip, (0, 0)); canvas.paste(strip, (newW-side-2, 0))
    canvas.paste(im, (side, 0))
```

---

## 七、参数速查

```bash
--bg / --out          底图 / 输出
--title-img           笔刷标题 PNG（透明，已裁飞溅）
--brand               品牌名（底部居中，宽字距）
--tagline             品牌标语（品牌名下方）
--left-head           左侧大写三行（\n 分隔）
--left-sub            左侧小字补充
--right-head          右侧手写体两行
--right-sub           右侧小字补充
--badge-top           圆形徽章弧形文字
--badge-sub           圆形徽章下方小字
--left-foot           左下角三行脚注
--ratio / --save-size 比例适配 / 导出尺寸
```

---

## 八、技术备忘

**`ImageDraw` 没有 `alpha_composite`** —— 合成必须走画布 `Image` 对象：
```python
im.alpha_composite(layer)     # ✅
d.im.alpha_composite(layer)   # ❌ ImagingCore 无此方法
```

**弧形文字**（徽章用）：逐字旋转绘制 ——
```python
sub = Image.new("RGBA", (fs*2, fs*2), (0,0,0,0))
ImageDraw.Draw(sub).text((sub.width/2 - wch/2, sub.height/2 - fs*0.62), ch, font=f, fill=fill)
sub = sub.rotate(-(ang-90), expand=True, resample=Image.BICUBIC)
im.alpha_composite(sub, (px, py))
```

---

## 九、v1 → v2 进化对照（实测）

| 维度 | v1 极简 | v2 品牌版 | 参考图 |
|---|---|---|---|
| 标题 | Montserrat 字体渲染 | **生图笔刷 PNG + 叠压** | 笔刷 + 穿插 |
| 氛围 | 冷灰影棚 | **暖棕 + 焦散 + 蒸汽** | 暖棕 + 焦散 |
| 信息 | 3 层 | **7 处矩阵** | 7 处矩阵 |
| 徽章 | 无 | **圆形描金徽章** | 有 |
| 主体位置 | 22%H 起 | 16.7%H 起 | 约 20%H |
