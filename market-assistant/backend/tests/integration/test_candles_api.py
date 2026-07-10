import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_candles_ordered_and_paginated(client: AsyncClient, seed_btc_1m_candles):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
            "limit": 10,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    timestamps = [c["ts"] for c in body]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_get_candles_bad_tf_returns_422(client: AsyncClient):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "3m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_candles_empty_range_returns_empty_list(client: AsyncClient, seed_btc_1m_candles):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "BTC/USDT",
            "tf": "1m",
            "from": "2099-01-01T00:00:00Z",
            "to": "2099-01-02T00:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_candles_unknown_symbol_returns_empty_list(client: AsyncClient):
    resp = await client.get(
        "/candles",
        params={
            "symbol": "NOPE/USDT",
            "tf": "1m",
            "from": "2024-01-01T00:00:00Z",
            "to": "2024-01-01T01:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == []
