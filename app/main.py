"""main.py - console entry point for the recruiting chatbot.

A simple terminal REPL that drives the Main Agent turn by turn. The Streamlit
proof of concept (streamlit_app/streamlit_main.py) is the primary UI; this is a
lightweight way to hold a conversation from the command line.

Run from the project root:
    python -m app.main
"""

from datetime import date

from app.modules import embedding, config
from app.modules.main_agent import MainAgent, compose_opening


def main() -> None:
    """Run an interactive console conversation with the Main Agent."""
    # Make sure the vector store and scheduling DB exist.
    embedding.ensure_collection()
    if not config.SQLITE_DB_PATH.exists():
        from app.modules.scheduling_tool import build_schedule_db
        build_schedule_db()

    agent = MainAgent(reference_date=date.today().isoformat())
    # The console has no registration form, so no candidate name/experience:
    # compose_opening still generates a fresh, agentic greeting (or falls back).
    opening = compose_opening()
    print("Python Developer Recruiting Chatbot (type 'quit' to exit)\n")
    print(f"Recruiter: {opening}\n")
    agent.memory.add_ai_message(opening)

    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in ("quit", "exit"):
            break

        result = agent.run_turn(message)
        print(f"\nRecruiter: {result['reply']}")
        print(f"   [action: {result['action']} | advisor: {result['advisor']}]\n")
        if result["action"] == "end":
            print("Conversation ended.")
            break


if __name__ == "__main__":
    main()
