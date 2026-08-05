import os
import redis

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Ping to check connection
    redis_client.ping()
    print(f"[REDIS] Connected successfully to {REDIS_URL}")
except Exception as e:
    print(f"[REDIS WARNING] Could not connect to Redis: {e}. Running without Redis tracking.")
    redis_client = None

def track_question(query: str):
    if redis_client is None:
        return
    try:
        cleaned_query = query.strip()
        if len(cleaned_query) > 2:
            # Increment frequency of question in sorted set 'frequent_questions'
            redis_client.zincrby("frequent_questions", 1, cleaned_query)
            # Set TTL to 60 minutes (3600 seconds) so the leaderboard resets if inactive
            redis_client.expire("frequent_questions", 3600)
    except Exception as e:
        print(f"[REDIS ERROR] Failed to track question: {e}")

def get_frequent_questions_list(limit: int = 10) -> list:
    if redis_client is None:
        return []
    try:
        results = redis_client.zrevrange("frequent_questions", 0, limit - 1, withscores=True)
        return [{"question": q, "count": int(score)} for q, score in results]
    except Exception as e:
        print(f"[REDIS ERROR] Failed to fetch frequent questions: {e}")
        return []
