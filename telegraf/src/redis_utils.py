from typing import Optional

import redis

DEFAULT_REDIS_HOST = 'localhost'
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB_INDEX = 0
DEFAULT_REDIS_URL = f"redis://{DEFAULT_REDIS_HOST}:{DEFAULT_REDIS_PORT}/{DEFAULT_REDIS_DB_INDEX}"


def redis_init(
        host: Optional[str] = DEFAULT_REDIS_HOST,
        port: Optional[int] = DEFAULT_REDIS_PORT,
        db: Optional[int] = DEFAULT_REDIS_DB_INDEX,
        password: Optional[str] = None):
    if password is not None:
        return redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            password=password,
            charset="utf-8",
            decode_responses=True)
    else:
        return redis.Redis(
            host=host,
            port=port,
            db=db,
            charset="utf-8",
            decode_responses=True)


def redis_init_from_url(url: str):
    return redis.from_url(url=url, decode_responses=True)
