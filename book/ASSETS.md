# ASSETS —— 本卷资产清单

> 一句话：**这本书有哪些文件、各是干什么的、门禁在哪儿、现在跑出来什么结果。**
> 清单在 2026-10-24 实测，数字可复核（命令见每节末尾）。
>
> **清单里的行数与合计由 `tools/verify_book_numbers.py` 核**——
> 资产表会随编辑漂移，漂了就是一张假清单，所以它有门。
> （**字节数不写进正文**：写下一个数字会改变文件大小，那种引用无法自洽。）

---

## 一、文件清单

### 1.1 正文（`book/chapters/` + 书级前后言）

| 文件 | 行 | 章节 |
|---|---|---|
| `chapters/00-导读.md` | 131 | 导读：怎么读、坐标怎么用、章速查 |
| `chapters/ch01-这是什么.md` | 233 | 边界、合法性根基、安全边界、三档退出码 |
| `chapters/ch02-契约先行.md` | 358 | C1–C7、21 条不可协商规则、core_hash |
| `chapters/ch03-知识库.md` | 305 | 扁平编号、五档 tier、"看不见 ≠ 没有"、引用完整性 |
| `chapters/ch04-外部证据与归属.md` | 297 | 三轴正交、五档来源、复用标注义务 |
| `chapters/ch05-引擎.md` | 352 | 三层依赖、接入层、时间轴硬门槛、CLI 序列 |
| `chapters/ch06-特征与归因.md` | 482 | S(e) 四因子、聚合公式、CAP、算例手算、ECE |
| `chapters/ch07-评估协议.md` | 403 | A-88、60/40 冻结、指标、top1_hit=0、规模下限 |
| `chapters/ch08-数据与脱敏.md` | 493 | 三组公开数据、侧车 19 字段、四条硬规则、三 token 门、**值类扫描门** |
| `chapters/ch09-诚实账与停机点.md` | 632 | 账面 vs 实测、三笔账、四件套、停机宣告、本卷自己的账、**清账战役** |
| `前言.md` | 109 | 定位、为什么用坐标、本卷怎么写自己 |
| `尾声.md` | 137 | 三件结论、本卷的诚实账、给下一个来的人 |

### 1.2 工具（`book/tools/`）

| 文件 | 行 | 干什么 | 失败时 |
|---|---|---|---|
| `tools/_anchor.py` | 32 | 锚点**唯一**定义 | — |
| `tools/audit_coords.py` | 295 | 坐标解析 + 行锚断言 | exit 1 |
| `tools/check_book_structure.py` | 160 | 逐章必备件 + 锚点串一致性 | exit 1 |
| `tools/verify_crops_verbatim.py` | 68 | 裁剪件逐字核对 | exit 1 |
| `tools/verify_book_numbers.py` | 285 | 书中数字：带文件名的行数、资产表行数、**自报门禁数字** | exit 1 |
| `tools/scan_absolute_paths.py` | 185 | 脱敏/绝对路径扫描（已清偿的登记项**不再豁免**） | exit 1 |
| `tools/check_broken_links.py` | 215 | 断链分八类 | exit 1 |
| `tools/build_crops.py` | 208 | 裁剪件生成器（唯一生成器） | — |
| `tools/locate.py` | 77 | 写作期反查：这句话在哪一行 | exit 1 |

`locate.py` 是**写作期**工具，不是门禁：写书时先查出行号再落笔，
免得凭印象写坐标。

### 1.3 数据与登记

| 文件 | 行 | 干什么 |
|---|---|---|
| `checks.json` | 421 | 行锚断言：120 条"这一行必须含哪几个词" |
| `evidence/axiscope-36e2c74-decision-list.md` | 72 | vendor 进来的收尾决策清单（原件 sha256 一致） |
| `evidence/REGISTRY.json` | 27 | 仓外原件登记：指针 + size + sha256 |
| `known_findings.json` | 51 | 查出来的既有问题及其处置（K-1、K-2，**均已清偿**） |
| `crops/裁剪版.md` | 187 | 裁剪件（**生成物**，勿手改） |
| `OUTLINE.md` | 125 | 本卷规格：每章交付什么、什么算完成 |
| `README.md` | 125 | 书的入口页 |
| `ASSETS.md` | 160 |

**全卷合计：28 件 / 6,454 行。**

---

## 二、门禁与实测结果

**2026-10-24 本机实跑**（Python 3.14.9，Windows）：

| 门禁 | 命令 | 结果 |
|---|---|---|
| 坐标审计 | `python book/tools/audit_coords.py` | **引用 759 ｜ 可解析 759 ｜ 失败 0 ｜ 行锚断言核对 367** ✅ |
| 结构体检 | `python book/tools/check_book_structure.py` | **章数 9/9；问题章数 0** ✅ |
| 裁剪件逐字 | `python book/tools/verify_crops_verbatim.py` | **18 段逐字命中；不一致 0** ✅ |
| 书中数字 | `python book/tools/verify_book_numbers.py` | **全部一致** ✅ |
| 脱敏/路径 | `python book/tools/scan_absolute_paths.py` | **未清 0 处**（豁免/登记 42 处） ✅ |
| 仓内值扫描 | `python data/probe_pii.py` | **三组全绿**：数据侧 token 归零、构建产物归零、**跟踪文件里六档值全 0**（主机路径 / 墙钟三形态 / 完整 NetID / 内网 IP）；**带理由的豁免**每次运行都打印 ✅ |
| 断链 | `python book/tools/check_broken_links.py` | **真断链 0** ｜ 记录性 3 ｜ 反例 11 ｜ 不入库区 31 ｜ 外部项目 2 ✅ |
| 仓内测试 | `python -m pytest -q` | **404 passed**（本机有原始数据时）；干净克隆里 294 passed / 110 skipped ✅ |

**一条坐标的完整链路**（读者可以照着走一遍）：

```
书里写   `docs/kb/KB0-conventions.md:26-29`
   ↓ audit_coords.py
读锚点   git show 7f7c37e:docs/kb/KB0-conventions.md
   ↓ 打印被引行原文
人工核对 那一行说的是不是书里那句话
   ↓ checks.json
机器核对 那一行含不含登记词（如 "看不见"、"没有"）
```

**367 处行锚断言**是这个卷的核心机制：
光验"行号存在"只能挡住行锚腐烂，挡不住**指错行**——
而指错行更常见，也更危险。

## 三、三个自指的门

这一卷的门禁里有三个是**指向它自己**的，值得单说：

| 门 | 挡的是什么 |
|---|---|
| `checks.json`（行锚断言） | 坐标指向**错的行**——行在，但不在说那句话 |
| 资产表行数核对 | 清单随编辑**漂了**——改完正文忘了改清单，清单就成了假清单 |
| 自报门禁数字核对 | 书里**关于自己**的那几行写旧了——改一次正文，坐标数就变，而正文里那句"引用 759"没人会去核对 |

第三条是这卷里最晚写、也最有用的一条：
**书里最容易变旧的，恰恰是它自己**。
所以工具会把「书里说的」和「当场实跑的」绑在一起对。

## 四、坐标的两个发现

**其一**：`src/agent` 目录**在 `d5717fb` 与 `7f7c37e` 两个提交下都不存在**，
而收尾文档的账面栏写了"`src/axiscope` + `src/agent`"
（`docs/项目回顾与收尾_20261022.md:26`）。这是**陈旧标注**，
数字本身没错。收尾文档是 2026-10-22 的历史事实，本卷**不改**它，
只在 ch09 §9.3.1 记明。

**其二**：收尾文档的 5,263 行是**非空行**口径，全部行是 6,039 行。
两个数字都对，差的是口径——**不交代口径就报差值，等于制造一个不存在的发现**。
ch09 §9.3 整节讲这件事。

## 五、复现

```powershell
git clone https://github.com/JosephIvon/axiscope
cd axiscope
python -m pip install "pytest==9.1.1" "numpy==2.5.3" "scipy==1.18.1"
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

## 六、边界声明

| 项 | 状态 |
|---|---|
| 本卷改动的仓内代码 | **11 处文件、约 20 行**，全部是**等行内替换**（不增删行，行号指针不失效）。逐条列在 ch09 §9.6.3：脱敏值令牌化（`src/` `tests/` `docs/` `data/`）、探针加扫描组与退出码、`.gitignore` 加规则、取消跟踪一份未脱敏的原始数据 |
| 本卷动过的仓外文件 | 3 处：`README.md`（加书入口，既有义务段一字未动）、CI workflow（加 `book` 作业 + 修「CI 从没装过任何依赖、从来就是红的」这个既有 bug）、`data/*.py` 19 个探针脚本（补 stdout 强制 utf-8 的房规，runner 控制台是 cp1252） |
| 本卷新增的目录 | **仅 `book/`** |
| 本卷发现的既有问题 | 2 条（`K-1` 文档侧 NetID、`K-2` 仓内未脱敏原始数据副本），**都已清偿**（清账战役，含**重写历史**把那份从历史里清掉；代价见 ch09 §9.7.2） |
| 坐标锚点 | `axiscope@7f7c37e`（单点定义于 `book/tools/_anchor.py`） |
| 仓外原件 | 1 件（收尾决策清单），已 vendor + 登记 sha256 |
