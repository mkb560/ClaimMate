from pathlib import Path

from ai.ingestion.ingest_policy import _policy_source_label


def test_policy_source_label_uses_file_name() -> None:
    label = _policy_source_label(Path("/tmp/sample-policy.pdf"))
    assert label == "Your Policy (sample-policy.pdf)"


def test_policy_source_label_falls_back_to_default() -> None:
    assert _policy_source_label(None) == "Your Policy"
