"""main_agent.py - Main Agent turn orchestration (Phase 6).

Implements one conversation turn exactly as the workflow diagram describes:

1. Receive the candidate input (added to LangChain memory).
2. Route to exactly ONE advisor - Exit, Scheduling, or Info.
3. That advisor processes the full history and returns a binary decision.
4. Consume the advisor output and decide one of Continue / Schedule / End.
5. Reply to the candidate.

The action-decision logic lives in decide_action() as a pure function of the
conversation history, so the Phase 7 evaluation can call it per labeled turn.
MainAgent wraps it with LangChain memory (InMemoryChatMessageHistory) to drive a
real multi-turn conversation.
"""

from datetime import date

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.modules.advisors.common import get_chat_llm, format_conversation
from app.modules.advisors.info_advisor import run_info_advisor
from app.modules.advisors.scheduling_advisor import run_scheduling_advisor
from app.modules.advisors.exit_advisor import run_exit_advisor
from app.prompts.main_agent import MAIN_ROUTER_SYSTEM, MAIN_CLOSING_SYSTEM

# Low temperature: routing and closing should be stable.
_TEMPERATURE = 0.0
_VALID_ADVISORS = {"exit", "scheduling", "info"}


def route(history, llm=None) -> dict:
    """Choose which advisor to consult for this turn.

    Returns {"advisor": "exit"|"scheduling"|"info", "reason": str}. Falls back to
    "info" (the safe, conversation-continuing choice) on any parsing problem.
    """
    llm = llm or get_chat_llm(temperature=_TEMPERATURE)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=MAIN_ROUTER_SYSTEM),
        ("user", "Conversation:\n{input}\n\nReturn only the JSON decision."),
    ])
    chain = prompt | llm | JsonOutputParser()
    try:
        raw = chain.invoke({"input": format_conversation(history)})
        advisor = str(raw.get("advisor", "info")).strip().lower()
        reason = raw.get("reason", "")
    except Exception:
        advisor, reason = "info", "route-fallback"
    if advisor not in _VALID_ADVISORS:
        advisor = "info"
    return {"advisor": advisor, "reason": reason}


def compose_closing(history, llm=None) -> str:
    """Write a short closing message for a conversation that is ending."""
    llm = llm or get_chat_llm(temperature=0.3)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=MAIN_CLOSING_SYSTEM),
        ("user", "Conversation:\n{input}\n\nWrite the closing message."),
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"input": format_conversation(history)}).strip()


def decide_action(history, reference_date: str = None, llm=None) -> dict:
    """Run one turn's decision: route, consult one advisor, choose the action.

    Returns:
        {
          "action": "continue" | "schedule" | "end",
          "reply": str,                 # message to send the candidate
          "advisor": "exit"|"scheduling"|"info",
          "advisor_output": dict,       # the consulted advisor's raw result
        }
    """
    reference_date = reference_date or date.today().isoformat()
    routing = route(history, llm=llm)
    advisor = routing["advisor"]

    if advisor == "exit":
        exit_out = run_exit_advisor(history, llm=llm)
        if exit_out["should_end"]:
            return {
                "action": "end",
                "reply": compose_closing(history, llm=llm),
                "advisor": "exit",
                "advisor_output": exit_out,
            }
        # Exit advisor vetoed ending -> keep the conversation going via Info.
        info_out = run_info_advisor(history, llm=llm)
        return {
            "action": "continue",
            "reply": info_out["answer"],
            "advisor": "exit",
            "advisor_output": exit_out,
        }

    if advisor == "scheduling":
        sched_out = run_scheduling_advisor(history, reference_date=reference_date, llm=llm)
        return {
            "action": "schedule" if sched_out["should_schedule"] else "continue",
            "reply": sched_out["answer"],
            "advisor": "scheduling",
            "advisor_output": sched_out,
        }

    # advisor == "info"
    info_out = run_info_advisor(history, llm=llm)
    return {
        "action": "continue",
        "reply": info_out["answer"],
        "advisor": "info",
        "advisor_output": info_out,
    }


class MainAgent:
    """Drives a multi-turn conversation with LangChain memory."""

    def __init__(self, reference_date: str = None, llm=None):
        self.memory = InMemoryChatMessageHistory()
        self.reference_date = reference_date or date.today().isoformat()
        self.llm = llm

    def _history_as_turns(self) -> list[dict]:
        turns = []
        for message in self.memory.messages:
            speaker = "candidate" if message.type == "human" else "recruiter"
            turns.append({"speaker": speaker, "text": message.content})
        return turns

    def run_turn(self, candidate_message: str) -> dict:
        """Process one candidate message and return the turn result."""
        self.memory.add_user_message(candidate_message)
        result = decide_action(self._history_as_turns(),
                               reference_date=self.reference_date, llm=self.llm)
        self.memory.add_ai_message(result["reply"])
        return result
