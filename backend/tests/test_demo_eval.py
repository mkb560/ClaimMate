from scripts.run_demo_eval import _passes


def test_passes_when_expected_substrings_and_citations_exist() -> None:
    passed, missing = _passes(
        "The policy number is 804 448 188 and the policyholders are Anlan Cai and Mingtao Ding.",
        expected_substrings=("804 448 188", "Anlan", "Mingtao"),
        citations=1,
        min_citations=1,
    )

    assert passed is True
    assert missing == []


def test_passes_reports_missing_substrings() -> None:
    passed, missing = _passes(
        "The policy number is 804 448 188.",
        expected_substrings=("804 448 188", "Mingtao"),
        citations=1,
        min_citations=1,
    )

    assert passed is False
    assert missing == ["Mingtao"]
