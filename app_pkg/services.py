import asyncio
import random
import time
from watchfiles import awatch


async def create_data(manager):
    """Generate simulation data and broadcast to all users"""
    t = 0
    try:
        while True:
            a = 4 * random.random()
            type = "chart_1_update"
            if a % 1 < 0.5:
                type = "chart_2_update"

            counter = 0
            for user in manager.user_queues.keys():
                if counter <= a and a < counter + 1:
                    await manager.broadcast_to_user(
                        user,
                        {
                            "type": type,
                            "time": t,
                            "value": a,
                            "timestamp": int(time.time()),
                        },
                    )
                    break
                counter += 1
            t += 1
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Error in create_data: {e}")


async def watch_file(manager, path: str = "data.txt"):
    """Watch for file changes and notify all users"""
    try:
        async for _changes in awatch(path):
            print("File changed:", _changes)
            await manager.broadcast_to_all_users(
                {
                    "type": "file_update",
                    "event": "file_updated",
                    "timestamp": int(time.time()),
                }
            )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Error in watch_file: {e}")
