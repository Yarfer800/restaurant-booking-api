from httpx import AsyncClient

from tests.conftest import (
    admin_headers,
    auth_headers,
    create_restaurant,
    create_table,
    login_as,
    register_user,
)


async def setup_restaurant(client: AsyncClient) -> tuple[dict[str, str], int, int]:
    """Создаёт ресторан со столиком на 4 персоны, возвращает headers, restaurant_id, table_id."""
    headers = await admin_headers(client)
    restaurant = await create_restaurant(client, headers)
    restaurant_id = restaurant.json()["id"]
    table = await create_table(client, restaurant_id, headers, number="1", capacity=4)
    return headers, restaurant_id, table.json()["id"]


async def setup_user(client: AsyncClient, email: str = "user@example.com"):
    await register_user(client, email=email)
    access, _ = await login_as(client, email)
    return auth_headers(access)


def reservation_payload(table_id: int, start: str = "2026-08-01T18:00:00", end: str = "2026-08-01T19:00:00") -> dict:
    return {"table_id": table_id, "guest_count": 2, "start_time": start, "end_time": end}


async def test_create_reservation(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    resp = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["table_id"] == table_id
    assert body["guest_count"] == 2
    assert body["status"] == "pending"
    assert body["table_number"] == "1"
    assert body["restaurant_name"] == "Тестовый ресторан"
    assert body["user_id"]


async def test_create_reservation_requires_auth(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    resp = await client.post("/reservations", json=reservation_payload(table_id))
    assert resp.status_code == 401


async def test_capacity_exceeded(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    payload = reservation_payload(table_id)
    payload["guest_count"] = 6
    resp = await client.post("/reservations", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "вместимость" in resp.json()["detail"]


async def test_overlapping_reservation_conflict(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    first = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    assert first.status_code == 201

    payload = reservation_payload(table_id, start="2026-08-01T18:30:00", end="2026-08-01T19:30:00")
    second = await client.post("/reservations", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"] == "Стол уже занят в выбранное время"


async def test_non_overlapping_reservation_ok(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    first = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    assert first.status_code == 201

    payload = reservation_payload(table_id, start="2026-08-01T20:00:00", end="2026-08-01T21:00:00")
    second = await client.post("/reservations", json=payload, headers=headers)
    assert second.status_code == 201


async def test_outside_working_hours(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    payload = reservation_payload(table_id, start="2026-08-01T00:00:00", end="2026-08-01T01:00:00")
    resp = await client.post("/reservations", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "рабочие часы" in resp.json()["detail"]


async def test_invalid_time_range(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    payload = reservation_payload(table_id, start="2026-08-01T20:00:00", end="2026-08-01T19:00:00")
    resp = await client.post("/reservations", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "раньше" in resp.json()["detail"]


async def test_user_own_reservations_list(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    await client.post("/reservations", json=reservation_payload(table_id), headers=headers)

    resp = await client.get("/me/reservations", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"


async def test_user_cannot_see_other_reservation(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    first_headers = await setup_user(client, "user@example.com")
    second_headers = await setup_user(client, "other@example.com")

    created = await client.post("/reservations", json=reservation_payload(table_id), headers=first_headers)
    reservation_id = created.json()["id"]

    resp = await client.get(f"/reservations/{reservation_id}", headers=second_headers)
    assert resp.status_code == 403


async def test_cancel_own_reservation(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    created = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    reservation_id = created.json()["id"]

    resp = await client.post(f"/reservations/{reservation_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_confirm_needs_admin(client: AsyncClient) -> None:
    admin, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    created = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    reservation_id = created.json()["id"]

    denied = await client.post(f"/reservations/{reservation_id}/confirm", headers=headers)
    assert denied.status_code == 403

    ok = await client.post(f"/reservations/{reservation_id}/confirm", headers=admin)
    assert ok.status_code == 200
    assert ok.json()["status"] == "confirmed"


async def test_complete_reservation(client: AsyncClient) -> None:
    admin, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    created = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    reservation_id = created.json()["id"]

    await client.post(f"/reservations/{reservation_id}/confirm", headers=admin)
    resp = await client.post(f"/reservations/{reservation_id}/complete", headers=admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_cancelled_reservation_frees_slot(client: AsyncClient) -> None:
    _, _, table_id = await setup_restaurant(client)
    headers = await setup_user(client)

    created = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    await client.post(f"/reservations/{created.json()['id']}/cancel", headers=headers)

    retry = await client.post("/reservations", json=reservation_payload(table_id), headers=headers)
    assert retry.status_code == 201
