# axiscope

**离线伺服波形诊断与归因引擎。** 读厂商导出的伺服波形（TwinCAT / Scope 等 CSV），
按仓内数据契约与知识库做通道映射、特征抽取、判据求值与归因，产出一份**可复核**的样本包。
它不连设备、也不替缺失的输入编数——缺什么就说缺什么。

## 它解决什么问题

现场拿到一份伺服波形，卡住的通常不是"没数据"，而是**结论没法被别人当场核**：
通道名各厂不同、采样时基可能被动过、异常是"看出来的"、结论落不到具体行号。
本仓把这件事拆成可核的三段：

| 段 | 干什么 | 在哪 |
|---|---|---|
| **契约** | 数据长什么样、什么算**拒收**（拒收不是崩溃） | `docs/contracts/`（C1–C7） |
| **知识库** | 波形格式、通道语义、数据集溯源、脱敏规则 | `docs/kb/`（KB0、KB2–KB8） |
| **引擎** | 映射 → 特征 → 判据 → 归因 → 样本包 | `src/axiscope/` |

## 怎么跑

依赖只有数值栈（**numpy + scipy**）；CI 钉死了一套版本，见 `.github/workflows/tests.yml`。

```bash
python -m axiscope --in <厂商导出.csv> --out <样本包输出目录>
```

退出码是结论的一部分，不是副产品：

| 退出码 | 含义 |
|---|---|
| `0` | 断言与 C3 契约全过 |
| `1` | 断言或 C3 契约有未过项（明细打到 stderr） |
| `2` | **拒收**：输入不在 / 格式不符 / 契约不过——拒收 ≠ 崩溃 |

跑测试**不需要** `pip install -e .`（`tests/conftest.py` 自己把 `src/` 放进 `sys.path`）：

```bash
pytest
```

## 仓里有什么

| 路径 | 内容 |
|---|---|
| `src/axiscope/` | 引擎本体（映射 / 特征 / 判据 / 归因 / 置信度） |
| `docs/contracts/` | C1–C7 数据契约 |
| `docs/kb/` | KB0、KB2–KB8 知识库（格式、语义、溯源、脱敏） |
| `docs/AUDIT-*.md` | 历次审计与清偿记录 |
| `tests/` | 19 个测试文件 |
| `book/` | 与本仓**同仓**的电子书（[`book/README.md`](book/README.md)）——讲怎么让每个技术主张都能被第三方当场核验 |

## 许可

- 本仓**自有的代码与文档**：MIT，全文见 [`LICENSE`](LICENSE)。
- **第三方材料**（数据集、厂商导出记录等）**不适用** MIT，权利归各自权利人；
  逐件状态与署名要求见 [`NOTICE.md`](NOTICE.md)——`LICENSE` 只放 MIT 正文，范围说明在 NOTICE。
- 数据来源与署名的**逐字引用**在本文件下半部分的「数据来源与署名」一节。

---


仓库的规范与事实分散在 `docs/contracts/`（C1–C7）、`docs/kb/`（KB0、KB2–KB8）与 `docs/AUDIT-*.md`。
本节只承担两项既有披露义务：**数据来源与署名**、**复用设计标注**。二者均不新增结论，只抄录仓内已登记的原文并给出出处。

## 数据来源与署名

### 1. DaRUS（斯图加特大学）—— CC BY 4.0，须署名

以下四行**逐字抄自本仓库**，未作改写：

- 作者（`docs/kb/KB7-dataset-da-rus-cat.md:11`）：
  `Reichenbach, Thomas — University of Stuttgart (ROR 04vnq7t77)`
  （署名块的中文排版形式见 `docs/kb/KB2-waveform-formats.md` §6.2：
  `作者：Reichenbach, Thomas — University of Stuttgart（ROR 04vnq7t77）`）
- 许可（`docs/kb/KB7-dataset-da-rus-cat.md:13`）：`**CC BY 4.0** | **CC BY 4.0**`
  （DARUS-3600 / DARUS-5171 两列；散文形式见 `docs/kb/KB2-waveform-formats.md` §6.2：
  `许可：**CC BY 4.0**；引用须注明作者 + 机构 + DOI + 许可（KB7 署名要求）。`）
- 数据集 DOI（`docs/kb/KB7-dataset-da-rus-cat.md:15`）：`10.18419/DARUS-3600` 与 `10.18419/DARUS-5171`
  （同款登记见 `docs/kb/KB2-waveform-formats.md:526` 与 `:560` 两张样本卡的「许可 / 署名 / DOI」行。）
- 权利 URI（`data/raw/DD_head.csv.source.txt:5`，抄自 DaRUS API `latestVersion.license`）：
  `{"name":"CC BY 4.0","uri":"http://creativecommons.org/licenses/by/4.0"}`
  （同一 URI 亦逐字见于 `data/incoming/` 下 11 份 sidecar 的 `license:` 第 5 行，以及
  `data/raw/darus3600.json` / `data/raw/darus5171.json` 的 `latestVersion.license.uri` 字段。）

署名要求原文（`docs/kb/KB7-dataset-da-rus-cat.md:17`）：
`署名要求：引用须注明 Reichenbach/University of Stuttgart + DOI + CC BY 4.0。`

数据集标题按 KB7 出处与许可表首行（`docs/kb/KB7-dataset-da-rus-cat.md:10`）登记。
**已裁决（2026-10-22）**：仓内 API 留档 `data/raw/darus3600.json`（latestVersion
metadataBlocks typeName=title）与 KB7:10 **逐字一致**——发布方原文即 KB7 所记；
`Export10_244531.csv.source.txt:6` 旧记短标题系转述有误，已当日纠偏（见该侧车
第 6 行纠偏注与 notes 脱敏记录），两条字串不再并存。同日完成 KB2 §六脱敏
（发布门断言三 token 归零，执行记录 `data/redact_pii_20261022.py` + 侧车 md5 前后对照）。

### 2. ScienceDB（中国科学院合肥物质科学研究院 等离子体研究所）—— CC BY 4.0，须独立署名

- DOI（`docs/kb/KB7-dataset-da-rus-cat.md:32`）：`**`10.57760/sciencedb.04148`**`
- 创作者逐字（`docs/kb/KB7-dataset-da-rus-cat.md:40-41`）：
  `Huayuan Huang`（Institute of Plasma Physics, Hefei Institutes of Physical Science, **University of Science and Technology of China**）、
  `Hongtao Pan`、`Cheng, Yong`（后二者同属等离子体研究所）
- 权利与 URI（`docs/kb/KB7-dataset-da-rus-cat.md:38`）：
  `rightsList = [Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/legalcode]`
  （同值亦见 `data/VERIFICATION-2026-10-20.md:198`；工件快照 `data/datacite_sciencedb_04148_2026-10-20.json`。）
- 相关论文 DOI（`docs/kb/KB7-dataset-da-rus-cat.md:44`）：
  `relatedIdentifiers`：`IsSupplementTo → doi:10.1002/acs.3276`
  （仓内可重跑：`data/probe_kb7_b_group.py`，快照 `build/probe_kb7_b_group.out:48`。）
- 归属纪律（`docs/kb/KB7-dataset-da-rus-cat.md:420-422`）：引用须带该 DOI + CC BY 4.0，
  **不得**并入 "Reichenbach / University of Stuttgart" 一行；它是**机器人关节实验，不是半导体产线数据**。

**待补**：`doi:10.1002/acs.3276` 的**论文标题**在本仓库不存在。已检索 `docs/kb/`、`docs/contracts/`、`data/`、
`build/` 全部含 `10.1002/acs.3276` 的位置，四处命中一律只给 DOI 与关系型 `IsSupplementTo`，无标题字段；
`build/probe_kb7_b_group.out:351` 已把它判为「外部出版物，未落盘 ⟹ 无法复算」。此处不填、不改写、不凭记忆补全。

### 3. Zenodo 两包 —— CC BY 4.0，署名不得并入 DaRUS 一行

- `10.5281/zenodo.21456277` 作者（`docs/kb/KB7-dataset-da-rus-cat.md:102`）：
  `Bátrla Adam / Hercík Radim / Byrtus Radek / Majidzadeh Gorjani Ojan（VSB – TU Ostrava）`；
  引用要求（`:66`）：`引用须带该 DOI + CC BY 4.0，**不得**并入 "Reichenbach / University of Stuttgart" 一行。`
- `10.5281/zenodo.21526135`（`docs/kb/KB7-dataset-da-rus-cat.md:31`）登记为硬拒、不接入；其署名同样不得并入上表。

### 4. 追加登记的 DaRUS DOI（全部 CC BY 4.0）

`docs/kb/KB7-dataset-da-rus-cat.md:23-29` 逐行登记 `10.18419/DARUS-2563`、`-3003`、`-3252`、`-4224`、`-6114`、`-3759`、`-4152`。
**待补**：该表只含 DOI／标题／文件数／关键 fs／用途五列，**无作者列**；除 `-3759`（`Steinle, Lukas`）与
`-4152`（`Röder, Benedict; Ebel, Henrik; Eberhard, Peter`，见 `data/research_current_channel.md:34`、`:50`）外，
其余五个 DOI 的作者姓名在本仓库**未见登记**，不得据「同一系列」推定为 Reichenbach。

### 5. T1-b 四库：一律 `[待核]`

CWRU / Paderborn CM / Aalto / MFPT 的正式标识在 `docs/kb/KB7-dataset-da-rus-cat.md:434-437` 登记为 `[待核]`，
并按 A-67（`:427-428`）规定：「本文不编造 DOI、论文标题、文件名、采样率或任何数值」。本节同样不补。

### 6. 脱敏门禁（发布前必做 → **已执行 2026-10-22**）

脱敏字段级规则与断言以 `docs/kb/KB2-waveform-formats.md` §六（`:780`–`:818`）为准，其中 `:804` 逐字：
`脱敏**只清除主机路径 / ADS NetID / 绝对墙钟时刻**，绝不清除署名与 DOI，也不改动数值。`
命中清单见各 KB2 样本卡的「发布前必做」行（`docs/kb/KB2-waveform-formats.md:527`、`:561`）。
**已执行（2026-10-22，`adf4c4b`）**：一次性执行记录 `data/redact_pii_20261022.py`；
`data/probe_pii.py` 复跑三个标识值 token（厂区名 / IP 前缀 / 盘符）归零；
两个侧车登记 md5 前后对照（Export10 `8cba13df…`→`178a6308…`、DD_head `995d0d91…`→`3f80439d…`）。

### 7. 复用设计标注（非本项目原创的部分）

义务来源逐字：`docs/AUDIT-minimax-mcopilot.md:72`
「**归属纪律**：复用部分必须在 README 与作品集中标注来源，不得以"我写的"呈现。」

| 复用的设计 | 本仓库落点 | 标注来源（已在本仓库写明"非原创"） |
|---|---|---|
| 接入卡**九项字段结构**（minimax《厂商手册索取清单》） | KB2 §4「接入卡模板」 | `docs/kb/KB2-waveform-formats.md:369-371`：「该九项字段结构参考第三方智能体（minimax）《厂商手册索取清单》的工程做法，**不是本项目原创**」／「本项目只吸收其**格式**，不采用其任何 SDK 签名作为事实来源」；裁决原文 `docs/AUDIT-minimax-round3.md:77`「《索取清单》的 9 项结构**直接复用**」 |
| **七段 jerk 受限 S 曲线**轨迹生成器的设计思路 | KB5 §4.1–§4.2 | `docs/kb/KB5-simulation-plant.md:793-805`：「**参考来源（设计思路，非代码）**」+「**借鉴**：七段对称结构…」「**自己重写**：…」「不复制任何代码行」；来源与理由 `docs/AUDIT-minimax-mcopilot.md:57`（「**高价值，直接复用**」）、`:70`（「收割复用」） |
| `events.jsonl` 的 `source` 词表与判据雏形 | C6 | `docs/AUDIT-minimax-mcopilot.md:59`：「借鉴设计，**不采信其检出率**」 |
| 上位机代码规范的漏乘当量数据流检查 | 代码规范类条目 | `docs/AUDIT-minimax-mcopilot.md:60`：「借鉴，非核心」 |
| 雷赛 `pulse/s` vs 正运动 `单位/秒` 的**单位口径事故模式** | C5 §8 不可映射项清单、KB3、KB5 §7 | `docs/AUDIT-minimax-mcopilot.md:18-19`；落点引用 `docs/kb/KB5-simulation-plant.md:456` |
| **A/B/C 诚实分级**的呈现方式（用于跨厂商能力矩阵） | C5 §8、KB2 §4.9 | `docs/AUDIT-glm-code-factory.md:70-72`：「**A/B/C 诚实分级的呈现方式**用在我们自己的跨厂商能力矩阵上……**不采纳**它把清单交给被检对象自身生成的做法」 |
| **「验证性执行」作为交付门禁**（真编译、失败返回非 0） | C5「无依据成功声明 = 0 次」 | `docs/AUDIT-glm-code-factory.md:73-75` |
| **适配层口径错误**列为正式归因目标 | KB3 R-22 判据扩充 | `docs/AUDIT-glm-code-factory.md:65-69` |
| 「验证金字塔」三档 / 文档级真值双标注 / 完成度口径（A-90、A-92、A-93） | KB0 §4、§6 检查 24/25、§7.3 | `docs/AUDIT-glm-code-factory.md:110-129`；`docs/kb/KB0-conventions.md` §7.3 表后注：「A-87 / A-88 / A-89 是由外部会话触发的三条」（此处**不写行号**——A-117 实测同一份台账的行号指针会随表格增行漂移） |
| 六个**软件诱导缺陷形态**（DPOS 冒充反馈、`_unit` 双重换算、IO 电平当错误码、PSO 比较点、回零后 MPOS 未同步、锁存源选错） | KB3 / C3 | `docs/kb/KB2-waveform-formats.md:636-639`（A-33）：一律表述为「**第三方实现审计中出现的缺陷形态**」，「**禁止**写「手册确认的错误」或「我们的发现」」；裁决原文 `docs/AUDIT-minimax-round3.md:89-93` |

引用纪律：外部会话（minimax 三轮、GLM 系）的手册与 SDK 绑定**不在本仓库**，故其核对结论对本仓库
只是 `public-doc` / `verified_by = third_party_report`，**不计入本仓库的 `已核对 k`**
（`docs/kb/KB2-waveform-formats.md:619-628`，A-32 / A-89）。

---

## 许可与第三方材料

- 本仓**自有的代码与文档**：MIT（见 `LICENSE` ✓）。
- 本仓**收录了第三方材料**（DaRUS / ScienceDB / Zenodo 数据集的派生样本卡与知识库引文）✓，
  全部为 **CC BY 4.0，须署名** ✓ —— 完整署名正文见上文「**数据来源与署名**」一节 ✓
  （DaRUS / ScienceDB / Zenodo / 追加 DOI / T1-b / 脱敏门禁 / 复用设计标注 七节 ✓）。
- 本仓**不含原始数据** ✓：原始数据集均有 DOI 可随时重下 ✓，
  入库的是派生样本卡 + 独立算出的真值，两者靠指纹绑定 ✓（见 `data/PROVENANCE-TEMPLATE.md` ✓）。
- 逐件登记与"不替你决定的事"见 **`NOTICE.md`** ✓。

## 电子书（`book/`）——与代码同仓

`book/` 是一本讲**方法**的书：怎么让每一个技术主张都能被第三方当场核验。
它原先不是这个仓的一部分；2026-10-24 起随本仓同在，
**坐标锚在本仓自己的某一次提交上**（`axiscope@7f7c37e`）。

**读者手里没有锚点，坐标就只剩作者能核**——而"当场可核"正是这本书要证伪的那件事。

| 入口 | 内容 |
|---|---|
| [`book/README.md`](book/README.md) | 从哪读起 + 坐标怎么用 + 门禁怎么跑 |
| [`book/chapters/`](book/chapters/) | 九章正文 + 导读 + 前言 + 尾声 |
| [`book/crops/裁剪版.md`](book/crops/裁剪版.md) | 每章的「可验证主张」+「讲师 90 分钟切分」（**一件**） |
| [`book/tools/`](book/tools/) | 书自己的自检工具链（坐标审计 / 结构体检 / 裁剪核对 / 数字核对 / 脱敏扫描 / 断链检查） |

**书里的引用会过期，过期的引用比没有引用更坏**，所以有一道机器门禁：

```powershell
python book\tools\audit_coords.py        # 每处「文件:行号」解析回源文件 + 行锚断言
python book\tools\check_book_structure.py # 逐章必备件 + 锚点串一致性
```

CI 里 `book` 作业跑这六道门（`fetch-depth: 0` 是硬要求：
坐标审计要按**锚点 commit** 读源文件，浅克隆里没有那个 commit）。
