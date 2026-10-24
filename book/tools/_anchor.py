# -*- coding: utf-8 -*-
"""坐标锚点：**全书只此一处**定义。

为什么单独一个文件：书里每一处坐标都写着 `axiscope@<commit>`，而工具读源文件时
也要用一个 commit。这两个东西**必须**是同一个——写成两处，早晚有一天它们会分叉，
于是"书里说的锚"与"工具实际读的锚"对不上，审计器却全绿：
**那正是"0 失败"变成假话的典型形状。**

所以：
  · 锚点只在这里改；
  · `check_book_structure.py` 会核对**正文里写的锚点字符串**与本文件一致，
    对不上直接判红；
  · 切锚的规矩：**先改这里并提交（那一版含最终代码与真值基座），
    再改书里正文里的锚点字符串**。顺序反了，书就会去核一个还不存在的 commit。
"""
from __future__ import annotations

#: 代码坐标按这个 commit 读（`git show <rev>:<path>`）
ANCHOR_COMMIT = "7f7c37e"

#: 书里正文用的写法（与正文里的字符串必须逐字一致，由结构门禁核对）
ANCHOR_LABEL = f"axiscope@{ANCHOR_COMMIT}"

#: 本卷在三册里的正式名。三册的对应关系由书仓 `OUTLINE-VOL2S.md` 规定：
#:   第一册《协议域卷》= mcopilot ｜ 第二册《审计与合规卷》= axiscope ｜
#:   第三册《代码工厂与真值链卷》= trae_factory
#: **这一条只能是本册的名字**——曾经写成《协议域卷》（那是 mcopilot 那本），
#: 抄结构时带过来的，结构门禁不查卷名所以一直没红。现在查了。
VOLUME_NAME = "《审计与合规卷》"

#: 仓名（书里 `axiscope@<commit>` 的前半截）
REPO_NAME = "axiscope"
