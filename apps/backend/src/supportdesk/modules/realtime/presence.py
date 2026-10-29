"""Expiring per-connection presence indexed by an authorized conversation."""

import time
from uuid import UUID

from redis.asyncio import Redis


async def update_presence(
    redis: Redis,
    workspace: UUID,
    conversation: UUID,
    actor: UUID,
    connection: UUID,
    *,
    online: bool = True,
) -> set[UUID]:
    key = f"sd:presence:{workspace}:{conversation}"
    member = f"{actor}:{connection}"
    clock = time.time()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, "-inf", clock)
        if online:
            pipe.zadd(key, {member: clock + 30})
        else:
            pipe.zrem(key, member)
        pipe.expire(key, 45)
        pipe.zrange(key, 0, -1)
        result = await pipe.execute()
    return {UUID(item.decode().split(":")[0]) for item in result[-1]}
