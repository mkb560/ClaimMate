from scripts.run_demo_eval import _missing_source_types, _passes


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


def test_passes_accepts_any_of_groups() -> None:
    passed, missing = _passes(
        "The insurer must acknowledge receipt within 15 calendar days and begin any necessary investigation.",
        expected_substrings=(),
        expected_any_groups=(
            ("15", "15 calendar days"),
            ("acknowledge", "acknowledgment"),
            ("investigation", "begin any necessary investigation"),
        ),
        citations=1,
        min_citations=1,
    )

    assert passed is True
    assert missing == []


def test_missing_source_types_reports_required_citation_sources() -> None:
    missing = _missing_source_types(
        citation_source_types={"kb_a"},
        required_source_types=("kb_a", "kb_b"),
    )

    assert missing == ["kb_b"]
