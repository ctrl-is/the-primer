from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from primer_core.eval.metrics import (
    MetricResult,
    TransitionMetricReport,
    precision_at_k,
    run_transition_metrics,
)
from tests.eval.test_retrieval_golden_fixtures import PROPOSED_K


@pytest.mark.eval
async def test_all_five_transition_metrics_pass_and_aggregate_into_report() -> None:
    """
    BDD Scenario #2
    ---------------
    Scenario: all five transition metrics pass and aggregate into the report

    Given run_transition_metrics(['education', 'coop-finance'])
    When declarative_orchestration, typed_models, port_conformance, protocol_compliance,
        and stateless_agents run
    Then each returns a passing MetricResult and TransitionMetricsReport.passed is True
    And typed_models proves the negative path (an undeclared dimension is
        rejected with ValueError)
    """
    # Given run_transition_metrics(['education', 'coop-finance'])
    report: TransitionMetricReport = await run_transition_metrics(["education", "coop-finance"])

    # When declarative_orchestration, typed_models, port_conformance, protocol_compliance,
    #   and stateless_agents run...
    # Then each returns a passing MetricResult and TransitionMetricsReport.passed is True
    try:
        assert report.passed
    except AssertionError:
        warning = ""
        for metric in report.metrics:
            if not metric.passed:
                warning += metric.detail + "\n"
        raise AssertionError(warning)

    # And typed_models proves the negative path (an undeclared dimension is
    #   rejected with ValueError)
    typed_models_metric = list(
        filter(lambda metric: metric.name == "typed_models", report.metrics)
    )[0]
    assert "undeclared and caught by validate_memory_entry" in typed_models_metric.detail


@pytest.mark.eval
async def test_retrieval_quality_is_scored_from_golden_fixtures() -> None:
    """
    BDD Scenario #3
    ---------------
    Scenario: retrieval quality is scored from the golden fixtures

    Given Rianna's tests/eval/fixtures/retrieval_golden.json
    When precision_at_k scores every case for both domains at the agreed k
    Then every case meets the agreed threshold and both domains share one scoring path
    """
    FIXTURE_PATH = Path(__file__).parent / "eval" / "fixtures" / "retrieval_golden.json"
    with open(FIXTURE_PATH) as json_file:
        golden = json.load(json_file)

    result: MetricResult = precision_at_k(fixture=golden, k_threshold=PROPOSED_K)
    assert result.passed


async def test_suite_is_runnable_as_first_class_entrypoint() -> None:
    """
    BDD Scenario #4
    ---------------
    Scenario: the suite is runnable as a first-class entrypoint

    Given the eval marker registered in pyproject.toml and a primer-eval console script
    When `uv run pytest -m eval -q` and `uv run primer-eval` execute
    Then the headline test passes and the script prints the formatted report,
        exiting 0 on pass / non-zero on fail
    """
    pytest_command = "uv run pytest -m eval -q".split()
    primer_eval_command = "uv run primer-eval".split()

    output = ""
    results = []

    repo_root = Path(__file__).resolve().parents[1]

    for command in (pytest_command, primer_eval_command):
        try:
            # When `uv run pytest -m eval -q` and `uv run primer-eval` execute
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, cwd=repo_root
            )
            output += result.stdout
            results.append(result)
        except subprocess.CalledProcessError as e:
            raise AssertionError(f'''Executed external command "{" ".join(pytest_command)}" failed:
    Exit code: {e.returncode}
    --- STDOUT ---
    {e.stdout}
    --- STDERR ---
    {e.stderr}
            ''')

    assert "3 passed" in output
    assert all(result.returncode == 0 for result in results)
