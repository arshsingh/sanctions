import os

import psycopg2
from pypika import Table, PostgreSQLQuery as Query


sanctions = Table('sanctions', schema='internal')


def create_sanctions(entries):
    """
    Insert sanctions data into the DB
    """
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    if not entries:
        return

    with conn.cursor() as c:
        cols = entries[0].keys()
        c.execute(str(
            Query.into(sanctions)
                .columns(*cols)
                .insert(*[tuple(e[c] for c in cols) for e in entries])
                .on_conflict(sanctions.source, sanctions.source_id)
                .do_nothing()
        ))
        conn.commit()

    conn.close()