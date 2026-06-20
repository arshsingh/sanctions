import os
from datetime import date
from typing import TypedDict

import psycopg


class Sanction(TypedDict):
    source_id: str
    target_type: str
    names: list[str]
    positions: list[str]
    listed_on: date | str | None
    remarks: str | None


_INSERT_SANCTION_SQL = """
    INSERT INTO internal.sanctions
        (source, source_id, target_type, names, positions, listed_on, remarks)
    VALUES
        (%(source)s, %(source_id)s, %(target_type)s, %(names)s, %(positions)s, %(listed_on)s, %(remarks)s)
    ON CONFLICT (source, source_id) DO NOTHING
"""

_UPSERT_SOURCE_STATUS_SQL = """
    INSERT INTO internal.source_status (source, synced_at) VALUES (%s, now())
    ON CONFLICT (source) DO UPDATE SET synced_at = EXCLUDED.synced_at
"""


def create_sanctions(source: str, entries: list[Sanction]) -> None:
    """Insert sanctions for the given source into the DB."""
    if not entries:
        return

    rows = [{**e, "source": source} for e in entries]

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor() as c:
            c.executemany(_INSERT_SANCTION_SQL, rows)


def update_source_status(source: str) -> None:
    """Record a successful sync for the given source."""
    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        with conn.cursor() as c:
            c.execute(_UPSERT_SOURCE_STATUS_SQL, (source,))
