import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.event_bus import bus

router = APIRouter(prefix="/events", tags=["Events"])

async def sse_generator():
    q = await bus.subscribe()
    try:
        yield "retry: 5000\n\n"
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=1.0)
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield ":keepalive\n\n"
    finally:
        await bus.unsubscribe(q)

@router.get("/stream")
async def stream_events():
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(sse_generator(), media_type="text/event-stream", headers=headers)
