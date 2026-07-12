"""app.modules.advisors - the specialized advisor agents.

Each advisor reads the complete chat history and returns a single
binary decision back to the Main Agent:
- info_advisor: Info needed (RAG over Chroma) / Info not needed.
- scheduling_advisor: Schedule (SQL slot retrieval) / Don't schedule.
- exit_advisor: End conversation / Don't end (prompt-engineered, few-shot).
"""
