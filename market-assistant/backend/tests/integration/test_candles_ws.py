import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app

# In the test env the WS token is accepted as a raw user UUID
# (get_current_user_id_from_ws_token non-prod fallback). Channels are keyed by
# symbol:tf, so any valid token admits the connection.
TOKEN = uuid.uuid4()
CANDLES_URL = f"/ws/candles?token={TOKEN}"


def test_ws_subscribe_receives_update_on_new_candle(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect(CANDLES_URL) as ws:
            ws.send_json({"subscribe": "candles:BTC/USDT:1m"})
            time.sleep(0.2)  # let the server complete SUBSCRIBE before we publish

            candle = {
                "ts": "2024-01-01T00:01:00Z",
                "o": 100,
                "h": 101,
                "l": 99,
                "c": 100.5,
                "v": 10,
            }
            redis_sync_client.publish("candles:BTC/USDT:1m", json.dumps(candle))

            received = json.loads(ws.receive_text())
            assert received == candle


def test_ws_resubscribe_stops_forwarding_old_channel(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect(CANDLES_URL) as ws:
            ws.send_json({"subscribe": "candles:BTC/USDT:1m"})
            time.sleep(0.2)
            ws.send_json({"subscribe": "candles:ETH/USDT:1m"})
            time.sleep(0.2)

            redis_sync_client.publish("candles:BTC/USDT:1m", json.dumps({"stale": True}))
            eth_candle = {"ts": "2024-01-01T00:01:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1}
            redis_sync_client.publish("candles:ETH/USDT:1m", json.dumps(eth_candle))

            received = json.loads(ws.receive_text())
            assert received == eth_candle


def test_ws_rejects_missing_token():
    # No ?token= -> FastAPI's required Query(...) rejects the handshake before
    # accept(); Starlette's TestClient surfaces that as WebSocketDisconnect.
    with TestClient(create_app()) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/candles"):
                pass


def test_ws_rejects_invalid_token():
    # A non-UUID token fails both JWT verification and the raw-UUID fallback, so
    # authenticate_ws closes the handshake (1008) before accept().
    with TestClient(create_app()) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/candles?token=not-a-valid-token"):
                pass
