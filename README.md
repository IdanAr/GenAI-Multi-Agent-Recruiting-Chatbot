# GenAI Multi-Agent Recruiting Chatbot

An SMS-style recruiting chatbot for a **Python Developer** role, built as a
GenAI concepts and delivered by Streamlit UI.
This project made as part of Technion's final project (Course: GenAI 14) as a proof of concept,
which demonstrates a demo of agentic Chatbot.
It chats with candidates, answers role questions,
and either **schedules an interview** with a human recruiter or **politely ends** the conversation.

## Purpose

The bot runs one conversation turn at a time. A **Main Agent** orchestrates each
turn: it consults exactly one specialized **Advisor**, then commits to one of
three actions and replies to the candidate.

- **Continue** the conversation
- **Schedule** an interview
- **End** the conversation

The advisors are:

- **Info Advisor** - answers role questions using RAG over a Chroma vector store
  built from the job description, and steers toward scheduling.
- **Scheduling Advisor** - checks recruiter availability in a SQL database via
  function calling and proposes the three nearest available slots (resolving
  relative dates like "next Friday" from the conversation date).
- **Exit Advisor** - detects when a conversation should end, using prompt
  engineering with few-shot examples mined from the labeled data (no fine-tuning).

### One turn (control flow)

1. The candidate sends a message (or submits the registration form).
2. The Main Agent routes to one advisor: Exit, Scheduling, or Info.
3. The advisor reads the full history and returns a decision (with retrieval from
   Chroma or the SQL calendar where relevant).
4. The Main Agent chooses Continue / Schedule / End and replies.

## Tech stack

- **LangChain** - agents, memory, tools (1.x line; the classic `AgentExecutor`
  API lives in `langchain_classic`)
- **OpenAI API** - chat completions (`gpt-4o-mini`) and embeddings
  (`text-embedding-3-small`), both configurable in `app/modules/config.py`
- **Chroma** - local persistent vector store for RAG
- **SQLite** (via SQLAlchemy) - recruiter availability, queried by function calling
- **Streamlit** - proof-of-concept UI
- **scikit-learn / seaborn** - evaluation (Accuracy + Confusion Matrix)

## Installation

Requires **Python 3.14** locally.

```bash
git clone https://github.com/IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot.git
cd GenAI-Multi-Agent-Recruiting-Chatbot
python -m venv .venv
.venv\Scripts\activate          # Windows (use: source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

Create your environment file and add your OpenAI key:

```bash
copy .env.example .env          # Windows (use: cp on macOS/Linux)
# edit .env and set OPENAI_API_KEY=sk-...
```

## Usage

### Run the Streamlit proof of concept

```bash
streamlit run streamlit_app/streamlit_main.py
```

Register with a name and contact, then chat. The app builds the Chroma vector
store and the scheduling database automatically on first run if they are missing.
Each reply shows a small caption with the chosen action and advisor.

### Run the console version

```bash
python -m app.main
```

### Rebuild the data artifacts manually (optional)

```bash
python -m app.modules.embedding          # build the Chroma collection from the PDF
python -m app.modules.scheduling_tool    # (re)build data/tech.db from the seed
python -m app.modules.data_exploration   # print a report on the three inputs
```

### Run the tests and the evaluation

```bash
pytest                                   # unit + integration tests
jupyter notebook tests/test_evals.ipynb  # Accuracy + Confusion Matrix over the labeled data
```

## Evaluation

`tests/test_evals.ipynb` runs the full system over the labeled conversations
(`sms_conversations.json`) and compares the predicted action against the label at
each recruiter turn. On the 44 labeled turns the system reaches about **0.68
accuracy**, with **End** detected reliably (recall ~0.87). The main confusion is
on the Continue/Schedule boundary, where the labels themselves are noisy (the
recruiter sometimes asks another question and sometimes proposes an interview
after a near-identical candidate answer). The Exit Advisor's few-shot prompt beats
a naive prompt on end-of-conversation detection (a documented improvement in
`app/modules/exit_tuning.py`).

## Project structure

```text
GenAI Multi-Agent Recruiting Chatbot/
|- app/
|  |- __init__.py
|  |- main.py                    # console entry point
|  |- modules/
|  |  |- config.py               # model names + paths (env-overridable)
|  |  |- data_exploration.py     # Phase 1 inputs report
|  |  |- embedding.py            # offline PDF -> Chroma
|  |  |- scheduling_tool.py      # SQLite build + find_interview_slots tool
|  |  |- main_agent.py           # routing + turn orchestration + memory
|  |  |- evaluation.py           # Accuracy / Confusion Matrix harness
|  |  |- exit_tuning.py          # naive vs few-shot Exit Advisor comparison
|  |  |- advisors/
|  |  |  |- common.py            # LLM factory + history formatter
|  |  |  |- info_advisor.py      # RAG over Chroma
|  |  |  |- scheduling_advisor.py
|  |  |  |- exit_advisor.py      # prompt-engineered End/Continue classifier
|  |- prompts/                   # version-controlled prompt text per agent
|- streamlit_app/
|  |- streamlit_main.py          # Streamlit PoC (registration + chat)
|- tests/
|  |- test_*.py                  # unit + integration tests
|  |- test_evals.ipynb           # Accuracy + Confusion Matrix
|- data/
|  |- inputs/                    # tracked copies of the PDF, SQL seed, conversations
|  |- tech.db                    # committed SQLite schedule DB (reproducible)
|  |- chroma/                    # vector store (git-ignored, rebuilt offline)
|- requirements.txt
|- .env.example
|- .claude/launch.json           # dev-server config
```

## Deployment - Streamlit Community Cloud

The app is Cloud-ready: it reads the API key from `st.secrets` when `.env` is
absent, and it rebuilds the Chroma store on first run (the scheduling DB
`data/tech.db` is committed).

Checklist:

1. Push the repo to GitHub (already at
   `IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot`).
2. On https://share.streamlit.io, create a new app from this repo.
3. Set **Main file path** to `streamlit_app/streamlit_main.py`.
4. Under **Advanced settings -> Secrets**, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
5. If Cloud offers a Python version, pick **3.12 or 3.13** (the pinned
   dependencies install there too). If a pinned version has no wheel for the
   Cloud Python, relax that single pin in `requirements.txt`.
6. Deploy. On first load the app builds the Chroma collection from the committed
   `data/inputs/job_description.pdf`, so the first response may take a few extra
   seconds.

## Notes - Next steps

- **No fine-tuning** is used anywhere; the Exit Advisor is prompt-engineered only.
- **Reproducibility**: `data/tech.db` is generated with a fixed seed and committed,
  so recruiter availability is identical across clones. Dependencies are pinned in
  `requirements.txt`.
- Secrets live in `.env` (local) or `st.secrets` (Cloud) and are never committed.
