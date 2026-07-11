import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio.client import PubSub

from app.core.deps import get_redis

router = APIRouter()


async def _forward(pubsub: PubSub, websocket: WebSocket) -> None:
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        data = message["data"]
        # decode_responses=True yields str; guard bytes defensively.
        if isinstance(data, bytes):
            data = data.decode()
        await websocket.send_text(data)


@router.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket) -> None:
    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    forward_task: asyncio.Task[None] | None = None
    try:
        while True:
            msg = await websocket.receive_json()
            channel = msg.get("subscribe")
            if not channel:
                continue
            if forward_task is not None:
                forward_task.cancel()
                await pubsub.unsubscribe()
            await pubsub.subscribe(channel)
            forward_task = asyncio.create_task(_forward(pubsub, websocket))
    except WebSocketDisconnect:
        pass
    finally:
        if forward_task is not None:
            forward_task.cancel()
        await pubsub.aclose()  # type: ignore[no-untyped-call]
