from httpx import AsyncClient

from tests.conftest import auth_headers, login_as, login_user, register_user


async def test_register_creates_user(client: AsyncClient) -> None:
    resp = await register_user(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "user"
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflict(client: AsyncClient) -> None:
    await register_user(client)
    resp = await register_user(client)
    assert resp.status_code == 409
    assert "detail" in resp.json()


async def test_register_short_password_rejected(client: AsyncClient) -> None:
    resp = await register_user(client, password="short")
    assert resp.status_code == 422


async def test_login_returns_tokens(client: AsyncClient) -> None:
    await register_user(client)
    resp = await login_user(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password(client: AsyncClient) -> None:
    await register_user(client)
    resp = await login_user(client, password="wrong-password")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Неверный email или пароль"


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    await register_user(client)
    login = await login_user(client)
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"] != refresh_token


async def test_refresh_rejects_blacklisted_token(client: AsyncClient) -> None:
    await register_user(client)
    access, refresh = await login_as(client, "user@example.com")

    await client.post("/auth/logout", json={"refresh_token": refresh}, headers=auth_headers(access))

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Refresh-токен отозван"


async def test_logout_blacklists_access_token(client: AsyncClient) -> None:
    await register_user(client)
    access, refresh = await login_as(client, "user@example.com")

    resp = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh},
        headers=auth_headers(access),
    )
    assert resp.status_code == 200

    me = await client.get("/me/reservations", headers=auth_headers(access))
    assert me.status_code == 401
