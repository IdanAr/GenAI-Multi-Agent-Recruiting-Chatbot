"""streamlit_main.py - Streamlit proof of concept (Phase 8).

A simple SMS-style chat UI plus a candidate registration form, wired to the
Main Agent. Each candidate message runs one full turn (route to an advisor,
decide Continue / Schedule / End) and the recruiter's reply is shown.

Run locally from the project root:
    streamlit run streamlit_app/streamlit_main.py
"""

import os
import sys
from datetime import date

# Make the project root importable when Streamlit runs this file directly.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st
from dotenv import load_dotenv

from app.modules import config, embedding
from app.modules.main_agent import MainAgent

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# On Streamlit Community Cloud there is no .env; the API key is provided through
# st.secrets. Bridge it into the environment so os.getenv keeps working. (This
# does not override an existing .env value locally.)
try:
    if "OPENAI_API_KEY" in st.secrets and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass  # no secrets configured (e.g. local run without a secrets file)


@st.cache_resource(show_spinner="Preparing the knowledge base...")
def _prepare_backend():
    """Build the Chroma collection and SQLite DB once if they are missing.

    Cached so it runs a single time per server (important on a fresh Cloud
    deploy where data/chroma/ is git-ignored and must be rebuilt).
    """
    embedding.ensure_collection()
    if not config.SQLITE_DB_PATH.exists():
        from app.modules.scheduling_tool import build_schedule_db
        build_schedule_db()
    return True

st.set_page_config(page_title="Python Developer Recruiting Chatbot", page_icon="🐍")

# Opening message the recruiter bot sends once the candidate registers.
_OPENER = ("Thanks for applying to our Python Developer opening! "
           "What kinds of Python projects have you worked on recently?")


def _reset() -> None:
    """Clear all conversation state (used by the sidebar reset button)."""
    for key in ("registered", "agent", "messages", "ended", "candidate_name"):
        st.session_state.pop(key, None)


def _register_view() -> None:
    """Show the candidate registration form (the diagram's registration step)."""
    st.title("🐍 Python Developer - Recruiting Chatbot")
    st.write("Please register to start chatting with our recruiter assistant.")

    with st.form("registration"):
        name = st.text_input("Full name")
        contact = st.text_input("Email or phone")
        experience = st.selectbox(
            "Years of Python experience",
            ["Less than 1", "1-2", "3-5", "5+"],
        )
        submitted = st.form_submit_button("Start conversation")

    if submitted:
        if not name.strip() or not contact.strip():
            st.error("Please enter your name and a contact so we can reach you.")
            return
        # Initialize the Main Agent and seed the recruiter's opening message.
        st.session_state.registered = True
        st.session_state.candidate_name = name.strip()
        st.session_state.agent = MainAgent(reference_date=date.today().isoformat())
        st.session_state.agent.memory.add_ai_message(_OPENER)
        st.session_state.messages = [{"role": "assistant", "content": _OPENER,
                                      "caption": None}]
        st.session_state.ended = False
        st.rerun()


def _chat_view() -> None:
    """Show the chat UI and drive one Main Agent turn per candidate message."""
    st.title("🐍 Python Developer - Recruiting Chatbot")
    st.caption(f"Chatting with {st.session_state.candidate_name}")

    # Render the conversation so far.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("caption"):
                st.caption(message["caption"])

    if st.session_state.ended:
        st.info("This conversation has ended. Use 'Reset conversation' to start over.")
        return

    prompt = st.chat_input("Type your message...")
    if not prompt:
        return

    # Show the candidate message immediately.
    st.session_state.messages.append({"role": "user", "content": prompt, "caption": None})
    with st.chat_message("user"):
        st.write(prompt)

    # Run one full Main Agent turn.
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = st.session_state.agent.run_turn(prompt)
            except Exception as exc:  # keep the UI alive on any backend error
                st.error(f"Something went wrong: {exc}")
                return
        reply = result["reply"]
        caption = f"action: {result['action']}  |  advisor: {result['advisor']}"
        st.write(reply)
        st.caption(caption)

    st.session_state.messages.append({"role": "assistant", "content": reply,
                                      "caption": caption})
    if result["action"] == "end":
        st.session_state.ended = True
        st.rerun()


def main() -> None:
    with st.sidebar:
        st.header("About")
        st.write("SMS-style recruiting chatbot for a **Python Developer** role. "
                 "It answers questions, schedules interviews, or politely ends "
                 "the conversation.")
        st.button("Reset conversation", on_click=_reset)

    if not os.getenv("OPENAI_API_KEY"):
        st.warning("OPENAI_API_KEY is not set. Add it to .env (local) or to the "
                   "app secrets (Streamlit Cloud) to enable the bot.")
        return

    # Build the vector store / scheduling DB once if they are missing.
    _prepare_backend()

    if not st.session_state.get("registered"):
        _register_view()
    else:
        _chat_view()


if __name__ == "__main__":
    main()
else:
    # Streamlit imports the module (no __main__), so run the app here too.
    main()
