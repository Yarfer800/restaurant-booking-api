from httpx import AsyncClient

from tests.conftest import admin_headers, create_restaurant, create_table, login_as, register_user


async def test_create_table_requires_admin(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]

    await register_user(client)
    access, _ = await login_as(client, "user@example.com")
    resp = await client.post(
        f"/restaurants/{restaurant_id}/tables",
        json={"number": "1", "capacity": 4},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 403


async def test_create_table_in_missing_restaurant(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    resp = await client.post(
        "/restaurants/999/tables",
        json={"number": "1", "capacity": 4},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_create_and_get_table(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]

    created = await create_table(client, restaurant_id, headers, number="5", capacity=8)
    assert created.status_code == 201
    table_id = created.json()["id"]
    assert created.json()["number"] == "5"
    assert created.json()["capacity"] == 8

    got = await client.get(f"/tables/{table_id}")
    assert got.status_code == 200
    assert got.json()["restaurant_id"] == restaurant_id


async def test_duplicate_table_number_in_restaurant(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]

    await create_table(client, restaurant_id, headers, number="1")
    resp = await create_table(client, restaurant_id, headers, number="1")
    assert resp.status_code == 500


async def test_update_table(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]
    table = await create_table(client, restaurant_id, headers)
    table_id = table.json()["id"]

    resp = await client.put(
        f"/tables/{table_id}",
        json={"capacity": 10},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["capacity"] == 10


async def test_delete_table(client: AsyncClient) -> None:
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]
    table = await create_table(client, restaurant_id, headers)
    table_id = table.json()["id"]

    resp = await client.delete(f"/tables/{table_id}", headers=headers)
    assert resp.status_code == 204

    got = await client.get(f"/tables/{table_id}")
    assert got.status_code == 404


async def test_get_table_not_found(client: AsyncClient) -> None:
    resp = await client.get("/tables/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Стол не найден"
