"""test_main_agent.py - tests for the Phase 6 Main Agent orchestration.

Memory conversion is tested offline. The end-to-end multi-turn integration test
calls the LLM and skips gracefully without an API key.
"""

import os

import pytest
from dotenv import load_dotenv

from app.modules import main_agent
from app.modules.main_agent import MainAgent

load_dotenv()
_HAS_KEY = bool(os.getenv("OPENAI_API_KEY"))


def test_history_as_turns_maps_memory():
    """Human messages map to candidate, AI messages to recruiter, in order."""
    agent = MainAgent(reference_date="2024-04-03")
    agent.memory.add_user_message("hi")
    agent.memory.add_ai_message("hello, how can I help?")
    agent.memory.add_user_message("tell me about the role")
    turns = agent._history_as_turns()
    assert turns == [
        {"speaker": "candidate", "text": "hi"},
        {"speaker": "recruiter", "text": "hello, how can I help?"},
        {"speaker": "candidate", "text": "tell me about the role"},
    ]


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_route_returns_valid_advisor():
    history = [{"speaker": "candidate", "text": "What frameworks would I use?"}]
    routing = main_agent.route(history)
    assert routing["advisor"] in {"exit", "scheduling", "info"}


@pytest.mark.skipif(not _HAS_KEY, reason="requires OPENAI_API_KEY")
def test_full_conversation_runs_end_to_end():
    """A scripted conversation should schedule, then end, with memory intact."""
    agent = MainAgent(reference_date="2024-04-03")
    script = [
        "Hi, I saw the Python Developer opening.",
        "What frameworks and tools would I be working with?",
        "Sounds great. Could we schedule an interview, maybe next Friday?",
        "Monday at 3 PM is good.",
    ]
    results = [agent.run_turn(msg) for msg in script]

    assert len(results) == 4
    assert all(r["reply"] for r in results)                 # every turn replies
    assert any(r["action"] == "schedule" for r in results)  # scheduling happened
    assert results[-1]["action"] == "end"                   # conversation ends
    # memory holds both sides of all four turns
    assert len(agent.memory.messages) == 8
