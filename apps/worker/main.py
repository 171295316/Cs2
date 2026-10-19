"""Dependency heartbeat; provider scheduling is disabled until authorization exists."""
import os
import time

from redis import Redis

cache = Redis.from_url(os.environ["REDIS_URL"])
while True:
    cache.set("cs2:worker:heartbeat", "ok", ex=60)
    time.sleep(20)
