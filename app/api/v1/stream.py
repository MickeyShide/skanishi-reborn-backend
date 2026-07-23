import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.redis_client import redis_client
from app.api.v1.dependencies import StreamUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])

async def event_generator(request: Request, user_id: int) -> AsyncGenerator[dict, None]:
    redis = redis_client
    pubsub = redis.pubsub()
    channel = f"user_events:{user_id}"
    await pubsub.subscribe(channel)
    logger.info(f"SSE client connected to {channel}")
    
    try:
        while True:
            # Pinging to keep connection alive
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected from {channel}")
                break
                
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10.0)
            if message is not None:
                data = message["data"]
                # Decode bytes to str if needed
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield {
                    "event": "message",
                    "data": data
                }
            else:
                # Keep-alive empty message
                yield {
                    "event": "ping",
                    "data": "ping"
                }
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


@router.get("/events")
async def sse_endpoint(
    request: Request,
    current_user: StreamUser,
):
    """
    Endpoint for SSE (Server-Sent Events).
    Connect from frontend using:
    const eventSource = new EventSource('/api/v1/stream/events?token=...');
    """
    return EventSourceResponse(event_generator(request, current_user.id))
