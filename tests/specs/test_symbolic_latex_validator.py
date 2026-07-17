import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT / "skills" / "math_modeling" / "validation" / "symbolic_latex_validator.py"
)
spec = importlib.util.spec_from_file_location("symbolic_latex_validator", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


ANALYSIS = r"""
\section{问题分析}
\subsection{问题一分析}
本问分析视线遮挡关系。
"""

MODEL = r"""
\section{模型的建立与求解}
\subsection{问题一的模型建立与求解}
\subsubsection{问题模型建立}
% SHUMO-SYMBOLIC-MODEL-BEGIN
\begin{equation}
  \bm r_B(t)=\bm r_d+v_F\bm e_F(t-t_d)-\frac{1}{2}g(t-t_d)^2\bm e_z .
  \label{eq:demo}
\end{equation}
令 $\lambda\in[0,1]$，由式\eqref{eq:demo}计算。
% SHUMO-SYMBOLIC-MODEL-END
\subsubsection{模型求解}
读取登记库。
\subsubsection{结果分析}
报告结果。
"""


class SymbolicLatexValidatorTests(unittest.TestCase):
    def test_symbolic_contract_passes(self):
        report = module.validate_symbolic_latex(
            ANALYSIS, MODEL, problem_name="问题一"
        )
        self.assertEqual(report["status"], "pass")

    def test_case_numeric_literal_in_model_fails(self):
        bad = MODEL.replace("v_F", "120", 1).replace("t_d", "1.5", 1)
        report = module.validate_symbolic_latex(
            ANALYSIS, bad, problem_name="问题一"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                item["code"] == "numeric_parameter_in_model"
                for item in report["errors"]
            )
        )

    def test_missing_chapter_contract_fails(self):
        report = module.validate_symbolic_latex(
            r"\subsection{问题一分析}", MODEL, problem_name="问题一"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                item["code"] == "analysis_section_contract"
                for item in report["errors"]
            )
        )

    def test_assumption_section_in_latex_fails(self):
        report = module.validate_symbolic_latex(
            ANALYSIS + r"\section{模型假设}", MODEL, problem_name="问题一"
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            any(
                item["code"] == "registry_only_assumption_violation"
                for item in report["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
