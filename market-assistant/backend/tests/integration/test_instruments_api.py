import pytest


@pytest.mark.asyncio
async def test_list_instruments_filters_by_asset_class(client, db_session):
    resp = await client.get("/api/instruments", params={"asset_class": "equity"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(i["asset_class"] == "equity" for i in body)
    assert all(i["delayed"] is True for i in body)
    assert all(i["delay_minutes"] == 15 for i in body)


@pytest.mark.asyncio
async def test_create_instrument(client, db_session):
    resp = await client.post(
        "/api/instruments",
        json={"symbol": "WIPRO.NS", "asset_class": "equity", "exchange": "NSE"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["symbol"] == "WIPRO.NS"
    assert body["active"] is True


@pytest.mark.asyncio
async def test_patch_instrument_toggles_active(client, db_session):
    create_resp = await client.post(
        "/api/instruments",
        json={"symbol": "LTIM.NS", "asset_class": "equity", "exchange": "NSE"},
    )
    instrument_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/instruments/{instrument_id}", json={"active": False}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["active"] is False
