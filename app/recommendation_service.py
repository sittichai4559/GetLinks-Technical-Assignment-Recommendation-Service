import random
import time
import json
from datetime import datetime

from app.database import get_connection
from app.redis_client import redis_client

CACHE_TTL = 600

def get_recommendations(user_id, limit):

    cache_key = f"rec:user:{user_id}:limit:{limit}"
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