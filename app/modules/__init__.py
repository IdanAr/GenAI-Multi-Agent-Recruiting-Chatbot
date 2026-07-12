"""app.modules - application modules.

Holds the building blocks consulted by the Main Agent:
- config: centralized settings (model names, paths) read from the environment.
- embedding: offline PDF -> Chroma embedding step (Phase 2).
- scheduling_tool: SQL availability lookup via function calling (Phase 3).
- advisors: the Info, Scheduling, and Exit advisor agents (Phase 4-5).
- main_agent: the turn orchestration (Phase 6).
"""
