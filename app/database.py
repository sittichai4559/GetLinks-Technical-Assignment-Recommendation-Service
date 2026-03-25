import os
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import ThreadedConnectionPool


_pool: ThreadedConnectionPool | None = None


def _get_pool() -> ThreadedConnectionPool:
    """
    Lazily create a thread-safe connection pool.

    We keep this intentionally lightweight (psycopg2-only) to avoid introducing new
    dependencies while still removing per-request connection overhead.
    """

    global _pool
    if _pool is not None:
        return _pool

    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    database = os.getenv("POSTGRES_DB", "recommendations")
    user = os.getenv("POSTGRES_USER", "user")
    password = os.getenv("POSTGRES_PASSWORD", "password")

    minconn = int(os.getenv("POSTGRES_POOL_MINCONN", "1"))
    maxconn = int(os.getenv("POSTGRES_POOL_MAXCONN", "20"))

    _pool = ThreadedConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )
    return _pool


@contextmanager
def get_connection():
    """
    Get a connection from the pool and always return it.

    Callers should create cursors and close them; we handle the connection lifecycle here.
    """

    pool = _get_pool()
    conn = pool.getconn()
    try:
        # Avoid leaving open transactions around pooled connections.
        conn.autocommit = True
        yield conn
    finally:
        try:
            conn.rollback()
        except Exception:
            # If rollback fails, still return the connection to the pool.
            pass
        pool.putconn(conn)