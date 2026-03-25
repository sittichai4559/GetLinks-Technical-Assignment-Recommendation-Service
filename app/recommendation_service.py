import json
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple

from app.database import get_connection
from app.redis_client import redis_client

CACHE_TTL = 600


def _build_cache_key(user_id: int, limit: int) -> str:
    return f"rec:user:{user_id}:limit:{limit}"


def _load_cached_recommendations(
    cache_key: str,
) -> tuple[List[Dict[str, Any]] | None, bool]:
    try:
        cached = redis_client.get(cache_key)
    except Exception:
        # Redis errors should not prevent serving recommendations.
        cached = None

    if cached is None:
        return None, False

    return json.loads(cached), True


def _fetch_user_genres_history(conn: Any, user_id: int) -> Sequence[Tuple[str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.genre
            FROM user_watch_history uwh
            JOIN content c ON uwh.content_id=c.id
            WHERE uwh.user_id=%s
            """,
            (user_id,),
        )
        return cur.fetchall()


def _compute_genre_preference(history: Sequence[Tuple[str]]) -> Dict[str, float]:
    genre_count: Dict[str, int] = {}
    for (g,) in history:
        genre_count[g] = genre_count.get(g, 0) + 1

    total = sum(genre_count.values())
    genre_pref: Dict[str, float] = {}
    if total > 0:
        for g, c in genre_count.items():
            genre_pref[g] = c / total

    return genre_pref


def _fetch_candidate_content(conn: Any, user_id: int) -> Sequence[Tuple[Any, ...]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,title,genre,popularity_score,created_at
            FROM content
            WHERE id NOT IN (
                SELECT content_id FROM user_watch_history WHERE user_id=%s
            )
            ORDER BY popularity_score DESC
            LIMIT 100
            """,
            (user_id,),
        )
        return cur.fetchall()


def _score_candidates(
    candidates: Sequence[Tuple[Any, ...]], genre_pref: Dict[str, float], limit: int
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    now = datetime.utcnow()

    for c in candidates:
        content_id, title, genre, popularity, created = c

        days = (now - created).days
        recency = 1 / (1 + days / 365)

        score = (
            popularity * 0.4
            + genre_pref.get(genre, 0.1) * 0.35
            + recency * 0.15
            + random.uniform(-0.05, 0.05)
        )

        results.append(
            {
                "content_id": content_id,
                "title": title,
                "genre": genre,
                "popularity_score": popularity,
                "score": score,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def _store_cached_recommendations(
    cache_key: str, result: List[Dict[str, Any]]
) -> None:
    try:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    except Exception:
        # Treat cache failures as non-fatal.
        pass

def _legacy_get_recommendations(user_id: int, limit: int):

    # Kept only for reference; the module-level `get_recommendations` contains
    # the refactored implementation.
    return get_recommendations(user_id, limit)
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached), True

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.genre
        FROM user_watch_history uwh
        JOIN content c ON uwh.content_id=c.id
        WHERE uwh.user_id=%s
    """,(user_id,))

    history = cur.fetchall()

    genre_count = {}
    for (g,) in history:
        genre_count[g] = genre_count.get(g,0)+1

    total = sum(genre_count.values())
    genre_pref = {}

    if total>0:
        for g,c in genre_count.items():
            genre_pref[g] = c/total

    cur.execute("""
        SELECT id,title,genre,popularity_score,created_at
        FROM content
        WHERE id NOT IN (
            SELECT content_id FROM user_watch_history WHERE user_id=%s
        )
        ORDER BY popularity_score DESC
        LIMIT 100
    """,(user_id,))

    candidates = cur.fetchall()

    time.sleep(random.randint(30,50)/1000)

    results = []

    for c in candidates:

        content_id,title,genre,popularity,created = c

        days = (datetime.utcnow()-created).days
        recency = 1/(1+days/365)

        score = (
            popularity*0.4
            + genre_pref.get(genre,0.1)*0.35
            + recency*0.15
            + random.uniform(-0.05,0.05)
        )

        results.append({
            "content_id":content_id,
            "title":title,
            "genre":genre,
            "popularity_score":popularity,
            "score":score
        })

    results.sort(key=lambda x:x["score"], reverse=True)

    result = results[:limit]

    redis_client.setex(cache_key,CACHE_TTL,json.dumps(result))

    cur.close()
    conn.close()

    return result, False


# Refactored implementation (kept after the original for minimal risk).
# Note: In Python, the last function definition wins.
def get_recommendations(user_id: int, limit: int):
    cache_key = _build_cache_key(user_id, limit)

    cached_result, cache_hit = _load_cached_recommendations(cache_key)
    if cached_result is not None:
        return cached_result, cache_hit

    with get_connection() as conn:
        history = _fetch_user_genres_history(conn, user_id)
        genre_pref = _compute_genre_preference(history)
        candidates = _fetch_candidate_content(conn, user_id)

        # Simulate additional work on cache miss.
        time.sleep(random.randint(30, 50) / 1000)

        result = _score_candidates(candidates, genre_pref, limit)

    _store_cached_recommendations(cache_key, result)
    return result, False