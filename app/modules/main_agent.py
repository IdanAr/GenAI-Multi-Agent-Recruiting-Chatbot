"""main_agent.py - Main Agent turn orchestration.

Implements one conversation turn per the workflow diagram: receive the
candidate input, route to exactly one advisor (Exit / Scheduling / Info),
consume the advisor's output, and decide one of Continue / Schedule /
End before replying to the candidate. Uses LangChain memory for history.

Phase 0: stub only. Implemented in Phase 6.
"""

# TODO (Phase 6): implement routing, advisor consultation, and the final
# Continue / Schedule / End decision with LangChain memory.
