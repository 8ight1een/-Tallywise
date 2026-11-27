import json
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx2 as httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import HttpUrl, SecretStr

import ai_drafts
from ai_config import AISettings
from auth import get_current_user
from database import get_session
from routers import ai

ENTRY = {
    "account_id": 1,
    "category_id": 2,
    "money": "8.00",
    "money_type": "支出",
    "description": "早餐",
    "transaction_date": "2026-11-19",
    "question": None,
}
BATCH = "/api/ai/transaction-drafts"
SINGLE = "/api/ai/transaction-draft"


def batch_output(drafts, *, warnings=(), too_many=False):
    return {"drafts": drafts, "warnings": list(warnings), "too_many": too_many}


@pytest.fixture
def post_drafts(monkeypatch):
    app = FastAPI()
    app.include_router(ai.router)
    settings = AISettings(
        enabled=True,
        api_key=SecretStr("test-only"),
        model="test-model",
        output_mode="json_object",
        token_field="max_tokens",
    )
    monkeypatch.setattr(ai, "ai_settings", settings)
    monkeypatch.setattr(ai_drafts, "gate", ai_drafts.LocalGate())
    account = SimpleNamespace(id=1, name_accounts="微信")
    category = SimpleNamespace(id=2, name_categories="餐饮", money_type="支出")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=42)

    def post(
        output,
        *,
        path=BATCH,
        text="昨天微信早饭8元",
        finish="stop",
        mode="json_object",
        base_url="https://api.deepseek.com/v1",
        effort="none",
    ):
        db = AsyncMock()
        results = []
        for row in (account, category):
            result = Mock()
            result.scalars.return_value.all.return_value = [row]
            results.append(result)
        db.execute.side_effect = results
        app.dependency_overrides[get_session] = lambda: db
        settings.output_mode = mode
        settings.base_url = HttpUrl(base_url)
        settings.reasoning_effort = effort
        requests = []

        def provider(request):
            body = json.loads(request.content)
            requests.append(body)
            assert json.loads(body["messages"][1]["content"])["text"] == text
            assert body["response_format"]["type"] == mode
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"finish_reason": finish, "message": {"content": json.dumps(output)}}
                    ]
                },
            )

        generate = partial(ai_drafts.generate_draft, transport=httpx.MockTransport(provider))
        monkeypatch.setattr(ai, "generate_draft", generate)
        with TestClient(app) as client:
            response = client.post(path, json={"text": text, "reference_date": "2026-11-20"})
        db.commit.assert_not_awaited()
        return response, requests

    return post


@pytest.mark.parametrize("path", [SINGLE, BATCH])
def test_deepseek_disables_thinking_for_drafts(post_drafts, path):
    output = batch_output([ENTRY]) if path == BATCH else {**ENTRY, "single_transaction": True}
    response, [body] = post_drafts(output, path=path)
    assert response.status_code == 200
    assert body["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in body


def test_explicit_thinking_effort(post_drafts):
    _, [body] = post_drafts(batch_output([]), effort="low")
    assert body["thinking"] == {"type": "enabled"}
    assert body["reasoning_effort"] == "low"


def test_other_providers_keep_compatible_request(post_drafts):
    _, [body] = post_drafts(batch_output([]), base_url="https://example.test/v1")
    assert "thinking" not in body
    assert "reasoning_effort" not in body


@pytest.mark.parametrize("mode", ["json_object", "json_schema"])
def test_batch_reviews_each_draft_in_order(post_drafts, mode):
    lunch = {**ENTRY, "description": "午饭", "money": "18"}
    milk_tea = {**ENTRY, "description": "奶茶", "money": None}
    response, calls = post_drafts(
        batch_output([ENTRY, lunch, milk_tea], warnings=["已跳过账户间转账"]),
        text="昨天微信早饭8元，午饭18元，共26元。买奶茶忘了金额，又从微信转了100元到银行卡。",
        mode=mode,
    )
    assert response.status_code == 200
    assert len(calls) == 1
    body = response.json()
    assert body["warnings"] == ["已跳过账户间转账"]
    drafts = body["drafts"]
    assert [item["status"] for item in drafts] == ["ready", "ready", "needs_input"]
    assert [item["fields"]["description"] for item in drafts] == ["早餐", "午饭", "奶茶"]
    assert drafts[0]["transaction"]["money"] == "8.00"
    assert drafts[2]["transaction"] is None and drafts[2]["issues"]


@pytest.mark.parametrize("count", [0, 1, 10])
def test_batch_sizes_and_text_limit(post_drafts, count):
    response, calls = post_drafts(batch_output([ENTRY] * count), text="账" * 1500)
    assert response.status_code == 200
    assert len(response.json()["drafts"]) == count
    assert len(calls) == 1


@pytest.mark.parametrize(("path", "length"), [(BATCH, 1501), (SINGLE, 501)])
def test_oversized_input_skips_provider(post_drafts, path, length):
    response, calls = post_drafts({}, path=path, text="账" * length)
    assert response.status_code == 422
    assert not calls


@pytest.mark.parametrize(
    ("output", "finish", "status", "code"),
    [
        (batch_output([], too_many=True), "stop", 422, "ai_too_many_drafts"),
        (batch_output([ENTRY] * 11), "stop", 422, "ai_too_many_drafts"),
        (batch_output([ENTRY]), "length", 502, "ai_incomplete"),
        ({"drafts": "invalid"}, "stop", 502, "ai_invalid_output"),
    ],
)
def test_no_partial_success(post_drafts, output, finish, status, code):
    response, _ = post_drafts(output, finish=finish)
    assert response.status_code == status
    assert response.json()["detail"]["code"] == code


@pytest.mark.parametrize("single", [True, False])
def test_legacy_response(post_drafts, single):
    response, _ = post_drafts({**ENTRY, "single_transaction": single}, path=SINGLE)
    assert response.status_code == 200
    body = response.json()
    assert body["fields"]["single_transaction"] is single
    assert body["status"] == ("ready" if single else "needs_input")
