import asyncio
from typing import List

class EventBus:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        async with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    async def publish(self, event: dict):
        async with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                await q.put(event)
            except asyncio.CancelledError:
                pass

bus = EventBus()
