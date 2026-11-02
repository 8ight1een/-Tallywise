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


def create_account(client, name="现金"):
    response = client.post("/api/accounts", json={"name_accounts": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_category(client, name="餐饮", money_type="支出"):
    response = client.post(
        "/api/categories",
        json={"name_categories": name, "money_type": money_type},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_transaction(
    client,
    account_id,
    category_id,
    transaction_date,
    money="10.00",
    description=None,
    money_type="支出",
):
    response = client.post(
        "/api/transactions",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "account_id": account_id,
            "category_id": category_id,
            "money": money,
            "money_type": money_type,
            "description": description,
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


def get_page(client, cursor=None, limit=2, **filters):
    params = {"year": 2026, "month": 10, "limit": limit}
    params.update(filters)
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


def test_page_returns_total_and_total_pages(seeded):
    client, _created = seeded

    first = get_page(client, limit=2)
    second = get_page(client, cursor=first["next_cursor"], limit=2)
    last = get_page(client, limit=7)
    empty = client.get(
        "/api/transactions/page",
        params={"year": 2026, "month": 11, "limit": 20},
    ).json()

    assert first["total"] == 7
    assert first["total_pages"] == 4
    assert second["total"] == 7
    assert last["total"] == 7
    assert last["total_pages"] == 1
    assert empty["total"] == 0
    assert empty["total_pages"] == 0


def test_search_matches_description_account_and_category(seeded):
    client, _created = seeded
    search_account = create_account(client, name="搜索账户")
    search_category = create_category(client, name="搜索分类")
    target = create_transaction(
        client,
        search_account,
        search_category,
        "2026-10-21",
        money="99.00",
        description="周末咖啡",
    )

    by_description = get_page(client, limit=20, q="咖啡")
    by_account = get_page(client, limit=20, q="现金")
    by_category = get_page(client, limit=20, q="餐饮")
    missing = get_page(client, limit=20, q="不存在")

    assert [item["id"] for item in by_description["items"]] == [target["id"]]
    assert by_description["total"] == 1
    assert by_account["total"] == 7
    assert by_category["total"] == 7
    assert missing["total"] == 0


def test_filter_by_money_type_and_account(seeded):
    client, _created = seeded
    income_category = create_category(client, name="工资", money_type="收入")
    bank_account = create_account(client, name="银行卡")
    income = create_transaction(
        client,
        bank_account,
        income_category,
        "2026-10-21",
        money="500.00",
        money_type="收入",
    )

    by_type = get_page(client, limit=20, money_type="收入")
    by_account = get_page(client, limit=20, account_id=bank_account)
    mismatch = get_page(client, limit=20, account_id=bank_account, money_type="支出")

    assert [item["id"] for item in by_type["items"]] == [income["id"]]
    assert by_type["total"] == 1
    assert [item["id"] for item in by_account["items"]] == [income["id"]]
    assert by_account["total"] == 1
    assert mismatch["total"] == 0


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
