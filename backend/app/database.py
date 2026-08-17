import os

import psycopg


def is_database_healthy() -> bool:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False

    try:
        with psycopg.connect(database_url, connect_timeout=3) as connection:
            result = connection.execute("SELECT 1").fetchone()
    except psycopg.Error:
        return False

    return result == (1,)
