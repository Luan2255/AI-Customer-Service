def test_health_returns_ok(client):
    """The health endpoint returns a successful liveness response."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_conversation_chat_and_history(client):
    """A chat turn is persisted and returned in chronological message order."""
    created = client.post("/conversations", json={})
    conversation_id = created.json()["id"]

    reply = client.post(
        "/chat",
        json={"conversation_id": conversation_id, "message": "Olá, preciso de ajuda"},
    )

    assert created.status_code == 201
    assert reply.status_code == 200
    assert reply.json()["intent"] == "suporte"
    assert reply.json()["human_required"] is False
    messages = client.get(f"/conversations/{conversation_id}/messages")
    assert [message["role"] for message in messages.json()] == ["user", "assistant"]


def test_explicit_human_request_is_escalated(client):
    """An explicit agent request activates a handoff that remains on the conversation."""
    conversation_id = client.post("/conversations", json={}).json()["id"]

    response = client.post(
        "/chat",
        json={"conversation_id": conversation_id, "message": "Quero falar com um atendente humano"},
    )

    assert response.status_code == 200
    assert response.json()["human_required"] is True
    assert response.json()["escalation_reason"]

    follow_up = client.post(
        "/chat",
        json={"conversation_id": conversation_id, "message": "Obrigado"},
    )
    assert follow_up.json()["human_required"] is True


def test_chat_rejects_unknown_conversation_and_empty_message(client):
    """Unknown conversation IDs and blank user input are rejected with client errors."""
    missing = client.post(
        "/chat",
        json={"conversation_id": "00000000-0000-0000-0000-000000000000", "message": "Olá"},
    )
    invalid = client.post(
        "/chat",
        json={"conversation_id": "00000000-0000-0000-0000-000000000000", "message": " "},
    )

    assert missing.status_code == 404
    assert invalid.status_code == 422