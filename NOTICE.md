# NOTICE —— 第三方材料与再分发说明

本仓**自有的代码与文档**按 MIT 许可发布（见 `LICENSE`）。
本仓同时收录/引用了第三方材料；那些材料**不适用** MIT，其权利归各自权利人。

本文件**不重复**署名正文——完整署名块在 `README.md` 的
**「数据来源与署名」**一节（DaRUS / ScienceDB / Zenodo / 追加 DOI / T1-b / 脱敏门禁 / 复用设计标注 七节 ✓）。
本文件只回答一个问题：**这份 NOTICE 与那些署名正文是什么关系，读者该看哪一份** ✓。

---

## 一、仓内第三方材料一览

| 材料 | 出处 | 许可 | 处置与义务 |
|---|---|---|---|
| `bench/samples/T1a-DARUS-*/waveform.tsv`（7 件）+ `features/vel_fb_psd.npy`（7 件）+ `meta.json`（7 件） | 由 DaRUS 数据集派生的**样本卡**（注入/对照两类） | **CC BY 4.0** | 可再分发，**须署名**；署名块见 `README.md` §1（逐条 DOI ✓） |
| `docs/kb/KB7-dataset-da-rus-cat.md` 等知识库条目里的引文与波形特征 | 同上数据集的派生记录 | **CC BY 4.0** | 同上署名义务（知识库条目里已逐条记 DOI 与许可 ✓） |
| `docs/kb/` 中登记的 ScienceDB / Zenodo 两包 | 见 `README.md` §2 / §3 | **CC BY 4.0** | **须独立署名**，不得并入 DaRUS 一行 ✓ |
| `data/PROVENANCE-TEMPLATE.md`、`data/VERIFICATION-2026-10-20.md` | 本仓自有的来源/校验记录 | 本仓 | 但里面引用的上游母包路径已按脱敏规则改为占位 ✓ |

## 二、不在仓内的材料（原始数据不入库）

按本仓 A-131 口径：**代码与文档入库，原始数据不入库**（`data/raw/`、`data/incoming/`、
`data/staging/` 均在 `.gitignore` 中 ✓）。

理由：这些数据集**均有 DOI，可随时重下** ✓；入库的是**派生样本卡 + 独立算出的真值**，
两者靠 `csv_sha256` 之类的指纹绑定 ✓（见 `data/PROVENANCE-TEMPLATE.md` 与各 `meta.json` ✓）。
读者要复算，从 README 记的 DOI 重下原始件即可 ✓。

## 三、脱敏已执行（发布前必做 → 已执行 2026-10-22）

上游导出件里的**本机绝对路径**、机构标识值、IP 前缀已按 `docs/kb/KB2-waveform-formats.md` §六
的规则处理：路径整体替换为 `[REDACTED_HOST_PATH]`，只留 basename ✓；
`README.md` §6 记了复跑口径与三个标识值 token 的**归零**结果 ✓（2026-10-22 亲跑 ✓）。

> 纪律沿用本仓已写下的规则：本仓的 KB2 §六早已要求"路径 PII：只留 basename 或占位" ✓，
> 这次是把**还没执行到的地方执行掉**——不是新立规矩 ✓。

## 四、尚未定性、本 NOTICE 不替你决定的事

- **T1-b 四库**：许可与来源一律标 `[待核]`（`README.md` §5 ✓）——
  在核清之前，不得当作可用外部真值 ✓。
- **复用设计的标注**：`README.md` §7 已登记哪些部分非本项目原创 ✓；
  二次分发时请连同该节一起带上 ✓。
- **T1-a 与 T1-b 的关系**：本仓的样本分两级，T1-b 未就位属**设计性挂起**，不是缺件 ✓。

## 五、读者该看哪一份

| 你想知道 | 看这里 |
|---|---|
| 本仓代码能不能用、什么许可 | `LICENSE`（MIT ✓） |
| 数据是谁的、怎么署名 | `README.md`「数据来源与署名」✓ |
| 原始数据怎么重下 | `README.md` 各节的 DOI + `data/PROVENANCE-TEMPLATE.md` ✓ |
| 哪些路径被脱敏了、依据哪条规则 | `README.md` §6 + `docs/kb/KB2-waveform-formats.md` §六 ✓ |
| 还有哪些没核清 | `README.md` §5（T1-b）✓ + 本文件 §四 ✓ |
