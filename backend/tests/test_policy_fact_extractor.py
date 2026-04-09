from ai.ingestion.vector_store import RetrievedChunk
from ai.policy.fact_extractor import answer_structured_policy_question, detect_requested_policy_fact_keys, extract_policy_facts


def test_extract_policyholders_and_policy_number_from_allstate_style_chunk() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Policyholder(s)\nAnlan Cai\nMingtao Ding\n55 E Hntngtn Dr #219\n"
                "Policy number\n804 448 188\n"
            ),
            document_id="policy_pdf",
            page_num=1,
            section=None,
            metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
        )
    ]

    facts = extract_policy_facts(chunks)

    assert facts["policyholders"][0].value == "Anlan Cai, Mingtao Ding"
    assert facts["policy_number"][0].value == "804 448 188"


def test_answer_structured_policy_question_prefers_deterministic_fact_answer() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text="Policyholders: Mingtao Ding Yizhan Huang Policy Number: 871890019",
            document_id="policy_pdf",
            page_num=1,
            section="PROGRESSIVE",
            metadata={"source_label": "Your Policy (Verification of Insurance.pdf)"},
        )
    ]

    answer = answer_structured_policy_question("Who are the policyholders and what is the policy number?", chunks)

    assert answer is not None
    assert "Mingtao Ding" in answer.answer
    assert "871890019" in answer.answer
    assert len(answer.citations) >= 1
    assert answer.citations[0].source_type == "kb_a"


def test_answer_structured_policy_question_handles_document_type_and_policyholders() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Here is your automobile insurance renewal offer for the next six months. "
                "Policyholder(s) Anlan Cai Mingtao Ding Policy number 804 448 188"
            ),
            document_id="policy_pdf",
            page_num=1,
            section="RENEWAL",
            metadata={"source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)"},
        )
    ]

    answer = answer_structured_policy_question(
        "What kind of insurance packet is this and who are the policyholders?",
        chunks,
    )

    assert answer is not None
    assert "renewal" in answer.answer.lower()
    assert "Anlan Cai" in answer.answer
    assert "Mingtao Ding" in answer.answer


def test_answer_structured_policy_question_handles_policy_number_period_and_insurer() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Policy Number: 871890019 Underwritten by: Progressive Select Ins Co "
                "Policy period: Apr 4, 2026 - Oct 4, 2026"
            ),
            document_id="policy_pdf",
            page_num=1,
            section="PROGRESSIVE",
            metadata={"source_label": "Your Policy (Verification of Insurance.pdf)"},
        )
    ]

    answer = answer_structured_policy_question(
        "What is the policy number, policy period, and insurer?",
        chunks,
    )

    assert answer is not None
    assert "871890019" in answer.answer
    assert "Apr 4, 2026" in answer.answer
    assert "Oct 4, 2026" in answer.answer
    assert "Progressive Select Ins Co" in answer.answer


def test_answer_structured_policy_question_handles_discount_without_false_policy_period_requirement() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Your premium for the current policy period has not been affected. "
                "Your discount savings for this policy period\nare: $965.29."
            ),
            document_id="policy_pdf",
            page_num=1,
            section="DISCOUNTS",
            metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
        )
    ]

    assert detect_requested_policy_fact_keys("What discount savings are listed for this policy period?") == {
        "discount_total"
    }

    answer = answer_structured_policy_question(
        "What discount savings are listed for this policy period?",
        chunks,
    )

    assert answer is not None
    assert "$965.29" in answer.answer


def test_answer_structured_policy_question_handles_liability_limits_and_rental_reimbursement() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Coverage detail for 2024 Hyundai Elantra\n"
                "Coverage Limits Deductible Premium\n"
                "Automobile Liability Insurance Not applicable $1,235.12\n"
                "Bodily Injury $50,000 each person\n$100,000 each occurrence\n"
                "Property Damage $50,000 each occurrence\n"
                "Auto Collision Insurance Not purchased*\n"
                "Auto Comprehensive Insurance Not purchased*\n"
                "Rental Reimbursement Not purchased*\n"
            ),
            document_id="policy_pdf",
            page_num=2,
            section="COVERAGE DETAIL",
            metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
        )
    ]

    answer = answer_structured_policy_question(
        "What are the liability limits, and is rental reimbursement purchased?",
        chunks,
    )

    assert answer is not None
    assert "$50,000 each person" in answer.answer
    assert "$100,000 each occurrence" in answer.answer
    assert "Rental Reimbursement as Not purchased" in answer.answer


def test_answer_structured_policy_question_handles_vehicle_and_vin() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Vehicle information\n"
                "Vehicle: 2024 HYUNDAI ELANTRA HYBRID\n"
                "Vehicle identification number: KMHLN4DJ8RU107842\n"
            ),
            document_id="policy_pdf",
            page_num=1,
            section="VEHICLE INFORMATION",
            metadata={"source_label": "Your Policy (Verification of Insurance.pdf)"},
        )
    ]

    answer = answer_structured_policy_question(
        "What vehicle and VIN are listed in this verification of insurance?",
        chunks,
    )

    assert answer is not None
    assert "2024 HYUNDAI ELANTRA HYBRID" in answer.answer
    assert "KMHLN4DJ8RU107842" in answer.answer


def test_answer_structured_policy_question_handles_identity_theft_limit_and_deductible() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Allstate Identity Theft Expenses Coverage\n"
                "If you are currently receiving the Good Driver discount, you can purchase Identity Theft Expenses Coverage for "
                "just $15 per policy period and no deductible. The cost is $20 per policy period for those without the Good Driver "
                "discount. With this coverage, we'll reimburse you for covered expenses you incur to help restore your identity, "
                "up to a coverage limit of $25,000.\n"
            ),
            document_id="policy_pdf",
            page_num=1,
            section="OPTIONAL COVERAGE",
            metadata={"source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)"},
        )
    ]

    answer = answer_structured_policy_question(
        "What deductible and coverage limit are described for Identity Theft Expenses Coverage?",
        chunks,
    )

    assert answer is not None
    assert "no deductible" in answer.answer.lower()
    assert "$25,000" in answer.answer
