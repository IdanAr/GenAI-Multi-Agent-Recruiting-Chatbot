"""exit_advisor.py - Conversation Exit Advisor (Phase 4, refined in Phase 5).

Detects conversations that should end. Built purely through prompt engineering
(role + instruction prompt, low temperature, and - from Phase 5 - few-shot
examples drawn from the labeled data). No fine-tuning is used anywhere.

The advisor is a JSON classifier built with the course pattern
(ChatPromptTemplate | ChatOpenAI | JsonOutputParser).

    result = run_exit_advisor(history)
    # -> {"should_end": bool, "decision": "end"|"continue", "reason": str}
"""

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.modules.advisors.common import get_chat_llm, format_conversation
from app.prompts.exit_advisor import EXIT_ADVISOR_SYSTEM

# Temperature 0: the exit decision should be stable and repeatable.
_TEMPERATURE = 0.0


def build_exit_advisor(few_shot_text: str = "", llm=None):
    """Build the Exit Advisor chain.

    Args:
        few_shot_text: optional block of worked examples appended to the system
            prompt (used from Phase 5). Empty means the naive engineered prompt.
    """
    llm = llm or get_chat_llm(temperature=_TEMPERATURE)
    system = EXIT_ADVISOR_SYSTEM
    if few_shot_text:
        system = f"{system}\n\nExamples:\n{few_shot_text}"
    # Pass the system text as a fixed SystemMessage so its literal JSON braces
    # are not interpreted as prompt-template variables. Only the user message
    # is templated (on {input}).
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system),
        ("user", "Conversation:\n{input}\n\nReturn only the JSON decision."),
    ])
    return prompt | llm | JsonOutputParser()


def run_exit_advisor(history, few_shot_text: str = "", llm=None) -> dict:
    """Classify whether the conversation should end.

    Args:
        history: conversation as a list of {'speaker', 'text'} turns, or a string.
        few_shot_text: optional few-shot block (Phase 5).

    Returns:
        {"should_end": bool, "decision": "end"|"continue", "reason": str}
        On any parsing failure the advisor defaults to "continue" (the safe,
        non-terminating choice).
    """
    conversation = format_conversation(history)
    chain = build_exit_advisor(few_shot_text, llm)
    try:
        raw = chain.invoke({"input": conversation})
        decision = str(raw.get("decision", "continue")).strip().lower()
        reason = raw.get("reason", "")
    except Exception:
        decision, reason = "continue", "parse-fallback"

    if decision not in ("end", "continue"):
        decision = "continue"
    return {
        "should_end": decision == "end",
        "decision": decision,
        "reason": reason,
    }
