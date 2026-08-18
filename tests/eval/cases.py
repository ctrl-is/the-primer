"""Re-exported from primer_core.eval.cases.

The eval-case builders (EngagementEvalCase, build_education_eval_case,
build_finance_eval_case, etc.) are consumed at runtime by primer_core.eval
itself (metrics.py, swap_test.py, determinism.py, harness.py) -- including
via the `primer-eval` console script, which runs outside pytest and has no
access to the `tests` package. The real implementation therefore lives in
the shipped package at primer_core/eval/cases.py; this module just keeps
existing test imports (`from tests.eval.cases import ...`) working.
"""

from __future__ import annotations

from primer_core.eval.cases import (
    CASE_BUILDERS,
    EDUCATION_INPUT,
    EDUCATION_SKILL,
    EDUCATION_SUBJECT_ID,
    EDUCATION_THREAD_ID,
    FINANCE_INPUT,
    FINANCE_SKILL,
    FINANCE_SUBJECT_ID,
    FINANCE_THREAD_ID,
    CaseBuilder,
    EngagementEvalCase,
    build_education_eval_case,
    build_finance_eval_case,
)

__all__ = [
    "CASE_BUILDERS",
    "EDUCATION_INPUT",
    "EDUCATION_SKILL",
    "EDUCATION_SUBJECT_ID",
    "EDUCATION_THREAD_ID",
    "FINANCE_INPUT",
    "FINANCE_SKILL",
    "FINANCE_SUBJECT_ID",
    "FINANCE_THREAD_ID",
    "CaseBuilder",
    "EngagementEvalCase",
    "build_education_eval_case",
    "build_finance_eval_case",
]
