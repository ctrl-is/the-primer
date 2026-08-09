from __future__ import annotations

import pytest

from tests.eval.cases import (
    EngagementEvalCase,
    build_education_eval_case,
    build_finance_eval_case,
)


@pytest.fixture
def education_eval_case() -> EngagementEvalCase:
    return build_education_eval_case()


@pytest.fixture
def finance_eval_case() -> EngagementEvalCase:
    return build_finance_eval_case()
