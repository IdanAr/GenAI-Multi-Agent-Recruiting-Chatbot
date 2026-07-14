"""scheduling_tool.py - SQL availability lookup via function calling (Phase 3).

Two responsibilities:

1. Build the SQLite ``Schedule`` table from the same rules as the provided
   T-SQL seed (dates 2024-2026 excluding Monday + Saturday, hours 09:00-17:00,
   four positions), but with a FIXED random seed so availability is
   reproducible. The result is persisted to ``data/tech.db`` and committed.

2. Expose a LangChain tool, ``find_interview_slots``, that the Scheduling
   Advisor calls. It resolves a relative date expression ("next Friday") from
   the conversation date and returns the three nearest available slots for the
   Python Developer role.

Database access uses the course SQLAlchemy idiom (create_engine + pd.read_sql
+ text), pointed at SQLite instead of SQL Server.

Build the database:
    python -m app.modules.scheduling_tool
"""

from datetime import date, datetime, timedelta

from langchain_core.tools import tool

from app.modules import config

# Seed generation rules (mirror the provided T-SQL script).
POSITIONS = ["Python Dev", "Sql Dev", "Analyst", "ML"]
DEFAULT_POSITION = "Python Dev"
_EXCLUDED_WEEKDAYS = {0, 5}  # Python weekday(): Monday=0, Saturday=5.
_HOURS = [f"{hour:02d}:00:00" for hour in range(9, 18)]  # 09:00..17:00 -> 9 slots.

_WEEKDAY_NUM = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_SOONEST_TERMS = {
    "", "asap", "soonest", "any", "anytime", "as soon as possible",
    "no preference", "whenever",
}


# How long a connection waits for a lock to clear before giving up (ms). SQLite
# defaults to 0, which is why a brief overlap raises "database is locked".
_BUSY_TIMEOUT_MS = 30_000


def _make_engine(db_path):
    """Create a SQLite engine that tolerates brief write locks.

    The default SQLite busy timeout is 0, so a connection that finds the database
    momentarily locked (by the app's own read connection, or an external editor
    that hasn't committed yet) fails instantly with "database is locked". Setting
    a busy timeout makes it *wait* for the lock to clear instead - which is what
    turns a booking write from fragile into reliable.

    The timeout is applied two ways for safety: via sqlite3's ``timeout`` connect
    arg and via ``PRAGMA busy_timeout`` on every connection. Both are per-
    connection settings that need no lock themselves, so reads stay cheap.
    """
    from sqlalchemy import create_engine, event

    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"timeout": _BUSY_TIMEOUT_MS / 1000},  # seconds
    )

    @event.listens_for(engine, "connect")
    def _set_busy_timeout(dbapi_conn, _record):  # noqa: ANN001 - SQLAlchemy hook
        cursor = dbapi_conn.cursor()
        cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        cursor.close()

    return engine


# --------------------------------------------------------------------------- #
# 1. Database build
# --------------------------------------------------------------------------- #
def build_schedule_db(db_path=config.SQLITE_DB_PATH, seed: int = 42,
                      start: date = date(2024, 1, 1),
                      end: date = date(2026, 12, 31)) -> dict:
    """Build (or replace) the SQLite Schedule table deterministically.

    The ``available`` flag mirrors the T-SQL pseudo-normal draw (average of two
    uniforms thresholded at 0.5, giving roughly 50% availability), but seeded so
    the database is identical on every build.
    """
    import random

    import pandas as pd

    rng = random.Random(seed)
    rows = []
    day = start
    while day <= end:
        if day.weekday() not in _EXCLUDED_WEEKDAYS:
            for slot_time in _HOURS:
                for position in POSITIONS:
                    available = 1 if (rng.random() + rng.random()) / 2 >= 0.5 else 0
                    rows.append((day.isoformat(), slot_time, position, available))
        day += timedelta(days=1)

    frame = pd.DataFrame(rows, columns=["date", "time", "position", "available"])
    frame.insert(0, "ScheduleID", range(1, len(frame) + 1))

    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = _make_engine(db_path)
    frame.to_sql("Schedule", engine, if_exists="replace", index=False)
    engine.dispose()

    return {
        "db_path": str(db_path),
        "rows": len(frame),
        "available": int(frame["available"].sum()),
        "positions": POSITIONS,
        "seed": seed,
    }


# --------------------------------------------------------------------------- #
# 2. Date inference + slot retrieval
# --------------------------------------------------------------------------- #
def _next_weekday(reference: date, target_weekday: int) -> date:
    """Return the next date strictly after ``reference`` on ``target_weekday``."""
    days_ahead = (target_weekday - reference.weekday() + 7) % 7
    days_ahead = days_ahead or 7  # if today matches, jump to next week
    return reference + timedelta(days=days_ahead)


def resolve_date_expression(expression, reference_date: date) -> date:
    """Resolve a natural-language date expression relative to a reference date.

    Handles: empty / "asap" (-> reference date, i.e. soonest), "today",
    "tomorrow", "next week", weekday names ("next Friday" -> the next Friday),
    ISO dates ("2026-07-20"), and a best-effort fallback for other formats.
    Anything unparseable falls back to the reference date.
    """
    if expression is None:
        return reference_date
    expr = str(expression).strip().lower()

    if expr in _SOONEST_TERMS:
        return reference_date
    if expr == "today":
        return reference_date
    if expr == "tomorrow":
        return reference_date + timedelta(days=1)
    if "next week" in expr:
        return reference_date + timedelta(days=7)
    for name, weekday in _WEEKDAY_NUM.items():
        if name in expr:
            return _next_weekday(reference_date, weekday)

    try:
        return date.fromisoformat(expr)
    except ValueError:
        pass
    try:
        from dateutil import parser as date_parser

        default = datetime(reference_date.year, reference_date.month, reference_date.day)
        return date_parser.parse(expr, default=default).date()
    except Exception:
        return reference_date


def get_nearest_available_slots(target_date, position: str = DEFAULT_POSITION,
                                n: int = 3, db_path=config.SQLITE_DB_PATH) -> list[dict]:
    """Return the ``n`` nearest available slots on/after ``target_date``.

    Uses the course SQLAlchemy idiom (create_engine + pd.read_sql + text).
    """
    import pandas as pd
    from sqlalchemy import text

    if isinstance(target_date, date):
        target_date = target_date.isoformat()

    engine = _make_engine(db_path)
    query = text(
        'SELECT "date", "time", position '
        "FROM Schedule "
        "WHERE available = 1 AND position = :position AND \"date\" >= :target "
        'ORDER BY "date" ASC, "time" ASC '
        "LIMIT :n"
    )
    frame = pd.read_sql(query, engine,
                        params={"position": position, "target": target_date, "n": n})
    engine.dispose()
    return frame.to_dict("records")


def book_slot(slot, position: str = DEFAULT_POSITION,
              db_path=config.SQLITE_DB_PATH) -> bool:
    """Book a proposed slot: flip its ``available`` flag from 1 to 0.

    Once a candidate confirms an interview time, that slot must never be offered
    again. ``slot`` is a display string as produced by the scheduling tool /
    advisor, for example ``"2026-07-17 at 09:00:00"``.

    The UPDATE requires ``available = 1``, so a slot that was already taken
    (between proposal and confirmation) is not double-booked. Returns True if the
    slot was available and is now booked, False if it was already taken, not
    found, or the display string could not be parsed.
    """
    from sqlalchemy import text

    try:
        slot_date, slot_time = (part.strip() for part in str(slot).split(" at ", 1))
    except ValueError:
        return False  # not in "<date> at <time>" form

    engine = _make_engine(db_path)
    with engine.begin() as conn:  # begin() commits on success
        result = conn.execute(
            text('UPDATE Schedule SET available = 0 '
                 'WHERE "date" = :date AND "time" = :time '
                 "AND position = :position AND available = 1"),
            {"date": slot_date, "time": slot_time, "position": position},
        )
        booked = result.rowcount > 0
    engine.dispose()
    return booked


# --------------------------------------------------------------------------- #
# 3. LangChain tool (function calling)
# --------------------------------------------------------------------------- #
@tool
def find_interview_slots(date_expression: str, reference_date: str) -> str:
    """Find the three nearest available interview slots for the Python Developer role.

    Args:
        date_expression: The candidate's requested timing in natural language,
            for example "next Friday", "tomorrow", "2026-07-20", or "" for the
            soonest available.
        reference_date: The conversation date in ISO format (YYYY-MM-DD). Used to
            resolve relative expressions such as "next Friday".
    """
    try:
        reference = date.fromisoformat(reference_date)
    except (ValueError, TypeError):
        reference = date.today()  # fall back if the caller passed a bad date
    target = resolve_date_expression(date_expression, reference)
    slots = get_nearest_available_slots(target, position=DEFAULT_POSITION, n=3)
    if not slots:
        return (f"No available {DEFAULT_POSITION} interview slots on or after "
                f"{target.isoformat()}.")
    formatted = "; ".join(f"{slot['date']} at {slot['time']}" for slot in slots)
    return (f"Three nearest available {DEFAULT_POSITION} interview slots "
            f"(on or after {target.isoformat()}): {formatted}")


def _main() -> None:
    """Build the database and print a short summary."""
    print("Building SQLite Schedule database ...")
    summary = build_schedule_db()
    for key, value in summary.items():
        print(f"  {key:12}: {value}")
    pct = 100 * summary["available"] / summary["rows"]
    print(f"  availability: {pct:.1f}% of {summary['rows']:,} slots")


if __name__ == "__main__":
    _main()
