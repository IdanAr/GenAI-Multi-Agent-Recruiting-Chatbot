"""common.py - shared helpers for the advisor agents.

Small utilities reused by the Info, Scheduling, and Exit advisors (and later
the Main Agent): a ChatOpenAI factory that loads the API key, and a formatter
that turns a conversation (list of turns) into readable text for a prompt.
"""

from app.modules import config

# Map raw speaker labels (as they appear in sms_conversations.json and in the
# app) to readable role names used inside prompts.
_SPEAKER_LABEL = {
    "candidate": "Candidate",
    "user": "Candidate",
    "recruiter": "Recruiter",
    "assistant": "Recruiter",
    "bot": "Recruiter",
}


def get_chat_llm(temperature: float = 0.0, model: str = None):
    """Return a ChatOpenAI model, loading OPENAI_API_KEY from .env first."""
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI

    load_dotenv()
    return ChatOpenAI(model=model or config.CHAT_MODEL, temperature=temperature)


def format_conversation(history) -> str:
    """Format a conversation as 'Speaker: text' lines.

    Accepts either a ready-made string (returned as-is) or a list of turns,
    where each turn is a dict with 'speaker' and 'text' keys (the shape used by
    sms_conversations.json).
    """
    if isinstance(history, str):
        return history
    lines = []
    for turn in history:
        speaker = str(turn.get("speaker", "")).lower()
        label = _SPEAKER_LABEL.get(speaker, speaker.capitalize() or "Speaker")
        lines.append(f"{label}: {turn.get('text', '')}")
    return "\n".join(lines)
