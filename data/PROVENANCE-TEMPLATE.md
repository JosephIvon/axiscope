# 来源存证模板（`.source.txt`  sidecar）

**为什么需要**：KB2 §4 接入卡的 `external_reference` / `verified_against` / `verified_by` 三个槽位，
以及 C3 规则 17 的 `audit.external_ledger[]`，都要求「这份文件从哪来」是可复核的。
没有 sidecar，文件只能用于解析器回归自测，**不能**作为「厂商格式代表性」「公开数据集真机性」的证据（A-88 同源无证明力）。

**写法**：与被校验文件同名 + `.source.txt`，纯文本，一行一项。校验脚本会把里面的数字声明逐条 vs 实测，
不匹配的标 `CONTRADICTED`（`python data/validate_raw.py` 的「自述核对」段）。

```
url:                 <下载用的完整 URL，不可写"某某网站"这种转述>
retrieved_at:        <YYYY-MM-DD，实际抓取日期>
retrieved_by:        <人/智能体/工具；若由第三方会话取得，verified_by 不得记 self>
publisher:           <厂商 / 数据集发布方 / 作者全名>
license:             <许可证与能否再分发，例如 CC BY 4.0 / 厂商文档示例文件 / 未知>
dataset_doi:         <有则写，无则写 NONE；禁止编造>
original_filename:   <厂商设备/软件导出的原始文件名，未经重命名>
format_family:       <TwinCAT Scope View / Tektronix TDS ASCII / Rigol DS ASCII / 其他>
device_or_software:  <型号 + 固件/软件版本，用于接入卡 §格式版本>
sampling_rate:       <如 500 Hz>            ← 脚本会 vs 实测时基
rows:                <如 200001>            ← 脚本会 vs 实测数据行数
channels:            <如 11>                ← 脚本会 vs 实测列数
variable_semantics:  <每个列/变量的物理含义与单位，须抄自数据集文档原文，不得自行推断>
derived_from:        <若本文件是本地转换/截断/重命名产物，写清源文件与转换方式；未转换写 NONE>
upstream_id:         <出版方给的文件号（DaRUS dataFile id、仓库 commit、SN），凡"文件名不唯一"时必须写>
md5:                 <本文件实体的 MD5（32 位十六进制）>
verified_against:    <我方用什么独立对象核对过：重抓的 URL / 出版方 API 记录 / 母包哈希>
verified_by:         <核对主体：self（本会话亲自执行）/ 他人转述（则不得计入已核对 k）>
notes:               <截断、重命名、单位换算等处理痕迹>
```

**红线**：`url` / `license` / `variable_semantics` 任一项拿不到，就在接入卡里写
「来源未登记」并降低叙述措辞强度，不要用「疑似/应该是」填空（KB0 §6 检查 21：③a/③b 举证）。

**三条从踩坑里长出来的硬规则**（细则与实测数据见 `VERIFICATION-2026-10-20.md`）：

1. **派生文件的哈希是自证，不是来源证据**。`.mat → CSV`、截断、重命名后的文件由同一只手写出并登记，
   md5 相符只说明没转坏。校验脚本据 `derived_from`/`original_filename: NONE` 自动把这类核对
   标为"同源剔除"，不计入 `verified k`。要主张来源，就得核对**上游对象**（重抓字节、出版方 API 记录）。
2. **文件名不是标识**。DaRUS-3600 里叫 `Export 10.csv` 的文件有 18 个、md5 各不相同；
   唯一标识只能是 `upstream_id` + `md5` + `directoryLabel` 三件套。
3. **"URL 打不开" ≠ "不存在"**。GitHub 匿名 REST 超限会返回伪 404；判"查无此物"前必须换路径复验，
   且结论要写成「未登记」而不是「疑为某文件的片段」。
4. **核对判据要匹配文件形态**（2026-10-20 由 `DD_head.csv` 的反面教训补）。
   拿**整文件的 md5/filesize** 去两个库里找一个**前缀切片**，结构上就不可能命中——"0 命中"证明的是
   判据用错了，不是来源不存在。切片/派生件要发 `Range: bytes=0-<N-1>` 取回候选母本，
   做**逐字节前缀比对**（本会话即用此法把 `DD_head.csv` 的母本锁定为 DaRUS-5171 dataFile 394008，
   并排除了同目录同名的 394122——它在第 156 字节就分歧）。

## sidecar 盘点（2026-10-20 已完成，核对结果另存）

27 份 sidecar 已就位：`data/raw/` 13 份、`data/staging/` 6 份、`data/staging/原始mat/` 6 份，
另有 2 份对应 `D:\迅雷下载` 里的 zip 母包（未随文件安装）。
逐份 vs 实体的核对结果见 `validate_out.txt` / `validate_staging.txt` 的「自述核对账」，
本会话亲自执行的独立重抓取结果见 `VERIFICATION-2026-10-20.md`。

仍为缺口、不得越级措辞的三项（2026-10-20 20:00 复核后更新）：
- ScienceDB 数据集页面**未逐列定义变量含义与单位**（已由我方直接读页面证实）；
  其 500 Hz 只是 `tout` 步长的实测推断，来源等级停在 public-doc（页面文件表取不到，母包 MD5 无外部对照值）。
- **`data/raw/` 内无任何电流通道**（`cur_q`），频域/共振类判据按 KB2 §5.2 保持软降级。
  唯一有实测电流的样本是 `data/incoming/current-hunt/4152_Sine_0_output_00.txt`
  （DARUS-4152，Dynamixel 四连杆真机，250 Hz，`Goal/Pres. Current [mA]`），它**缺位置指令 ⟹ 无 fe**；
  而真 fe 样本（DARUS-3759 2 kHz、DARUS-5171 CDD 母本 1 kHz）都只记力矩不记电流。
  ⟹ **「同一份里既有真 fe 又有真 cur_q」这一格仍未闭合**，能力矩阵里须写 `not_mappable(公开数据无此样本)`。
- ~~`DD_head.csv` 来源未登记~~ **已纠正**：该文件是 DaRUS-5171 `dataFile 394008`
  （`CableDirectDrive_Testbed/2024-07-23_LdaFricIdent/Data/RW/Export 10.csv`）的前 400,001 字节前缀切片，
  本会话逐字节证实；早先"md5/filesize 双口径 0 命中 ⟹ 查无此文件"是判据用错（见上面硬规则 4）。
  母本可整文件取回（md5 已核），切片本身仍受 `n_samples<2000` 硬拒，只可用于表头/词表回归。

