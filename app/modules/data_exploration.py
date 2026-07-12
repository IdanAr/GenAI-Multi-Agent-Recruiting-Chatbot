"""data_exploration.py - Phase 1 inputs ingestion and sanity-check.

Loads and summarizes the three project inputs so we can confirm each one
parses correctly before building on it:

1. The scheduling SQL seed script (schema + generation rules + expected rows).
2. The Python Developer job-description PDF (pages, characters, a text sample).
3. The labeled SMS conversations (counts, per-turn schema, label distribution).

Run it as a report:
    python -m app.modules.data_exploration

Heavy third-party imports (PyPDF2) are done lazily inside the functions, so
importing this module never fails even without those packages installed.
"""

import json
import re
from collections import Counter
from datetime import date, timedelta

from app.modules import config


# Weekdays excluded by the SQL seed (DATENAME(WEEKDAY,d) NOT IN (...)).
_EXCLUDED_WEEKDAYS = {"Saturday", "Monday"}
# Python's date.weekday(): Monday=0 ... Sunday=6.
_WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


def summarize_schedule_sql(path=config.SCHEDULE_SQL_PATH) -> dict:
    """Parse the T-SQL seed script and summarize schema + generation rules.

    The .sql file is a generator (it computes rows at run time in SQL Server),
    so instead of reading literal rows we extract the schema, the seed
    parameters, and compute how many rows the script is expected to produce.
    """
    sql = path.read_text(encoding="utf-8", errors="replace")

    # Columns from the CREATE TABLE dbo.Schedule ( ... ) block only.
    # Column names may be bracketed (e.g. [date], [time]).
    columns = []
    table_block = re.search(r"CREATE TABLE\s+dbo\.Schedule\s*\((.*?)\)\s*;",
                            sql, flags=re.DOTALL | re.IGNORECASE)
    if table_block:
        columns = re.findall(
            r"^\s*\[?(\w+)\]?\s+(INT|DATE|TIME\(\d\)|VARCHAR\(\d+\)|BIT)",
            table_block.group(1), flags=re.MULTILINE | re.IGNORECASE)

    # Seed parameters.
    start = re.search(r"@StartDate\s+DATE\s*=\s*'(\d{8})'", sql)
    end = re.search(r"@EndDate\s+DATE\s*=\s*'(\d{8})'", sql)

    # Positions: isolate the Positions CTE block, then grab its quoted literals.
    positions = []
    cte = re.search(r"Positions\s+AS\s*\((.*?)\)", sql, flags=re.DOTALL | re.IGNORECASE)
    if cte:
        positions = re.findall(r"'([^']+)'", cte.group(1))

    start_date = _yyyymmdd(start.group(1)) if start else None
    end_date = _yyyymmdd(end.group(1)) if end else None

    # Count valid dates (exclude Saturday and Monday) in the range.
    valid_days = 0
    if start_date and end_date:
        d = start_date
        while d <= end_date:
            if _WEEKDAY_NAMES[d.weekday()] not in _EXCLUDED_WEEKDAYS:
                valid_days += 1
            d += timedelta(days=1)

    # Hours 09:00..17:00 inclusive, hourly.
    hours_per_day = 9
    n_positions = len(positions)
    expected_rows = valid_days * hours_per_day * n_positions

    return {
        "path": str(path),
        "table": "dbo.Schedule",
        "columns": columns,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "excluded_weekdays": sorted(_EXCLUDED_WEEKDAYS),
        "hours": "09:00-17:00 hourly (9 slots/day)",
        "positions": positions,
        "valid_days": valid_days,
        "expected_rows": expected_rows,
    }


def summarize_job_description(path=config.JOB_DESCRIPTION_PDF) -> dict:
    """Load the job-description PDF with PyPDF2 and summarize it."""
    from PyPDF2 import PdfReader  # lazy import (course RAG tool)

    reader = PdfReader(str(path))
    pages_text = [(p.extract_text() or "") for p in reader.pages]
    full_text = "\n".join(pages_text)
    return {
        "path": str(path),
        "num_pages": len(reader.pages),
        "total_chars": len(full_text),
        "chars_per_page": [len(t) for t in pages_text],
        "sample": full_text[:400].strip(),
    }


def summarize_conversations(path=config.CONVERSATIONS_JSON) -> dict:
    """Load the labeled conversations JSON and summarize structure + labels."""
    data = json.loads(path.read_text(encoding="utf-8"))

    total_turns = 0
    labeled_turns = 0
    labels = Counter()
    speakers = Counter()
    for conv in data:
        for turn in conv["turns"]:
            total_turns += 1
            speakers[turn.get("speaker")] += 1
            label = turn.get("label")
            if label is not None:
                labeled_turns += 1
                labels[label] += 1

    return {
        "path": str(path),
        "num_conversations": len(data),
        "total_turns": total_turns,
        "labeled_turns": labeled_turns,
        "label_distribution": dict(labels),
        "speaker_distribution": dict(speakers),
        "conversation_keys": list(data[0].keys()) if data else [],
        "turn_keys": list(data[0]["turns"][0].keys()) if data else [],
        "sample_conversation_id": data[0].get("conversation_id") if data else None,
        "sample_turn": data[0]["turns"][0] if data else None,
    }


def _yyyymmdd(s: str) -> date:
    """Convert a 'YYYYMMDD' string to a date."""
    return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))


def _print_report() -> None:
    """Print the consolidated Phase 1 report to stdout."""
    line = "=" * 70

    print(line)
    print("1. SCHEDULING SQL SEED")
    print(line)
    sql = summarize_schedule_sql()
    print(f"file            : {sql['path']}")
    print(f"table           : {sql['table']}")
    print("columns         :")
    for name, typ in sql["columns"]:
        print(f"                  - {name} ({typ})")
    print(f"date range      : {sql['start_date']} .. {sql['end_date']}")
    print(f"excluded days   : {', '.join(sql['excluded_weekdays'])}")
    print(f"hours           : {sql['hours']}")
    print(f"positions       : {', '.join(sql['positions'])}")
    print(f"valid days      : {sql['valid_days']}")
    print(f"expected rows   : {sql['expected_rows']:,} "
          f"(= {sql['valid_days']} days x 9 hours x {len(sql['positions'])} positions)")
    print()

    print(line)
    print("2. JOB DESCRIPTION PDF")
    print(line)
    pdf = summarize_job_description()
    print(f"file            : {pdf['path']}")
    print(f"pages           : {pdf['num_pages']}")
    print(f"total chars     : {pdf['total_chars']:,}")
    print(f"chars per page  : {pdf['chars_per_page']}")
    print("sample (first 400 chars):")
    print(pdf["sample"])
    print()

    print(line)
    print("3. LABELED SMS CONVERSATIONS")
    print(line)
    conv = summarize_conversations()
    print(f"file            : {conv['path']}")
    print(f"conversations   : {conv['num_conversations']}")
    print(f"total turns     : {conv['total_turns']}")
    print(f"labeled turns   : {conv['labeled_turns']}")
    print(f"label dist      : {conv['label_distribution']}")
    print(f"speaker dist    : {conv['speaker_distribution']}")
    print(f"conversation keys: {conv['conversation_keys']}")
    print(f"turn keys       : {conv['turn_keys']}")
    print(f"sample turn     : {conv['sample_turn']}")
    print()
    print("Phase 1 report complete.")


if __name__ == "__main__":
    _print_report()
