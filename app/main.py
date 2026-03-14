from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor
from app.recommendation_service import get_recommendations

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=10)

@app.get("/users/{user_id}/recommendations")
def single(user_id:int, limit:int=10):
    recs, cache_hit = get_recommendations(user_id, limit)
    return {
        "user_id": user_id,
        "recommendations": recs,
        "metadata": {
            "cache_hit": cache_hit,
            "total_count": len(recs)
        }
    }

@app.get("/recommendations/batch")
def batch(page:int=1, limit:int=20):
    users = range((page-1)*limit+1, page*limit+1)

    futures = [
        executor.submit(get_recommendations, u, 10)
        for u in users
    ]

    results = []

    for u,f in zip(users,futures):
        try:
            recs,_ = f.result()
            results.append({
                "user_id":u,
                "status":"success",
                "recommendations":recs
            })
        except Exception as e:
            results.append({
                "user_id":u,
                "status":"failed",
                "error":str(e)
            })

    return {
        "page":page,
        "limit":limit,
        "results":results
    }