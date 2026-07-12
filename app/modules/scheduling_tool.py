"""scheduling_tool.py - SQL availability lookup via function calling.

A LangChain tool that queries the SQLite scheduling database for
recruiter availability, resolves relative dates (for example
"next Friday") from the conversation timestamp, and returns the three
nearest available slots for the Python Dev position.

Phase 0: stub only. Implemented in Phase 3.
"""

# TODO (Phase 3): build the SQLite DB from db_Tech, add date inference and
# the 3-nearest-slots query, and expose it as a LangChain @tool.
