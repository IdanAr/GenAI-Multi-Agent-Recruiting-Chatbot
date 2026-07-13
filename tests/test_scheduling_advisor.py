"""test_scheduling_advisor.py - tests for the Phase 4 Scheduling Advisor.

Deterministic wiring runs offline; behavioral tests that call the LLM skip
gracefully without an API key.
"""

import os

import pytest
from dotenv import load_dotenv

from app.modules.advisors import scheduling_advisor

load_dotenv()
_HAS_KEY = bool(os.getenv("OPENAI_API_KEY"))


def test_build_scheduling_advisor_wiring():
    executor = scheduling_advisor.build_scheduling_advisor()
    tool_names = [t.name for t in executor.tools]
    assert "find_interview_slots" in tool_names
    assert executor.return_intermediate_steps is True


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_agreement_triggers_scheduling():
    """Candidate agreeing to interview -> advisor looks up slots."""
    history = [
        {"speaker": "recruiter", "text": "Would you like to interview for the Python Developer role?"},
        {"speaker": "candidate", "text": "Yes, I'd love to. Maybe next Friday?"},
    ]
    result = scheduling_advisor.run_scheduling_advisor(history, reference_date="2024-04-03")
    assert result["should_schedule"] is True
    # The tool output must carry concrete available slots from the DB for that
    # Friday (the LLM may phrase the date naturally, e.g. "next Friday").
    assert any("2024-04" in slot for slot in result["slots"])


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_role_question_does_not_schedule():
    """A pure role question should not trigger scheduling."""
    history = [
        {"speaker": "recruiter", "text": "Thanks for applying to the Python Developer role."},
        {"speaker": "candidate", "text": "What databases does the team use?"},
    ]
    result = scheduling_advisor.run_scheduling_advisor(history, reference_date="2024-04-03")
    assert result["should_schedule"] is False
