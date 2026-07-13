"""info_advisor.py - Conversation Info Advisor (Phase 4).

Answers candidate questions about the Python Developer role using RAG over the
Chroma job-description collection, and steers the conversation toward scheduling.

Built with the course LangChain agent pattern (create_tool_calling_agent +
AgentExecutor). The advisor's binary decision from the workflow diagram -
"Info needed" vs "Info not needed" - is captured by whether the agent chose to
call the retrieval tool on this turn.

    result = run_info_advisor(history)
    # -> {"info_needed": bool, "answer": str, "retrieved": [...]}
"""

# In langchain 1.x the classic AgentExecutor / create_tool_calling_agent API
# lives in langchain_classic (langchain.agents is unavailable on Python 3.14
# here due to a langgraph mismatch).
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from app.modules.advisors.common import get_chat_llm, format_conversation
from app.prompts.info_advisor import INFO_ADVISOR_SYSTEM

# Low temperature: answers should stay faithful to the retrieved job text, with
# just enough fluency for a natural SMS tone.
_TEMPERATURE = 0.2


@tool
def retrieve_job_information(query: str) -> str:
    """Retrieve relevant text from the Python Developer job description.

    Use this to answer any candidate question about the role: responsibilities,
    required skills, tech stack, tools, benefits, location, growth, and so on.
    """
    from app.modules import embedding

    results = embedding.retrieve(query, n_results=3)
    documents = results.get("documents", [[]])[0]
    if not documents:
        return "No relevant job information found."
    return "\n\n".join(documents)


def build_info_advisor(llm=None) -> AgentExecutor:
    """Build the Info Advisor agent executor."""
    llm = llm or get_chat_llm(temperature=_TEMPERATURE)
    prompt = ChatPromptTemplate.from_messages([
        ("system", INFO_ADVISOR_SYSTEM),
        ("user", "Conversation so far:\n{input}\n\nWrite the recruiter's next reply."),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, [retrieve_job_information], prompt)
    return AgentExecutor(
        agent=agent,
        tools=[retrieve_job_information],
        return_intermediate_steps=True,
        verbose=False,
    )


def run_info_advisor(history, llm=None) -> dict:
    """Run the Info Advisor on a conversation and return its decision + reply.

    Args:
        history: a conversation as a list of {'speaker', 'text'} turns, or a
            pre-formatted string.

    Returns:
        {"info_needed": bool, "answer": str, "retrieved": list[str]}
        info_needed is True when the advisor chose to retrieve from Chroma.
    """
    conversation = format_conversation(history)
    executor = build_info_advisor(llm)
    result = executor.invoke({"input": conversation})

    steps = result.get("intermediate_steps", [])
    retrieved = [observation for (_action, observation) in steps]
    return {
        "info_needed": len(steps) > 0,
        "answer": result["output"],
        "retrieved": retrieved,
    }
