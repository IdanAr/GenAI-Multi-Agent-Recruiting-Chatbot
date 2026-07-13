"""test_exit_advisor.py - tests for the Phase 4 Exit Advisor.

Wiring runs offline; the End/Continue behavioral checks call the LLM and skip
gracefully without an API key. Broader agreement-with-labels measurement is
done in Phase 5.
"""

import os

import pytest
from dotenv import load_dotenv

from app.modules.advisors import exit_advisor

load_dotenv()
_HAS_KEY = bool(os.getenv("OPENAI_API_KEY"))


def test_build_exit_advisor_returns_runnable():
    chain = exit_advisor.build_exit_advisor()
    assert hasattr(chain, "invoke")
    chain_fs = exit_advisor.build_exit_advisor(few_shot_text="Example: ...")
    assert hasattr(chain_fs, "invoke")


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_not_interested_ends():
    history = [
        {"speaker": "recruiter", "text": "Would you like to interview for the Python Developer role?"},
        {"speaker": "candidate", "text": "No thanks, I just accepted another offer. Please remove me."},
    ]
    result = exit_advisor.run_exit_advisor(history)
    assert result["should_end"] is True
    assert result["decision"] in ("end", "continue")


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_confirmed_interview_ends():
    history = [
        {"speaker": "candidate", "text": "Monday at 3 PM is good."},
        {"speaker": "recruiter", "text": "Great, your interview is confirmed. You'll get a calendar invite shortly."},
    ]
    result = exit_advisor.run_exit_advisor(history)
    assert result["should_end"] is True


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_engaged_candidate_continues():
    history = [
        {"speaker": "recruiter", "text": "Thanks for applying to the Python Developer role."},
        {"speaker": "candidate", "text": "Thanks! What frameworks would I be working with?"},
    ]
    result = exit_advisor.run_exit_advisor(history)
    assert result["should_end"] is False
