from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skills.math_modeling.validation.latex_paper_validator import validate_tex


VALID = r"""
\documentclass{shumo-cumcm2025}
\begin{document}
\papertitle{题目}
\begin{cnabstract}摘要。\end{cnabstract}
\keywords{模型；优化}
\clearpage
\section{问题重述}正文引用式~\eqref{eq:model}和图~\ref{fig:a}。
\keyequation{eq:model}{y=x}
\begin{figure}[H]\centering\includegraphics{a.pdf}\caption{图}\label{fig:a}\end{figure}
\section{结论}结论。
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
        result = self.run_validation(VALID.replace("摘要。", "参赛学校：某校"))
        self.assertEqual(result["status"], "fail")

    def test_missing_appendix_fails(self):
        result = self.run_validation(VALID.replace("\\clearpage\\appendix", ""))
        self.assertEqual(result["status"], "fail")

    def test_raster_figure_warns(self):
        result = self.run_validation(VALID.replace("a.pdf", "a.png"))
        self.assertEqual(result["status"], "pass")
        self.assertTrue(any(x["code"] == "raster_figure" for x in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
