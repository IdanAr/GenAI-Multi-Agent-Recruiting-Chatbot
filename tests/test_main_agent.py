"""test_main_agent.py - tests for the Phase 6 Main Agent orchestration.

Memory conversion is tested offline. The end-to-end multi-turn integration test
calls the LLM and skips gracefully without an API key.
"""

import os

import pytest
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.modules import main_agent
from app.modules.main_agent import MainAgent

load_dotenv()
_HAS_KEY = bool(os.getenv("OPENAI_API_KEY"))


def _echo_llm():
    """A fake LLM (Runnable) that echoes the rendered prompt back as the reply.

    Lets us assert offline that the candidate context reaches the prompt, without
    calling the real API. Mirrors the taught chain shape: prompt | llm | parser.
    """
    return RunnableLambda(lambda prompt_value: AIMessage(content=prompt_value.to_string()))


def _raising_llm():
    """A fake LLM (Runnable) that fails, to exercise the fallback path."""
    def _boom(_prompt_value):
        raise RuntimeError("no API available")
    return RunnableLambda(_boom)


def test_compose_opening_uses_name_and_experience():
    """The greeting prompt must receive the candidate's name and experience."""
    reply = main_agent.compose_opening("Dana", "3-5", llm=_echo_llm())
    assert "Dana" in reply
    assert "3-5" in reply


def test_compose_opening_falls_back_when_llm_fails():
    """Any LLM failure returns the static fallback opener, never an exception."""
    reply = main_agent.compose_opening("Dana", "3-5", llm=_raising_llm())
    assert reply == main_agent._FALLBACK_OPENING


def test_compose_opening_works_without_candidate_context():
    """The console has no registration form, so name/experience are optional."""
    reply = main_agent.compose_opening(llm=_echo_llm())
    assert isinstance(reply, str) and reply.strip()


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


def test_exit_veto_delegates_to_scheduling(monkeypatch):
    """When the router picks 'exit' but the exit advisor vetoes ending, the turn
    must hand off to the Scheduling advisor (which checks the DB) - not the Info
    advisor, which would hallucinate an "I'll check availability" promise.
    """
    monkeypatch.setattr(main_agent, "route",
                        lambda history, llm=None: {"advisor": "exit", "reason": ""})
    monkeypatch.setattr(main_agent, "run_exit_advisor",
                        lambda history, llm=None: {"should_end": False,
                                                   "decision": "continue", "reason": ""})
    sched_out = {"should_schedule": True, "answer": "Here are three slots ...",
                 "slots": ["2024-04-05 at 09:00:00", "2024-04-05 at 12:00:00",
                           "2024-04-05 at 13:00:00"]}
    monkeypatch.setattr(main_agent, "run_scheduling_advisor",
                        lambda history, reference_date=None, llm=None: sched_out)
    # Info advisor must NOT be consulted on the exit-veto path.
    monkeypatch.setattr(main_agent, "run_info_advisor",
                        lambda history, llm=None: (_ for _ in ()).throw(
                            AssertionError("Info advisor should not run on exit-veto")))

    result = main_agent.decide_action([{"speaker": "candidate", "text": "Wednesday works for me"}],
                                      reference_date="2024-04-03")
    assert result["action"] == "schedule"
    assert result["advisor"] == "scheduling"
    assert result["advisor_output"]["slots"] == sched_out["slots"]


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
