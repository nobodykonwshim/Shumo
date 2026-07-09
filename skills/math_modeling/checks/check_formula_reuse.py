#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公式重复定义审查脚本

用途：
    这是通用数模 Skill 的审查脚本，只负责执行检查规则；
    具体赛题的公式库、参数库和模型边界规则应放在对应项目目录中，
    例如 2024A/registry/model_contracts.yaml。

用法示例：
    python skills/math_modeling/checks/check_formula_reuse.py \
        --contract 2024A/registry/model_contracts.yaml \
        --problem problem3 \
        --tex sections/problem3.tex
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_contract(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("缺少 PyYAML，请先安装：pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def collect_forbidden_phrases(contract: dict, problem: str) -> list[str]:
    phrases: list[str] = []

    global_rules = contract.get("global_rules", {})
    phrases.extend(global_rules.get("forbidden_general_phrases_when_reused", []) or [])

    problem_rules = contract.get(problem, {})
    phrases.extend(problem_rules.get("forbidden_redefine", []) or [])

    # 兼容旧版结构：bench_dragon.problemX
    bench = contract.get("bench_dragon", {})
    if isinstance(bench, dict):
        legacy_problem_rules = bench.get(problem, {})
        phrases.extend(legacy_problem_rules.get("forbidden_redefine", []) or [])

    return list(dict.fromkeys(str(p) for p in phrases if str(p).strip()))


def check_tex(tex: str, forbidden_phrases: list[str]) -> list[str]:
    hits = []
    for phrase in forbidden_phrases:
        if phrase in tex:
            hits.append(phrase)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="检查数学建模章节是否重复定义前文模型。")
    parser.add_argument("--contract", required=True, type=Path, help="项目 model_contracts.yaml 路径")
    parser.add_argument("--problem", required=True, help="问题编号，例如 problem3")
    parser.add_argument("--tex", required=True, type=Path, help="待检查 LaTeX 文件路径")
    args = parser.parse_args()

    contract = load_contract(args.contract)
    tex = args.tex.read_text(encoding="utf-8")
    forbidden = collect_forbidden_phrases(contract, args.problem)
    hits = check_tex(tex, forbidden)

    if hits:
        print("[FAIL] 发现疑似重复定义或禁止表达：")
        for item in hits:
            print(f"  - {item}")
        print("\n处理方式：将上述内容改为引用前文式号或调用已有模型，不要重新推导。")
        return 1

    print("[PASS] 未发现合同中登记的重复定义关键词。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
