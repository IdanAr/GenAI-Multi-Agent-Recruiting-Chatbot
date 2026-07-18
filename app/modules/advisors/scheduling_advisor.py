"""scheduling_advisor.py - Interview Scheduling Advisor (Phase 4).

Decides whether now is the right moment to schedule an interview. When it is,
the advisor calls the Phase 3 find_interview_slots tool to fetch the three
nearest available Python Developer slots (resolving the candidate's requested
timing from the conversation date) and proposes them. Because the tool only
returns available slots, any time the advisor proposes is already validated.

Built with the course LangChain agent pattern. The diagram's binary decision -
"Schedule" vs "Don't schedule" - is captured by whether the agent called the
scheduling tool on this turn.

    result = run_scheduling_advisor(history, reference_date="2024-04-03")
    # -> {"should_schedule": bool, "answer": str, "slots": [...]}
"""

from datetime import date

# langchain 1.x: the classic agent API lives in langchain_classic (see the
# note in info_advisor.py).
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.modules.advisors.common import get_chat_llm, format_conversation
from app.modules.scheduling_tool import (find_interview_slots, DEFAULT_POSITION,
                                         resolve_date_expression,
                                         get_nearest_available_slots)
from app.prompts.scheduling_advisor import (SCHEDULING_ADVISOR_SYSTEM,
                                            SCHED_PLAN_SYSTEM)

# Temperature 0: scheduling should be precise and consistent.
_TEMPERATURE = 0.0


def build_scheduling_advisor(llm=None) -> AgentExecutor:
    """Build the Scheduling Advisor agent executor."""
    llm = llm or get_chat_llm(temperature=_TEMPERATURE)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SCHEDULING_ADVISOR_SYSTEM),
        ("user",
         "Current date: {reference_date}\n\nConversation so far:\n{input}\n\n"
         "Write the recruiter's next reply."),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, [find_interview_slots], prompt)
    return AgentExecutor(
        agent=agent,
        tools=[find_interview_slots],
        return_intermediate_steps=True,
        verbose=False,
    )


def _plan_scheduling(history, llm=None) -> dict:
    """One planning call: whether to skip scheduling, and the date preference.

    Returns {"skip": bool, "date_expression": str}. The agent-based tool-calling
    approach was unreliable at proactively proposing times, so scheduling is
    driven deterministically from this plan instead.
    """
    llm = llm or get_chat_llm(temperature=_TEMPERATURE)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SCHED_PLAN_SYSTEM),
        ("user", "Conversation:\n{input}\n\nReturn only the JSON."),
    ])
    chain = prompt | llm | JsonOutputParser()
    try:
        raw = chain.invoke({"input": format_conversation(history)})
        return {
            "skip": bool(raw.get("skip", False)),
            "date_expression": str(raw.get("date_expression", "") or ""),
        }
    except Exception:
        return {"skip": False, "date_expression": ""}


def run_scheduling_advisor(history, reference_date: str = None, llm=None) -> dict:
    """Run the Scheduling Advisor on a conversation and return its decision.

    Args:
        history: conversation as a list of {'speaker', 'text'} turns, or a string.
        reference_date: the conversation date in ISO format (YYYY-MM-DD), used to
            resolve relative timing. Defaults to today.

    Returns:
        {"should_schedule": bool, "answer": str, "slots": list[str]}
        ``slots`` is one display string per available slot (for example
        "2024-04-03 at 09:00:00"), so a UI can offer them as discrete choices.
        should_schedule is True unless the candidate declined. A candidate who
        accepts or proposes a time still schedules: we re-surface the real
        available slots so the booking is confirmed from validated options (via
        the picker), never from unverified free text.
    """
    reference_date = reference_date or date.today().isoformat()
    plan = _plan_scheduling(history, llm=llm)

    if plan["skip"]:
        return {
            "should_schedule": False,
            "answer": "No problem - just let me know if there is anything else I can help with.",
            "slots": [],
        }

    # Resolve the requested timing (via the same Phase 3 logic the tool uses) and
    # fetch the three nearest available slots as structured rows, so we can return
    # them both as a human-readable reply and as discrete, selectable options.
    try:
        reference = date.fromisoformat(reference_date)
    except (ValueError, TypeError):
        reference = date.today()
    target = resolve_date_expression(plan["date_expression"], reference)
    slot_rows = get_nearest_available_slots(target, position=DEFAULT_POSITION, n=3)
    slots = [f"{row['date']} at {row['time']}" for row in slot_rows]

    if not slots:
        return {
            "should_schedule": False,
            "answer": (f"I couldn't find open {DEFAULT_POSITION} interview slots on or "
                       f"after {target.isoformat()}. Let me know another time that "
                       "works and I'll check again."),
            "slots": [],
        }

    reply = ("Let's get your interview booked. The three nearest available slots are: "
             f"{'; '.join(slots)}. Which time works best for you?")
    return {"should_schedule": True, "answer": reply, "slots": slots}
