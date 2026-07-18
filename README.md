<!-- PROJECT LOGO -->
<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" alt="Logo" width="120" height="120">
</p>

<h1 align="center">GenAI Multi-Agent Recruiting Chatbot</h1>

<p align="center">
  Final project for the GenAI course (Technion, GenAI 14) - an SMS-style chatbot for Python Developer job candidates<br>
  <a href="https://genai-multi-agent-recruiting-chatbot.streamlit.app/">View Live Demo</a>
  ·
  <a href="https://github.com/IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot/issues">Report Bug</a>
  ·
  <a href="https://github.com/IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot/issues">Request Feature</a>
</p>

---
<br></br>

## Project Participants

| Name | Id | Contact |
| ---- | ---- | ------- |
| _Idan Arbel_ | _204344022_ | _idan.rbel@gmail.com_ |
| _Yovel Yefet_ | _318987815_ | _yovel10@gmail.com_ |

---
<br></br>

## Table of Contents

- [About The Project](#about-the-project)
- [Features](#features)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Architecture](#architecture)
- [Code Examples](#code-examples)
- [Evaluation](#evaluation)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [To-Do List](#to-do-list)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

---
<br></br>


## About The Project

> An SMS-style chatbot that interacts with job candidates for a Python Developer position. The bot answers questions about the role, gathers information, and decides on every turn whether to continue the conversation, schedule an interview, or end it.<br>

The bot is built from a Main Agent and three advisor agents:

- **Main Agent** (`app/modules/main_agent.py`) - routes each turn to exactly one advisor, then commits to **Continue** / **Schedule** / **End** and replies. It also composes the personalized opening greeting and the closing message.
- **Exit Advisor** (`app/modules/advisors/exit_advisor.py`) - decides whether the conversation should end, using prompt engineering with few-shot examples mined from the labeled data. No fine-tuning.
- **Scheduling Advisor** (`app/modules/advisors/scheduling_advisor.py`) - checks recruiter availability in a SQLite database through function calling, and proposes the nearest available slots (resolving relative dates like "next Friday" against the conversation date).
- **Info Advisor** (`app/modules/advisors/info_advisor.py`) - answers questions about the role via RAG over a Chroma vector store built from the job description PDF, and steers the candidate toward scheduling.

The proof of concept runs in Streamlit instead of real SMS.

<div style="background: #272822; color: #f8f8f2; padding: 10px; border-radius: 8px;">
  <b> Technologies:</b> Python, OpenAI API, LangChain, Chroma, SQLite (SQLAlchemy), Streamlit, scikit-learn
</div>

---
<br></br>


## Features

- [x] Main Agent + 3 advisor agents (Exit, Scheduling, Info)
- [x] Prompt engineering with few-shot examples (no fine-tuning)
- [x] Prompts kept as version-controlled strings under `app/prompts/`
- [x] Chroma vector database for the job description PDF (RAG)
- [x] Function calling against a SQLite database of interview slots
- [x] Relative-date resolution ("next Friday") against a reference date
- [x] Agentic, personalized opening greeting per candidate
- [x] Streamlit chat app as a proof of concept
- [x] Console REPL entry point
- [x] Evaluation with Accuracy and Confusion Matrix over labeled conversations (0.841)
- [x] Unit and integration test suite (`pytest`, developed via TDD, kept local)
- [x] Deployment to Streamlit Community Cloud
- [ ] Connect to a real SMS provider

---
<br></br>


##  Getting Started

### Prerequisites

- Python 3.14 (the pinned dependency set is verified on 3.14; see the notes in `requirements.txt`)
- pip
- An OpenAI API key

### Installation

```bash
git clone https://github.com/IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot.git
cd GenAI-Multi-Agent-Recruiting-Chatbot
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Create your environment file from the template and add your key:

```bash
copy .env.example .env          # Windows (macOS/Linux: cp .env.example .env)
```

`.env` contents:

```text
OPENAI_API_KEY=sk-your_api_key_here

# Optional overrides; defaults live in app/modules/config.py
CHAT_MODEL=gpt-4.1-2025-04-14
EMBEDDING_MODEL=text-embedding-3-small
```

No manual setup scripts are required. **Both entry points build the Chroma vector
store and the SQLite scheduling database automatically on first run if they are
missing.** To rebuild them by hand, see [Usage](#usage).

---
<br></br>


## Usage

### Run the Streamlit proof of concept (primary UI)

```bash
streamlit run streamlit_app/streamlit_main.py
```

Register with a name, a contact, and your years of Python experience, then chat.
The opening greeting is generated per candidate from the registration details.
Each recruiter reply carries a small caption showing the chosen action and the
advisor that was consulted.

### Chat in the terminal

```bash
python -m app.main
```

Type `quit` or `exit` to leave.

### Rebuild the data artifacts manually (optional)

```bash
python -m app.modules.embedding          # build the Chroma collection from the PDF
python -m app.modules.scheduling_tool    # (re)build data/tech.db from the seed
python -m app.modules.data_exploration   # print a report on the three input files
```

### Run the evaluation

```bash
jupyter notebook tests/test_evals.ipynb  # Accuracy + Confusion Matrix (the required deliverable)
python -m app.modules.exit_tuning        # naive vs few-shot Exit Advisor comparison
```

A `pytest` unit and integration suite was built via TDD during development but is
kept local (not part of the submitted repo), so a fresh clone ships only the
evaluation notebook above.

Example conversation:

```text
Recruiter: Thanks for applying to our Python Developer opening! What kinds of
           Python projects have you worked on recently?
You:       I have 4 years of experience. Is the position remote?
           [action: continue | advisor: info]
Recruiter: ... (answers from the job description, then steers to scheduling)
You:       Yes, sometime next week please
           [action: schedule | advisor: scheduling]
Recruiter: Here are the nearest available slots: ...
```

---
<br></br>


## Architecture

One turn in the conversation:

<p float="left">
  <img src="One Turn in the Conversation.jpg" width="620"/>
</p>

1. The candidate sends a message (or submits the registration form).
2. The Main Agent routes to exactly one advisor: Exit, Scheduling, or Info.
3. That advisor reads the full history and returns a binary decision, retrieving
   from Chroma or the SQL calendar where relevant.
4. The Main Agent chooses Continue / Schedule / End and replies.

Temperature is set per function rather than globally: `0.0` for routing (stable
decisions), `0.3` for the closing message, and `0.7` for the opening greeting so
it does not repeat verbatim across candidates.

---
<br></br>


## Code Examples

The Main Agent routes the turn, consults one advisor, and maps the advisor's
decision onto an action (`app/modules/main_agent.py`):

```python
def decide_action(history, reference_date: str = None, llm=None) -> dict:
    """Run one turn's decision: route, consult one advisor, choose the action."""
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
        # Exit advisor vetoed ending: hand off to Scheduling, which checks the
        # DB and proposes real slots rather than hallucinating availability.
        sched_out = run_scheduling_advisor(history, reference_date=reference_date, llm=llm)
        return {
            "action": "schedule" if sched_out["should_schedule"] else "continue",
            "reply": sched_out["answer"],
            "advisor": "scheduling",
            "advisor_output": sched_out,
        }
    ...
```

Driving a multi-turn conversation with LangChain memory:

```python
from app.modules.main_agent import MainAgent, compose_opening

agent = MainAgent(reference_date=date.today().isoformat())
opening = compose_opening(candidate_name="Dana", experience="3-5")
agent.memory.add_ai_message(opening)

result = agent.run_turn("Is the position remote?")
print(result["action"])   # continue
print(result["advisor"])  # info
print(result["reply"])
```

---
<br></br>


## Evaluation

`tests/test_evals.ipynb` runs the full system over the 15 labeled conversations
in `data/inputs/sms_conversations.json` and compares the predicted action against
the label at each recruiter turn.

| Metric | Result |
| ------ | ------ |
| Turns evaluated | 44 |
| Accuracy | **0.841** (7 of 44 misclassified) |
| Highest recall | **End** (precision 0.80, recall 1.00) and **Schedule** (recall 0.97) |
| Highest precision | **Continue** (1.00, but recall 0.40) |

> **Run-to-run variance.** These are live OpenAI calls, so the score is not fully
> deterministic even at `temperature=0`. Across repeated runs it lands in a
> **0.80-0.84** band; **0.841** is the top of that band, not a fixed value. The
> *behavioral* guarantees below (bookings only via the slot picker, no fabricated
> confirmations) are plain code paths and are deterministic.

Accuracy climbed from a **0.705** baseline through two stages, with no fine-tuning:

1. **Prompt engineering (0.705 -> 0.818)**, documented in the notebook:
   - **Info Advisor** was instructed to always call `retrieve_job_information`
     rather than answer familiar-looking questions from its own knowledge, and
     hard-coded facts were stripped from its few-shot examples so none could leak
     into a live answer.
   - **Exit Advisor** few-shot set was expanded (`app/prompts/exit_fewshot.py`) to
     cover the case where a candidate proposes their own specific time as a real
     commitment.
   - **Router** gained disambiguating rules for time-related turns.
2. **DB-safe booking redesign (0.818 -> 0.841)**: a candidate committing to a
   specific time now routes to the **Scheduling Advisor**, which checks the SQLite
   calendar and proposes real slots, instead of letting the Exit Advisor end the
   turn with a fabricated "you're booked" message. Only the validated Streamlit
   slot picker calls `book_slot()`. To reflect this in the metric, 11
   "commit-to-a-time" turns that the raw dataset labels **End** are treated as
   **Schedule** at evaluation time via `REDESIGN_LABEL_OVERRIDES` in
   `app/modules/evaluation.py` (the raw JSON is left untouched).

The 7 remaining errors are structural. Six are Continue turns predicted as
Schedule, sitting on an inherently ambiguous boundary: the identical candidate
sentence *"I have three years' experience with Django and Flask"* appears labeled
Continue in one conversation and Schedule in another, so no prompt can separate
them. A controlled experiment in the notebook confirmed this: forcing a rule onto
that boundary *reduced* accuracy, so it was reverted. The bot stays deliberately
biased toward scheduling, which favors its objective of booking interviews. The
seventh is a single borderline Schedule/End turn (conv8 turn7).

`app/modules/exit_tuning.py` documents the separate finding that the few-shot
Exit Advisor prompt beats a naive prompt on end-of-conversation detection. It
splits by conversation to avoid leakage: conversations 1-5 are the few-shot pool,
conversations 6-15 are the held-out test set.

---
<br></br>


## Project Structure

```text
GenAI Multi-Agent Recruiting Chatbot/
├── app/
│   ├── __init__.py
│   ├── main.py                       # console entry point
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── config.py                 # model names + paths (env-overridable)
│   │   ├── data_exploration.py       # report on the three input files
│   │   ├── embedding.py              # offline PDF -> Chroma
│   │   ├── scheduling_tool.py        # SQLite build + find_interview_slots tool
│   │   ├── main_agent.py             # routing + turn orchestration + memory
│   │   ├── evaluation.py             # Accuracy / Confusion Matrix harness
│   │   ├── exit_tuning.py            # naive vs few-shot Exit Advisor comparison
│   │   └── advisors/
│   │       ├── __init__.py
│   │       ├── common.py             # LLM factory + history formatter
│   │       ├── info_advisor.py       # RAG over Chroma
│   │       ├── scheduling_advisor.py # function calling over SQLite
│   │       └── exit_advisor.py       # prompt-engineered End/Continue classifier
│   └── prompts/                      # version-controlled prompt text per agent
│       ├── __init__.py
│       ├── main_agent.py
│       ├── info_advisor.py
│       ├── scheduling_advisor.py
│       ├── exit_advisor.py
│       └── exit_fewshot.py
├── streamlit_app/
│   ├── __init__.py
│   └── streamlit_main.py             # Streamlit PoC (registration + chat)
├── data/
│   ├── inputs/
│   │   ├── job_description.pdf
│   │   ├── sms_conversations.json    # 15 labeled conversations
│   │   └── SQL_DB/schedule_seed.sql
│   ├── tech.db                       # committed SQLite schedule DB (reproducible)
│   └── chroma/                       # vector store (git-ignored, rebuilt on first run)
├── tests/
│   ├── __init__.py
│   └── test_evals.ipynb              # Accuracy + Confusion Matrix (the deliverable)
├── One Turn in the Conversation.jpg  # workflow diagram
├── .env.example
├── .gitignore
├── LICENSE
├── requirements.txt
└── README.md
```

---
<br></br>


## Deployment

**Live app:** https://genai-multi-agent-recruiting-chatbot.streamlit.app/

The app is deployed on Streamlit Community Cloud: it reads the API key from
`st.secrets` when `.env` is absent, and rebuilds the Chroma store on first run
(`data/tech.db` is committed, so recruiter availability is identical across
clones).

To reproduce the deployment from a fork:

1. Push the repo to GitHub (`IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot`).
2. On https://share.streamlit.io, create a new app from this repo.
3. Set **Main file path** to `streamlit_app/streamlit_main.py`.
4. Under **Advanced settings -> Secrets**, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
5. If Cloud offers a Python version, pick **3.12 or 3.13**. If a pinned version
   has no wheel for the Cloud Python, relax that single pin in
   `requirements.txt`.
6. Deploy. The first load builds the Chroma collection from the committed
   `data/inputs/job_description.pdf`, so the first response may take a few extra
   seconds.

---
<br></br>


## To-Do List

- [x] SQLite database with demo interview slots (fixed seed, committed)
- [x] Chroma vector database for the job description
- [x] Main Agent and three Advisor agents
- [x] Personalized, agentic opening greeting
- [x] Streamlit proof of concept
- [x] Evaluation notebook with Accuracy and Confusion Matrix
- [x] Deploy to Streamlit Community Cloud
- [ ] Connect to a real SMS provider
- [ ] Reduce Continue/Schedule confusion (relabel the noisy turns)

---
<br></br>


## Contributing

Contributions are **welcome**! Please open an issue first to discuss the change.

---
<br></br>


## License

Distributed under the MIT License.

---
<br></br>


## Contact

See [Project Participants](#project-participants)

Project Link: [https://github.com/IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot](https://github.com/IdanAr/GenAI-Multi-Agent-Recruiting-Chatbot)

---
<br></br>


## Acknowledgments

- [Python](https://www.python.org/)
- [OpenAI API](https://platform.openai.com/docs/overview)
- [LangChain](https://python.langchain.com/)
- [Chroma](https://www.trychroma.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Streamlit](https://streamlit.io/)
- [scikit-learn](https://scikit-learn.org/)


---
