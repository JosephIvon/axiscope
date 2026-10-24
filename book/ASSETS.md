# ASSETS —— 本卷资产清单

> 一句话：**这本书有哪些文件、各是干什么的、门禁在哪儿、现在跑出来什么结果。**
> 清单在 2026-10-24 实测，数字可复核（命令见每节末尾）。

---

## 一、文件清单

### 1.1 正文（`book/chapters/` + 书级前后言）

| 文件 | 行 | 章节 |
|---|---|---|
| `chapters/00-导读.md` | 128 | 导读：怎么读、坐标怎么用、章速查 |
| `chapters/ch01-这是什么.md` | 233 | 边界、合法性根基、安全边界、三档退出码 |
| `chapters/ch02-契约先行.md` | 358 | C1–C7、21 条不可协商规则、core_hash |
| `chapters/ch03-知识库.md` | 305 | 扁平编号、五档 tier、"看不见 ≠ 没有"、引用完整性 |
| `chapters/ch04-外部证据与归属.md` | 297 | 三轴正交、五档来源、复用标注义务 |
| `chapters/ch05-引擎.md` | 352 | 三层依赖、接入层、时间轴硬门槛、CLI 序列 |
| `chapters/ch06-特征与归因.md` | 482 | S(e) 四因子、聚合公式、CAP、算例手算、ECE |
| `chapters/ch07-评估协议.md` | 403 | A-88、60/40 冻结、指标、top1_hit=0、规模下限 |
| `chapters/ch08-数据与脱敏.md` | 395 | 三组公开数据、侧车 19 字段、四条硬规则、三 token 门 |
| `chapters/ch09-诚实账与停机点.md` | 414 | 账面 vs 实测、三笔账、四件套、停机宣告、本卷自己的账 |
| `前言.md` | 109 | 定位、为什么用坐标、本卷怎么写自己 |
| `尾声.md` | 135 | 三件结论、本卷的诚实账、给下一个来的人 |
| **小计** | **3 631** | 12 件 |

### 1.2 工具（`book/tools/`）

| 文件 | 行 | 干什么 | 失败时 |
|---|---|---|---|
| `_anchor.py` | 25 | 锚点**唯一**定义 | — |
| `audit_coords.py` | 295 | 坐标解析 + 行锚断言 | exit 1 |
| `check_book_structure.py` | 149 | 逐章必备件 + 锚点串一致性 | exit 1 |
| `verify_crops_verbatim.py` | 68 | 裁剪件逐字核对 | exit 1 |
| `verify_book_numbers.py` | 91 | 书中数字对实文件 | exit 1 |
| `scan_absolute_paths.py` | 173 | 脱敏/绝对路径扫描 | exit 1 |
| `check_broken_links.py` | 213 | 断链分七类 | exit 1 |
| `build_crops.py` | 208 | 裁剪件生成器（唯一生成器） | — |
| `locate.py` | 77 | 写作期反查：这句话在哪一行 | exit 1 |
| **小计** | **1 299** | 9 件 | |

`locate.py` 是**写作期**工具，不是门禁：写书时先查出行号再落笔，
免得凭印象写坐标。

### 1.3 数据与登记

| 文件 | 行 | 干什么 |
|---|---|---|
| `checks.json` | 421 | 行锚断言：120 条"这一行必须含哪几个词" |
| `evidence/axiscope-36e2c74-decision-list.md` | 72 | vendor 进来的收尾决策清单（原件 sha256 一致） |
| `evidence/REGISTRY.json` | 25 | 仓外原件登记：指针 + size + sha256 |
| `known_findings.json` | 21 | 查出来但不修改的既有问题（K-1） |
| `crops/裁剪版.md` | 187 | 裁剪件（**生成物**，勿手改） |
| **小计** | **726** | 5 件 |

**全卷合计：26 件 / 5 636 行 / 257.5 KB。**

---

## 二、门禁与实测结果

**2026-10-24 本机实跑**（Python 3.14.9，Windows）：

| 门禁 | 命令 | 结果 |
|---|---|---|
| 坐标审计 | `python book/tools/audit_coords.py` | **引用 743 ｜ 可解析 743 ｜ 失败 0 ｜ 行锚断言核对 365** ✅ |
| 结构体检 | `python book/tools/check_book_structure.py` | **章数 9/9；问题章数 0** ✅ |
| 裁剪件逐字 | `python book/tools/verify_crops_verbatim.py` | **18 段逐字命中；不一致 0** ✅ |
| 书中数字 | `python book/tools/verify_book_numbers.py` | **带文件名的数字 0 处，全部一致** ✅ |
| 脱敏/路径 | `python book/tools/scan_absolute_paths.py` | **未清 0 处**（豁免/登记 42 处） ✅ |
| 断链 | `python book/tools/check_broken_links.py` | **真断链 0** ｜ 记录性 3 ｜ 反例 11 ｜ 不入库区 28 ｜ 外部项目 2 ✅ |
| 仓内测试 | `python -m pytest -q` | **404 passed** ✅ |

**一条坐标的完整链路**（读者可以照着走一遍）：

```
书里写   `docs/kb/KB0-conventions.md:26-29`
   ↓ audit_coords.py
读锚点   git show 0bf4ad4:docs/kb/KB0-conventions.md
   ↓ 打印被引行原文
人工核对 那一行说的是不是书里那句话
   ↓ checks.json
机器核对 那一行含不含登记词（如 "看不见"、"没有"）
```

**365 处行锚断言**是这个卷的核心机制：
光验"行号存在"只能挡住行锚腐烂，挡不住**指错行**——
而指错行更常见，也更危险。

## 三、坐标的两个发现

**其一**：`src/agent` 目录**在 `ddd03af` 与 `0bf4ad4` 两个提交下都不存在**，
而收尾文档的账面栏写了"`src/axiscope` + `src/agent`"
（`docs/项目回顾与收尾_20261022.md:26`）。这是**陈旧标注**，
数字本身没错。收尾文档是 2026-10-22 的历史事实，本卷**不改**它，
只在 ch09 §9.3.1 记明。

**其二**：收尾文档的 5,263 行是**非空行**口径，全部行是 6,039 行。
两个数字都对，差的是口径——**不交代口径就报差值，等于制造一个不存在的发现**。
ch09 §9.3 整节讲这件事。

## 四、复现

```powershell
git clone https://github.com/<owner>/axiscope
cd axiscope
python -m pytest -q                      # 仓内测试
python book/tools/audit_coords.py        # 坐标审计
python book/tools/check_book_structure.py
python book/tools/verify_crops_verbatim.py
python book/tools/verify_book_numbers.py
python book/tools/scan_absolute_paths.py
python book/tools/check_broken_links.py
```

**重建裁剪件**（正文改过之后）：

```powershell
python book/tools/build_crops.py
python book/tools/verify_crops_verbatim.py   # 必须跟着跑，否则裁剪件与正文会分家
```

**写作期反查**：

```powershell
python book/tools/locate.py "看不见"          # 这句话在哪个文件第几行
python book/tools/locate.py --file KB4 "1641"
```

## 五、边界声明

| 项 | 状态 |
|---|---|
| 本卷改动的仓内代码 | **0 行**（`src/` `docs/` `tests/` 一行未动） |
| 本卷动过的仓外文件 | 2 件：`README.md`（加书入口，既有义务段一字未动）、CI workflow（加 `book` 作业 + 修「CI 从没装过任何依赖、从来就是红的」这个既有 bug） |
| 本卷新增的目录 | **仅 `book/`** |
| 本卷发现的既有问题 | 1 条（`K-1`），**登记在册并披露**，未修改 |
| 坐标锚点 | `axiscope@0bf4ad4`（单点定义于 `book/tools/_anchor.py`） |
| 仓外原件 | 1 件（收尾决策清单），已 vendor + 登记 sha256 |
