import json
import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_ws_subscribe_receives_update_on_new_candle(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws/candles") as ws:
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
        with client.websocket_connect("/ws/candles") as ws:
            ws.send_json({"subscribe": "candles:BTC/USDT:1m"})
            time.sleep(0.2)
            ws.send_json({"subscribe": "candles:ETH/USDT:1m"})
            time.sleep(0.2)

            redis_sync_client.publish("candles:BTC/USDT:1m", json.dumps({"stale": True}))
            eth_candle = {"ts": "2024-01-01T00:01:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1}
            redis_sync_client.publish("candles:ETH/USDT:1m", json.dumps(eth_candle))

            received = json.loads(ws.receive_text())
            assert received == eth_candle
