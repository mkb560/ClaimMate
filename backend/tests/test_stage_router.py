from ai.chat.stage_router import determine_stage
from models.ai_types import ChatStage, Participant


def test_stage_router_returns_stage_1_for_owner_only() -> None:
    stage = determine_stage([Participant(user_id="1", role="owner")], invite_sent=False)
    assert stage == ChatStage.STAGE_1


def test_stage_router_returns_stage_2_when_invite_sent() -> None:
    stage = determine_stage([Participant(user_id="1", role="owner")], invite_sent=True)
    assert stage == ChatStage.STAGE_2


def test_stage_router_returns_stage_3_when_external_party_joins() -> None:
    stage = determine_stage(
        [
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
    )
    assert stage == ChatStage.STAGE_3

