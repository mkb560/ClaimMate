from ai.chat.mention_handler import contains_ai_mention, extract_ai_question


def test_extract_ai_question() -> None:
    assert extract_ai_question("Can you help? @AI What is my deductible?") == "What is my deductible?"


def test_contains_ai_mention_is_case_insensitive() -> None:
    assert contains_ai_mention("hey @ai can you help") is True
    assert contains_ai_mention("no assistant mention here") is False

