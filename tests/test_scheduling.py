"""test_scheduling.py - unit tests for the Phase 3 scheduling tool.

Covers date inference and slot retrieval (the deterministic, offline parts).
A small database is built into a temp path per test so the tests are fast and
independent of the committed data/tech.db.
"""

from datetime import date

import pytest

from app.modules import scheduling_tool as st


@pytest.fixture(scope="module")
def small_db(tmp_path_factory):
    """Build a small, reproducible Schedule DB for the April 2024 range."""
    db_path = tmp_path_factory.mktemp("db") / "test_tech.db"
    st.build_schedule_db(db_path=db_path, seed=42,
                         start=date(2024, 4, 1), end=date(2024, 4, 30))
    return db_path


# --- date inference ------------------------------------------------------- #
def test_resolve_next_friday_from_wednesday():
    # 2024-04-03 is a Wednesday; "next Friday" -> 2024-04-05.
    assert st.resolve_date_expression("next Friday", date(2024, 4, 3)) == date(2024, 4, 5)


def test_resolve_weekday_when_today_is_that_weekday_jumps_a_week():
    # On Friday, "friday" should mean the next one, not today.
    friday = date(2024, 4, 5)
    assert st.resolve_date_expression("friday", friday) == date(2024, 4, 12)


def test_resolve_tomorrow_today_next_week():
    ref = date(2024, 4, 3)
    assert st.resolve_date_expression("tomorrow", ref) == date(2024, 4, 4)
    assert st.resolve_date_expression("today", ref) == ref
    assert st.resolve_date_expression("next week", ref) == date(2024, 4, 10)


def test_resolve_iso_date():
    assert st.resolve_date_expression("2026-07-20", date(2024, 4, 3)) == date(2026, 7, 20)


def test_resolve_soonest_terms_fall_back_to_reference():
    ref = date(2024, 4, 3)
    for expr in ["", "asap", "no preference", None]:
        assert st.resolve_date_expression(expr, ref) == ref


def test_resolve_unparseable_falls_back_to_reference():
    ref = date(2024, 4, 3)
    assert st.resolve_date_expression("sometime maybe", ref) == ref


# --- slot retrieval ------------------------------------------------------- #
def test_slots_are_available_python_dev_sorted(small_db):
    slots = st.get_nearest_available_slots(date(2024, 4, 5), db_path=small_db)
    assert 1 <= len(slots) <= 3
    for slot in slots:
        assert slot["position"] == "Python Dev"
        assert slot["date"] >= "2024-04-05"
    # sorted by (date, time)
    keys = [(s["date"], s["time"]) for s in slots]
    assert keys == sorted(keys)


def test_slots_skip_excluded_weekdays(small_db):
    # Target a Monday (2024-04-08); no rows exist on Mondays/Saturdays, so the
    # nearest available slots must land on allowed weekdays only.
    slots = st.get_nearest_available_slots(date(2024, 4, 8), db_path=small_db)
    assert slots
    for slot in slots:
        weekday = date.fromisoformat(slot["date"]).weekday()
        assert weekday not in st._EXCLUDED_WEEKDAYS


def test_build_is_reproducible(tmp_path):
    """Same seed + range -> identical query results across two builds."""
    a = tmp_path / "a.db"
    b = tmp_path / "b.db"
    st.build_schedule_db(db_path=a, seed=42, start=date(2024, 4, 1), end=date(2024, 4, 30))
    st.build_schedule_db(db_path=b, seed=42, start=date(2024, 4, 1), end=date(2024, 4, 30))
    slots_a = st.get_nearest_available_slots(date(2024, 4, 5), db_path=a)
    slots_b = st.get_nearest_available_slots(date(2024, 4, 5), db_path=b)
    assert slots_a == slots_b


def test_full_db_row_count(tmp_path):
    """The full 2024-2026 build produces the Phase 1 expected row count."""
    db_path = tmp_path / "full.db"
    summary = st.build_schedule_db(db_path=db_path, seed=42)
    assert summary["rows"] == 28188  # 783 valid days x 9 hours x 4 positions


# --- the LangChain tool --------------------------------------------------- #
def test_tool_invoke_returns_slots_string():
    result = st.find_interview_slots.invoke(
        {"date_expression": "next Friday", "reference_date": "2024-04-03"})
    assert "Python Dev" in result
    assert "2024-04-05" in result
