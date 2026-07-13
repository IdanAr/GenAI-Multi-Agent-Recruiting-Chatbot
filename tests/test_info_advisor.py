"""test_info_advisor.py - tests for the Phase 4 Info Advisor.

Deterministic parts (conversation formatting, agent wiring) run offline.
Behavioral tests that call the LLM / Chroma skip gracefully without a key.
"""

import os

import pytest
from dotenv import load_dotenv

from app.modules.advisors import common
from app.modules.advisors import info_advisor

load_dotenv()  # so the skipif below sees OPENAI_API_KEY when present

_HAS_KEY = bool(os.getenv("OPENAI_API_KEY"))


# --- deterministic, offline ---------------------------------------------- #
def test_format_conversation_labels_speakers():
    history = [
        {"speaker": "recruiter", "text": "Hi there!"},
        {"speaker": "candidate", "text": "What frameworks do you use?"},
    ]
    formatted = common.format_conversation(history)
    assert formatted == "Recruiter: Hi there!\nCandidate: What frameworks do you use?"


def test_format_conversation_passthrough_string():
    assert common.format_conversation("already text") == "already text"


def test_build_info_advisor_wiring():
    """The executor builds and exposes the retrieval tool."""
    executor = info_advisor.build_info_advisor()
    tool_names = [t.name for t in executor.tools]
    assert "retrieve_job_information" in tool_names
    assert executor.return_intermediate_steps is True


# --- behavioral (needs API key + built Chroma collection) ---------------- #
@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_role_question_triggers_retrieval():
    """A role question should make the advisor retrieve and answer from the JD."""
    history = [
        {"speaker": "recruiter", "text": "Thanks for applying to the Python Developer role."},
        {"speaker": "candidate", "text": "Which Python web frameworks would I use?"},
    ]
    result = info_advisor.run_info_advisor(history)
    assert result["info_needed"] is True
    assert isinstance(result["answer"], str) and result["answer"]


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_non_question_skips_retrieval():
    """A simple acknowledgement should not require retrieval."""
    history = [
        {"speaker": "recruiter", "text": "You would work with Django and Flask."},
        {"speaker": "candidate", "text": "Sounds good, thanks!"},
    ]
    result = info_advisor.run_info_advisor(history)
    assert result["info_needed"] is False
