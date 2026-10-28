from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app


@pytest.fixture
def auth_client(client):
    registered = client.post(
        "/api/auth/register",
        json={
            "email": "api@example.com",
            "password": "password123",
            "nickname": "接口测试",
        },
    )
    assert registered.status_code == 200, registered.text

    response = client.post(
        "/api/auth/login",
        json={"email": "api@example.com", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return client


def make_transaction_payload(account_id, category_id, money="10.00", **overrides):
    payload = {
        "account_id": account_id,
        "category_id": category_id,
        "money": money,
        "money_type": "支出",
        "description": None,
        "transaction_date": "2025-01-01",
    }
    payload.update(overrides)
    return payload


def post_transaction(client, payload, key=None):
    return client.post(
        "/api/transactions",
        json=payload,
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def list_transactions(client):
    response = client.get("/api/transactions")
    assert response.status_code == 200, response.text
    return response.json()


def create_account(client, name="现金"):
    response = client.post("/api/accounts", json={"name_accounts": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_category(client, name="餐饮", money_type="支出"):
    response = client.post(
        "/api/categories", json={"name_categories": name, "money_type": money_type}
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_未登录访问受保护接口返回401(client):
    response = client.get("/api/transactions")
    assert response.status_code == 401


def test_注册响应不包含密码哈希(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "leak@example.com",
            "password": "password123",
            "nickname": "泄露检查",
        },
    )
    assert response.status_code == 200

    body = response.json()

    assert set(body.keys()) == {"id", "email", "nickname"}


def test_登录后可以拿到自己的信息(auth_client):
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "api@example.com"


def test_退出登录后不再有登录态(auth_client):
    assert auth_client.get("/api/auth/me").status_code == 200

    auth_client.post("/api/auth/logout")

    assert auth_client.get("/api/auth/me").status_code == 401


def test_重复邮箱注册返回409(client):
    payload = {
        "email": "dup@example.com",
        "password": "password123",
        "nickname": "第一个",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 200
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_密码错误返回401(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "wrongpw@example.com",
            "password": "password123",
            "nickname": "用户",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrongpw@example.com",
            "password": "bad-password",
        },
    )
    assert response.status_code == 401


def test_money_type传非法值返回422(auth_client):
    response = auth_client.get("/api/categories", params={"money_type": "转账"})
    assert response.status_code == 422


def test_未登录访问分类返回401(client):
    response = client.get("/api/categories", params={"money_type": "支出"})
    assert response.status_code == 401


def test_更新流水用的是PUT而不是POST(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    created = post_transaction(auth_client, make_transaction_payload(account_id, category_id))
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    updated = make_transaction_payload(account_id, category_id, money="20.00")

    assert auth_client.post(f"/api/transactions/{tid}", json=updated).status_code == 405

    response = auth_client.put(f"/api/transactions/{tid}", json=updated)
    assert response.status_code == 200

    assert response.json()["money"] == "20.00"


@pytest.mark.parametrize(
    "resource,create,payload",
    [
        ("accounts", create_account, {"name_accounts": "银行卡"}),
        ("categories", create_category, {"name_categories": "交通", "money_type": "支出"}),
    ],
)
def test_更新账户和分类使用PUT(auth_client, resource, create, payload):
    resource_id = create(auth_client)
    url = f"/api/{resource}/{resource_id}"
    assert auth_client.post(url, json=payload).status_code == 405
    response = auth_client.put(url, json=payload)
    assert response.status_code == 200, response.text
    for key, value in payload.items():
        assert response.json()[key] == value


def test_删除流水返回204且无响应体(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    tid = post_transaction(auth_client, make_transaction_payload(account_id, category_id)).json()[
        "id"
    ]

    response = auth_client.delete(f"/api/transactions/{tid}")
    assert response.status_code == 204
    assert response.content == b""


def test_分类有流水时删除返回409(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    post_transaction(auth_client, make_transaction_payload(account_id, category_id))

    response = auth_client.delete(f"/api/categories/{category_id}")
    assert response.status_code == 409


def test_账户有流水时删除返回409(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    post_transaction(auth_client, make_transaction_payload(account_id, category_id))

    response = auth_client.delete(f"/api/accounts/{account_id}")
    assert response.status_code == 409


def test_用户之间不能互相访问流水(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    created = post_transaction(auth_client, make_transaction_payload(account_id, category_id))
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    with TestClient(app) as other:
        assert (
            other.post(
                "/api/auth/register",
                json={
                    "email": "other@example.com",
                    "password": "password123",
                    "nickname": "另一个人",
                },
            ).status_code
            == 200
        )

        assert (
            other.post(
                "/api/auth/login",
                json={
                    "email": "other@example.com",
                    "password": "password123",
                },
            ).status_code
            == 200
        )

        other_account_id = create_account(other, name="B的现金")
        other_category_id = create_category(other, name="B的餐饮")

        response = other.put(
            f"/api/transactions/{tid}",
            json=make_transaction_payload(other_account_id, other_category_id, money="999.00"),
        )

        assert response.status_code == 404

    listed = auth_client.get("/api/transactions").json()
    assert len(listed) == 1
    assert listed[0]["money"] == "10.00"


def test_summary返回三个金额字段(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    post_transaction(
        auth_client,
        make_transaction_payload(account_id, category_id, money="10.00"),
    )

    response = auth_client.get("/api/summary", params={"year": 2025, "month": 1})
    assert response.status_code == 200

    body = response.json()
    assert set(body.keys()) == {"money_in", "money_out", "money_sum"}
    assert body["money_out"] == "10.00"
    assert body["money_in"] == "0"


def test_重复提交只创建一条流水并返回原记录(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)
    payload = make_transaction_payload(account_id, category_id)

    first = post_transaction(auth_client, payload, key="repeat-key")
    second = post_transaction(auth_client, payload, key="repeat-key")

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.headers["Idempotent-Replayed"] == "true"
    assert first.json()["id"] == second.json()["id"]
    assert len(list_transactions(auth_client)) == 1


def test_同一个键不同请求体返回409(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    first = post_transaction(
        auth_client,
        make_transaction_payload(account_id, category_id, money="10.00"),
        key="conflict-key",
    )
    second = post_transaction(
        auth_client,
        make_transaction_payload(account_id, category_id, money="20.00"),
        key="conflict-key",
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    assert len(list_transactions(auth_client)) == 1


def test_创建失败时幂等键回滚(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)
    key = "rollback-key"

    failed = post_transaction(
        auth_client,
        make_transaction_payload(account_id, 999999),
        key=key,
    )

    assert failed.status_code == 404, failed.text

    retried = post_transaction(
        auth_client,
        make_transaction_payload(account_id, category_id),
        key=key,
    )

    assert retried.status_code == 201, retried.text
    assert len(list_transactions(auth_client)) == 1


def test_不同键相同请求体创建两条流水(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)
    payload = make_transaction_payload(account_id, category_id)

    first = post_transaction(auth_client, payload, key="first-key")
    second = post_transaction(auth_client, payload, key="second-key")

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]
    assert len(list_transactions(auth_client)) == 2


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Idempotency-Key": ""},
        {"Idempotency-Key": "x" * 201},
    ],
)
def test_幂等键缺失或非法返回422(auth_client, headers):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    response = auth_client.post(
        "/api/transactions",
        json=make_transaction_payload(account_id, category_id),
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert list_transactions(auth_client) == []


def test_幂等键按用户隔离(auth_client):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)
    payload = make_transaction_payload(account_id, category_id)
    key = "shared-key"

    first = post_transaction(auth_client, payload, key=key)
    assert first.status_code == 201, first.text

    with TestClient(app) as other:
        registered = other.post(
            "/api/auth/register",
            json={
                "email": "idempotency-other@example.com",
                "password": "password123",
                "nickname": "另一个用户",
            },
        )
        assert registered.status_code == 200, registered.text

        logged_in = other.post(
            "/api/auth/login",
            json={"email": "idempotency-other@example.com", "password": "password123"},
        )
        assert logged_in.status_code == 200, logged_in.text

        other_account_id = create_account(other, name="B的现金")
        other_category_id = create_category(other, name="B的餐饮")
        other_payload = make_transaction_payload(other_account_id, other_category_id)

        second = post_transaction(other, other_payload, key=key)

        assert second.status_code == 201, second.text
        assert second.json()["id"] != first.json()["id"]
        assert len(list_transactions(other)) == 1

    replay = post_transaction(auth_client, payload, key=key)

    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert len(list_transactions(auth_client)) == 1


def test_提交失败时客户端不收到成功(auth_client, monkeypatch):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)
    payload = make_transaction_payload(account_id, category_id)

    async def fail_commit(_session):
        raise RuntimeError("commit failed")

    monkeypatch.setattr(AsyncSession, "commit", fail_commit)

    with TestClient(app, raise_server_exceptions=False) as failing_client:
        failing_client.cookies.update(auth_client.cookies)
        response = post_transaction(failing_client, payload, key="commit-failure-key")

    assert response.status_code == 500, response.text

    monkeypatch.undo()

    assert list_transactions(auth_client) == []


def test_写接口只提交一次(auth_client, monkeypatch):
    account_id = create_account(auth_client)
    category_id = create_category(auth_client)

    original_commit = AsyncSession.commit
    calls = []

    async def counting_commit(session):
        calls.append(1)
        await original_commit(session)

    monkeypatch.setattr(AsyncSession, "commit", counting_commit)

    response = post_transaction(
        auth_client,
        make_transaction_payload(account_id, category_id),
    )

    assert response.status_code == 201
    assert len(calls) == 1


def test_读接口不提交(auth_client, monkeypatch):
    original_commit = AsyncSession.commit
    calls = []

    async def counting_commit(session):
        calls.append(1)
        await original_commit(session)

    monkeypatch.setattr(AsyncSession, "commit", counting_commit)

    response = auth_client.get("/api/transactions")

    assert response.status_code == 200
    assert calls == []


def test_创建账户提交失败不返回成功(auth_client, monkeypatch):
    async def fail_commit(_session):
        raise RuntimeError("commit failed")

    monkeypatch.setattr(AsyncSession, "commit", fail_commit)

    with TestClient(app, raise_server_exceptions=False) as failing_client:
        failing_client.cookies.update(auth_client.cookies)
        response = failing_client.post(
            "/api/accounts",
            json={"name_accounts": "失败账户"},
        )

    assert response.status_code == 500
