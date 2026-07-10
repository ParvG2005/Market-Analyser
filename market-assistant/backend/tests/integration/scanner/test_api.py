import pytest
from httpx import AsyncClient

VALID_RULE = {
    "name": "RSI dip + volume spike",
    "definition": {
        "all": [
            {"ind": "rsi", "tf": "5m", "op": "<", "value": 30},
            {"ind": "rel_volume", "tf": "5m", "op": ">", "value": 2},
        ]
    },
}


@pytest.mark.asyncio
async def test_create_rule_returns_201_with_id(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == VALID_RULE["name"]
    assert body["enabled"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_create_rule_with_invalid_dsl_returns_422(client: AsyncClient, auth_headers: dict):
    bad_rule = {"name": "bad", "definition": {"ind": "not_real", "tf": "5m", "op": "<", "value": 1}}
    resp = await client.post("/api/scanner/rules", json=bad_rule, headers=auth_headers)
    assert resp.status_code == 422
    assert "ind" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_rules_scoped_to_current_user(
    client: AsyncClient, auth_headers: dict, other_user_headers: dict
):
    await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    resp = await client.get("/api/scanner/rules", headers=other_user_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_patch_toggles_enabled(client: AsyncClient, auth_headers: dict):
    created = (
        await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    ).json()
    resp = await client.patch(
        f"/api/scanner/rules/{created['id']}", json={"enabled": False}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_delete_removes_rule(client: AsyncClient, auth_headers: dict):
    created = (
        await client.post("/api/scanner/rules", json=VALID_RULE, headers=auth_headers)
    ).json()
    resp = await client.delete(f"/api/scanner/rules/{created['id']}", headers=auth_headers)
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/scanner/rules/{created['id']}", headers=auth_headers)
    assert resp2.status_code == 404
