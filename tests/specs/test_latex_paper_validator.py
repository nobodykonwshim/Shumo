from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skills.math_modeling.validation.latex_paper_validator import validate_tex


VALID = r"""
\documentclass{shumo-cumcm2025}
\begin{document}
\paperbodytarget{20}{30}
\papertitle{题目}
\begin{cnabstract}本文针对某问题建立模型并给出量化结果和检验结论。\end{cnabstract}
\keywords{模型；优化}
\clearpage
\section{问题重述}本文用完整段落说明问题背景、约束条件和需要完成的交付结果，避免把短句逐条堆叠成正文。
\section{模型建立与求解}
\subsection{问题一：示例模型}
先定义变量，再建立模型，并在正文中引用式~\eqref{eq:model}。
\keyequation{eq:model}{y=f(x)}
\begin{modelsummary}[问题一模型归纳]
输入为自变量与参数，输出为目标量，所有变量均在公式建立前定义。
\end{modelsummary}
\begin{solvercontract}[问题一算法求解说明]
\item[输入] 给定参数和数据。
\item[计算顺序] 先初始化，再计算模型输出。
\item[精度] 内部使用双精度，输出保留三位小数。
\item[特殊情况] 非法输入直接报错。
\end{solvercontract}
图~\ref{fig:a} 展示计算结果并在正文中解释趋势。
\begin{figure}[H]\centering\includegraphics{a.pdf}\caption{图}\label{fig:a}\end{figure}
\section{模型检验与讨论}通过一致性和敏感性分析检查结果，不隐藏不利结论。
\section{结论}本文直接汇总模型结果和适用边界，不增加未经验证的判断。
\begin{thebibliography}{9}\bibitem{x} 文献。\end{thebibliography}
\clearpage\appendix
\section{支撑材料文件列表}文件。
\section{完整源程序}\lstinputlisting{a.py}
\end{document}
"""


class LatexPaperValidatorTests(unittest.TestCase):
    def run_validation(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "main.tex"
            path.write_text(text, encoding="utf-8")
            return validate_tex(path)

    def test_valid_source_passes(self):
        self.assertEqual(self.run_validation(VALID)["status"], "pass")

    def test_table_of_contents_fails(self):
        result = self.run_validation(VALID.replace("\\clearpage", "\\tableofcontents\n\\clearpage", 1))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any(x["code"] == "table_of_contents_forbidden" for x in result["errors"]))

    def test_identity_term_fails(self):
        result = self.run_validation(VALID.replace("量化结果", "参赛学校：某校"))
        self.assertEqual(result["status"], "fail")

    def test_missing_appendix_fails(self):
        result = self.run_validation(VALID.replace("\\clearpage\\appendix", ""))
        self.assertEqual(result["status"], "fail")

    def test_raster_figure_warns(self):
        result = self.run_validation(VALID.replace("a.pdf", "a.png"))
        self.assertEqual(result["status"], "pass")
        self.assertTrue(any(x["code"] == "raster_figure" for x in result["warnings"]))

    def test_body_target_is_required(self):
        result = self.run_validation(VALID.replace("\\paperbodytarget{20}{30}\n", ""))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any(x["code"] == "body_page_target_required" for x in result["errors"]))

    def test_model_summary_is_required_for_each_problem(self):
        result = self.run_validation(VALID.replace("\\begin{modelsummary}[问题一模型归纳]", "\\begin{quote}").replace("\\end{modelsummary}", "\\end{quote}"))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any(x["code"] == "model_summary_missing" for x in result["errors"]))

    def test_solver_contract_requires_precision_and_special_cases(self):
        broken = VALID.replace("\\item[精度] 内部使用双精度，输出保留三位小数。\n", "").replace("\\item[特殊情况] 非法输入直接报错。\n", "")
        result = self.run_validation(broken)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any(x["code"] == "solver_contract_incomplete" for x in result["errors"]))


if __name__ == "__main__":
    unittest.main()
