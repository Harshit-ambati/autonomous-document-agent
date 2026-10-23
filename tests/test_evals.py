"""Regression checks that the evaluator detects real artifact and content errors."""

import copy
from pathlib import Path

from evals.run import CASES, evaluate, load_recorded

FIXTURES = Path(__file__).resolve().parents[1] / "evals" / "fixtures"


def failed_names(checks):
    return {check.name for check in checks if not check.passed}


def test_recorded_cases_pass():
    for case in CASES:
        payload, docx = load_recorded(case, FIXTURES)
        assert not failed_names(evaluate(case, payload, docx))


def test_mismatched_word_file_fails():
    standard, standard_docx = load_recorded(CASES[0], FIXTURES)
    _, complex_docx = load_recorded(CASES[1], FIXTURES)
    assert standard_docx != complex_docx
    assert "JSON/Word content parity" in failed_names(evaluate(CASES[0], standard, complex_docx))


def test_missing_review_check_fails():
    payload, docx = load_recorded(CASES[0], FIXTURES)
    tampered = copy.deepcopy(payload)
    checks = tampered["reviews"][-1]["checks"]
    checks.remove(next(check for check in checks if check["requirement_index"] == 1))
    assert "self-check coverage" in failed_names(evaluate(CASES[0], tampered, docx))


def test_wrong_budget_total_fails():
    payload, docx = load_recorded(CASES[1], FIXTURES)
    tampered = copy.deepcopy(payload)
    tampered["document"]["sections"][0]["tables"][0]["rows"][-1][-1] = "999,999.00"
    assert "exact engineering estimate" in failed_names(evaluate(CASES[1], tampered, docx))
