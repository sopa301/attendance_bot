import asyncio
import os

import redis
from dotenv import dotenv_values

from util.debouncer import RedisDebouncer

env_vars = dotenv_values(".env")
print(env_vars.keys())


async def test_redis_debouncer():
    debouncer = RedisDebouncer(redis_url=env_vars["REDIS_URL"])

    # fire call 1 + call 2 at the same time
    task1 = asyncio.create_task(
        debouncer.debounce("test_key", lambda: print("Executed 1!"))
    )
    task2 = asyncio.create_task(
        debouncer.debounce("test_key", lambda: print("Executed 2!"))
    )

    print("Both calls dispatched.")

    await asyncio.gather(task1, task2)

    await asyncio.sleep(1)

    # now a third call should get through
    await debouncer.debounce("test_key", lambda: print("Executed 3!"))
    print("Debounce call 3 made.")


if __name__ == "__main__":
    asyncio.run(test_redis_debouncer())
