"""判定行自数器（KB0 §6 检查 27 的自我适用，`data/probe_*.py` 共用）。

两份探针脚本都把"成立 / 不成立 / 无法复算"逐行打印，但此前 KB7 §6 引用的汇总是**人工点数**的结果，
而且两处点的是不同口径（B 组 106/7/6 只数行尾判词标记，5171 的 219/24/12 数的是含关键字的行）。
本模块把汇总改成脚本自己打印，口径只有一处定义：

    一行算一条判定 ⟺ 去掉成对的 `*` 强调标记后，行尾是 `成立` / `不成立` / `无法复算（…）`
    （允许尾随括号注释，如 `成立（零命中）`）；`不成立` 优先于 `成立`，一行只计一次。
    判定再分两类：**对拍判定**（行内指向被检文档的登记值，即"本仓复算的数 vs 文档登记的数"，
    文档与台账只能引用这一类）与**脚本自设的子判定**（「差一个常数」一类，
    是主线程为判成因临时加的打印，不在文档断言清单里）。判别用 `DOC_REF`（`复算|报告|KB\\d|§|登记`），
    两类之和 = 本脚本打印的全部判定行。

已知盲区（宁可少计，不可虚计）：判词出现在行中而非行尾的打印（如 `成立：<值>`）不计入——
这类行的数字在行尾，会被"行尾判词"口径漏掉，汇总因此是**下界**；引用时按汇总行原样抄，
不要按关键字行数手工点数。

用法（探针脚本顶部，早于第一条 print）：

    import probe_tally
    probe_tally.install()
"""
import atexit
import re
import sys

OK_TAIL = re.compile(r"(?<!不)成立(?:（[^）]*）)?\**$")
BAD_TAIL = re.compile(r"不成立(?:（[^）]*）)?\**$")
NA_TAIL = re.compile(r"无法复算（.*）\**$")
# 一行是"对拍"而非脚本自设的子判定，当且仅当它指向被检文档里的某条登记（复算值 / 报告 / KB / § / 登记）
DOC_REF = re.compile(r"复算|报告|KB\d|§|登记")


class _Tee:
    def __init__(self, stream):
        self.src, self.buf = stream, []

    def write(self, s):
        self.buf.append(s)
        return self.src.write(s)

    def flush(self):
        return self.src.flush()

    def lines(self):
        return [ln.strip() for ln in "".join(self.buf).splitlines()]

    def report(self):
        """返回 {(doc|sub): (成立, 不成立, 无法复算)}。

        doc = 行内含 DOC_REF 命中的文档指向（复算值 vs 被检文档登记的数），即**对拍判定**，
              文档与台账只能引用这一类；
        sub = 脚本自己临时立的子判定（如「差一个常数」），不是文档里的断言。
        """
        out = {"doc": [0, 0, 0], "sub": [0, 0, 0]}
        for ln in self.lines():
            if BAD_TAIL.search(ln):
                idx = 1
            elif OK_TAIL.search(ln):
                idx = 0
            elif NA_TAIL.search(ln):
                idx = 2
            else:
                continue
            out["doc" if DOC_REF.search(ln) else "sub"][idx] += 1
        return {k: tuple(v) for k, v in out.items()}


def install():
    tee = _Tee(sys.stdout)
    sys.stdout = tee

    def _finish():
        sys.stdout = tee.src
        (d_ok, d_bad, d_na), (s_ok, s_bad, _) = tee.report().values()
        print("\n== 汇总（本脚本自数的判定行数；口径见 data/probe_tally.py 文档）==")
        print("  对拍判定（行内指向被检文档的登记值）：成立 %d ‖ 不成立 %d ‖ 无法复算 %d"
              % (d_ok, d_bad, d_na))
        print("  脚本自设的子判定（不是文档断言，勿引用为对拍数）：成立 %d ‖ 不成立 %d"
              % (s_ok, s_bad))
        print("  总打印 %d 行" % len(tee.lines()))

    atexit.register(_finish)
    return tee
