import json
import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_ws_subscribe_receives_published_signal(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws/signals") as ws:
            ws.send_json({"subscribe": "signals:BTC/USDT:15m"})
            time.sleep(0.2)  # let the server complete SUBSCRIBE before we publish

            signal = {
                "id": 1,
                "instrument_id": 1,
                "strategy": "orb",
                "direction": "long",
                "ts": "2024-01-01T10:15:00Z",
                "confidence": None,
                "ref_entry": 107.0,
                "ref_sl": 100.0,
                "ref_tp": 121.0,
                "backtest_ref": None,
                "meta": {"or_high": 105, "or_low": 100},
            }
            redis_sync_client.publish("signals:BTC/USDT:15m", json.dumps(signal))

            received = json.loads(ws.receive_text())
            assert received == signal


def test_ws_resubscribe_stops_forwarding_old_channel(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws/signals") as ws:
            ws.send_json({"subscribe": "signals:BTC/USDT:15m"})
            time.sleep(0.2)
            ws.send_json({"subscribe": "signals:ETH/USDT:15m"})
            time.sleep(0.2)

            redis_sync_client.publish("signals:BTC/USDT:15m", json.dumps({"stale": True}))
            eth_signal = {"id": 2, "strategy": "orb", "direction": "short"}
            redis_sync_client.publish("signals:ETH/USDT:15m", json.dumps(eth_signal))

            received = json.loads(ws.receive_text())
            assert received == eth_signal
