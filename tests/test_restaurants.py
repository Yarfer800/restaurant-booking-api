from httpx import AsyncClient

from tests.conftest import admin_headers, create_restaurant, create_table, login_as, register_user


async def test_list_restaurants_empty(client: AsyncClient) -> None:
    resp = await client.get("/restaurants")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_restaurant_requires_admin(client: AsyncClient) -> None:
    headers = {"Authorization": "Bearer invalid"}
    resp = await create_restaurant(client, headers)
    assert resp.status_code == 401


async def test_regular_user_cannot_create_restaurant(client: AsyncClient) -> None:
    await register_user(client)
    access, _ = await login_as(client, "user@example.com")

    resp = await create_restaurant(client, {"Authorization": f"Bearer {access}"})
    assert resp.status_code == 403


async def test_admin_creates_restaurant(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    resp = await create_restaurant(client, headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Тестовый ресторан"
    assert body["opening_time"] == "09:00:00"
    assert body["closing_time"] == "23:00:00"


async def test_get_restaurant_with_tables(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    assert restaurant.status_code == 201
    restaurant_id = restaurant.json()["id"]

    await client.post(
        f"/restaurants/{restaurant_id}/tables",
        json={"number": "3", "capacity": 6},
        headers=headers,
    )

    resp = await client.get(f"/restaurants/{restaurant_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == restaurant_id
    assert len(body["tables"]) == 1
    assert body["tables"][0]["number"] == "3"


async def test_get_restaurant_not_found(client: AsyncClient) -> None:
    resp = await client.get("/restaurants/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Ресторан не найден"


async def test_pagination(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    for i in range(3):
        await create_restaurant(client, headers, name=f"Ресторан {i}")

    resp = await client.get("/restaurants", params={"limit": 2, "offset": 1})
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


async def test_update_restaurant(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]

    resp = await client.patch(
        f"/restaurants/{restaurant_id}",
        json={"name": "Новое название"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Новое название"


async def test_delete_restaurant(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]

    resp = await client.delete(f"/restaurants/{restaurant_id}", headers=headers)
    assert resp.status_code == 204

    detail = await client.get(f"/restaurants/{restaurant_id}")
    assert detail.status_code == 404


async def test_available_tables_cached(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]
    table = await create_table(client, restaurant_id, headers)
    table_id = table.json()["id"]
    await create_table(client, restaurant_id, headers, number="2", capacity=2)

    params = {
        "start": "2026-08-01T18:00:00",
        "end": "2026-08-01T19:00:00",
        "guests": 4,
    }
    resp = await client.get(f"/restaurants/{restaurant_id}/tables/available", params=params)
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()] == [table_id]

    resp2 = await client.get(f"/restaurants/{restaurant_id}/tables/available", params=params)
    assert resp2.json() == resp.json()
