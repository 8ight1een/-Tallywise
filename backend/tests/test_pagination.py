from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def auth_client(client):
    email = "pagination@example.com"
    registered = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "password123",
            "nickname": "分页测试",
        },
    )
    assert registered.status_code == 200, registered.text

    logged_in = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    return client


def create_account(client):
    response = client.post("/api/accounts", json={"name_accounts": "现金"})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_category(client):
    response = client.post(
        "/api/categories",
        json={"name_categories": "餐饮", "money_type": "支出"},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_transaction(client, account_id, category_id, transaction_date, money="10.00"):
    response = client.post(
        "/api/transactions",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "account_id": account_id,
            "category_id": category_id,
            "money": money,
            "money_type": "支出",
            "description": None,
            "transaction_date": transaction_date,
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture
def seeded(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)
    rows = [
        ("2026-10-18", "10.00"),
        ("2026-10-18", "11.00"),
        ("2026-10-19", "12.00"),
        ("2026-10-19", "13.00"),
        ("2026-10-20", "14.00"),
        ("2026-10-20", "15.00"),
        ("2026-10-20", "16.00"),
    ]
    created = []
    for day, money in rows:
        txn = create_transaction(auth_client, account_id, category_id, day, money)
        created.append((day, txn["id"]))
    return auth_client, created


def get_page(client, cursor=None, limit=2):
    params = {"year": 2026, "month": 10, "limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    response = client.get("/api/transactions/page", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_pages_cover_all_rows_without_duplicates(seeded):
    client, created = seeded

    seen = []
    cursor = None
    for _ in range(20):
        body = get_page(client, cursor=cursor)
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    expected = [
        transaction_id
        for _day, transaction_id in sorted(
            created,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
    ]
    assert seen == expected
    assert len(seen) == len(set(seen)) == 7


def test_same_day_rows_are_not_lost(seeded):
    client, created = seeded
    same_day = {transaction_id for day, transaction_id in created if day == "2026-10-20"}

    first = get_page(client, limit=2)
    second = get_page(client, cursor=first["next_cursor"], limit=2)
    seen = {item["id"] for item in first["items"] + second["items"]}

    assert same_day <= seen


def test_invalid_cursor_returns_422(seeded):
    client, _created = seeded
    response = client.get(
        "/api/transactions/page",
        params={"year": 2026, "month": 10, "cursor": "not-a-cursor"},
    )
    assert response.status_code == 422


def test_empty_cursor_returns_422(seeded):
    client, _created = seeded
    response = client.get(
        "/api/transactions/page",
        params={"year": 2026, "month": 10, "cursor": ""},
    )
    assert response.status_code == 422


def test_last_page_has_no_next_cursor(seeded):
    client, _created = seeded
    body = get_page(client, limit=7)

    assert len(body["items"]) == 7
    assert body["has_more"] is False
    assert body["next_cursor"] is None


def test_empty_month_returns_empty_page(seeded):
    client, _created = seeded
    body = get_page(client)
    empty = client.get(
        "/api/transactions/page",
        params={"year": 2026, "month": 11, "limit": 20},
    ).json()

    assert empty["items"] == []
    assert empty["next_cursor"] is None
    assert empty["has_more"] is False
    assert body["has_more"] is True


def test_user_isolation(seeded):
    client, _created = seeded

    with TestClient(app) as other:
        registered = other.post(
            "/api/auth/register",
            json={
                "email": "pagination-other@example.com",
                "password": "password123",
                "nickname": "另一个用户",
            },
        )
        assert registered.status_code == 200, registered.text
        logged_in = other.post(
            "/api/auth/login",
            json={"email": "pagination-other@example.com", "password": "password123"},
        )
        assert logged_in.status_code == 200, logged_in.text

        response = other.get(
            "/api/transactions/page",
            params={"year": 2026, "month": 10, "limit": 20},
        )
        assert response.status_code == 200, response.text
        assert response.json()["items"] == []
