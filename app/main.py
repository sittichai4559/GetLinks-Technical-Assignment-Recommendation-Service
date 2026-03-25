from concurrent.futures import ThreadPoolExecutor
import os

from fastapi import FastAPI

from app.recommendation_service import get_recommendations
from app.schemas import BatchRecommendationsResponse, SingleRecommendationsResponse

app = FastAPI()


@app.on_event("startup")
def _startup() -> None:
    # Create once per process. We keep this lightweight; Postgres uses a pool already.
    app.state.executor = ThreadPoolExecutor(
        max_workers=int(os.getenv("RECOMMENDATION_THREADPOOL_MAX_WORKERS", "10"))
    )


@app.on_event("shutdown")
def _shutdown() -> None:
    executor = getattr(app.state, "executor", None)
    if executor is not None:
        executor.shutdown(wait=False)


@app.get("/users/{user_id}/recommendations", response_model=SingleRecommendationsResponse)
def single(user_id: int, limit: int = 10):
    recs, cache_hit = get_recommendations(user_id, limit)
    return {
        "user_id": user_id,
        "recommendations": recs,
        "metadata": {
            "cache_hit": cache_hit,
            "total_count": len(recs),
        },
    }


@app.get("/recommendations/batch", response_model=BatchRecommendationsResponse)
def batch(page: int = 1, limit: int = 20):
    users = range((page - 1) * limit + 1, page * limit + 1)

    executor = app.state.executor
    recommendations_per_user = 10  # Historical behavior: `limit` = number of users in the batch.

    futures = [
        executor.submit(get_recommendations, u, recommendations_per_user) for u in users
    ]

    results = []
    for u, f in zip(users, futures):
        try:
            recs, _ = f.result()
            results.append(
                {
                    "user_id": u,
                    "status": "success",
                    "recommendations": recs,
                }
            )
        except Exception as e:
            results.append(
                {
                    "user_id": u,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return {
        "page": page,
        "limit": limit,
        "results": results,
    }