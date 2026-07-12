# GenAI Multi-Agent Recruiting Chatbot

An SMS-style recruiting chatbot for a **Python Developer** role, built as a
Streamlit proof of concept. It talks to candidates, answers role questions,
and either **schedules an interview** with a human recruiter or **politely
ends** the conversation.

> Status: work in progress. This README is filled in phase by phase.

## Purpose

The bot runs one conversation turn at a time. A **Main Agent** orchestrates
each turn and consults exactly one specialized **Advisor**, then commits to one
of three actions:

- **Continue** the conversation
- **Schedule** an interview
- **End** the conversation

The advisors are:

- **Info Advisor** - answers role questions using RAG over a Chroma vector store
  built from the job description, and steers toward scheduling.
- **Scheduling Advisor** - checks recruiter availability in a SQL database via
  function calling and proposes the three nearest available slots.
- **Exit Advisor** - detects when a conversation should end, using prompt
  engineering with few-shot examples (no fine-tuning).

## Tech stack

- **LangChain** - agents, memory, tools
- **OpenAI API** - chat completions and embeddings
- **Chroma** - local vector store for RAG
- **SQLite** (via SQLAlchemy) - recruiter availability, queried by function calling
- **Streamlit** - proof-of-concept UI
- **scikit-learn / seaborn** - evaluation (Accuracy + Confusion Matrix)

## Installation

Requires Python 3.14.

```bash
git clone <your-repo-url>
cd "GenAI Multi-Agent Recruiting Chatbot"
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Then create your environment file:

```bash
copy .env.example .env        # Windows
# edit .env and set OPENAI_API_KEY=...
```

## Usage

```bash
# Run the Streamlit proof of concept (available from Phase 8):
streamlit run streamlit_app/streamlit_main.py
```

Additional entry points (embedding the PDF, building the scheduling DB, running
the evaluation notebook) are documented as each phase lands.

## Project structure

```text
GenAI Multi-Agent Recruiting Chatbot/
|- app/
|  |- __init__.py
|  |- main.py                 # application entry point
|  |- modules/
|  |  |- __init__.py
|  |  |- config.py            # model names + paths (env-overridable)
|  |  |- embedding.py         # offline PDF -> Chroma (Phase 2)
|  |  |- scheduling_tool.py   # SQL availability via function calling (Phase 3)
|  |  |- main_agent.py        # turn orchestration (Phase 6)
|  |  |- advisors/
|  |  |  |- __init__.py
|  |  |  |- info_advisor.py
|  |  |  |- scheduling_advisor.py
|  |  |  |- exit_advisor.py
|  |- prompts/                # version-controlled prompt text per agent
|     |- __init__.py
|- streamlit_app/
|  |- __init__.py
|  |- streamlit_main.py       # Streamlit PoC (Phase 8)
|- tests/
|  |- __init__.py
|  |- test_main.py            # smoke tests
|  |- test_evals.ipynb        # Accuracy + Confusion Matrix (Phase 7)
|- data/                      # Chroma store (ignored) + SQLite DB (tracked)
|- requirements.txt
|- .env.example
|- .gitignore
|- README.md
```
