def _seed_voting_scenario(client):
    cat = client.post("/api/categories", json={"name": "Ingeniería"}).get_json()
    u1 = client.post(
        "/api/users",
        json={"name": "Matías", "email": "matias@grupo26.local", "password": "password123"},
    ).get_json()
    u2 = client.post(
        "/api/users",
        json={"name": "Milena", "email": "milena@grupo26.local", "password": "password123"},
    ).get_json()
    q = client.post(
        "/api/questions",
        json={
            "title": "¿Cómo funciona XOR en votos?",
            "body": "Validar pregunta o respuesta.",
            "category_id": cat["id"],
            "author_id": u1["id"],
        },
    ).get_json()
    ans = client.post(
        f"/api/questions/{q['id']}/answers",
        json={"body": "Con CheckConstraint y validación en API.", "author_id": u2["id"]},
    ).get_json()
    return u1, u2, q, ans


def test_votes_create_list_score_on_question_and_response(client):
    u1, u2, q, ans = _seed_voting_scenario(client)

    v_q_up = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "POSITIVE", "question_id": q["id"]},
    )
    assert v_q_up.status_code == 201
    v1 = v_q_up.get_json()
    assert v1["vote"] == "POSITIVE"
    assert v1["question_id"] == q["id"]
    assert v1["response_id"] is None
    assert v1["score"] == 1

    v_q_down = client.post(
        "/api/votes",
        json={"user_id": u2["id"], "vote": "NEGATIVO", "question_id": q["id"]},
    )
    assert v_q_down.status_code == 201
    v2 = v_q_down.get_json()
    assert v2["vote"] == "NEGATIVE"
    assert v2["score"] == 0

    v_a_up = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote_type": "POSITIVO", "response_id": ans["id"]},
    )
    assert v_a_up.status_code == 201
    va = v_a_up.get_json()
    assert va["vote"] == "POSITIVE"
    assert va["response_id"] == ans["id"]
    assert va["score"] == 1

    list_q = client.get(f"/api/votes?question_id={q['id']}")
    assert list_q.status_code == 200
    assert list_q.get_json()["score"] == 0
    assert len(list_q.get_json()["votes"]) == 2

    list_a = client.get(f"/api/votes?response_id={ans['id']}")
    assert list_a.status_code == 200
    assert list_a.get_json()["score"] == 1

    detail_q = client.get(f"/api/questions/{q['id']}").get_json()
    assert detail_q["score"] == 0
    assert detail_q["answers"][0]["score"] == 1


def test_votes_patch_and_delete_update_score(client):
    u1, u2, q, _ = _seed_voting_scenario(client)

    created = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "POSITIVE", "question_id": q["id"]},
    ).get_json()
    assert created["score"] == 1

    forbidden_patch = client.patch(
        f"/api/votes/{created['id']}",
        json={"user_id": u2["id"], "vote": "NEGATIVE"},
    )
    assert forbidden_patch.status_code == 403
    assert forbidden_patch.get_json()["code"] == "forbidden"

    changed = client.patch(
        f"/api/votes/{created['id']}",
        json={"user_id": u1["id"], "vote": "NEGATIVE"},
    )
    assert changed.status_code == 200
    assert changed.get_json()["vote"] == "NEGATIVE"
    assert changed.get_json()["score"] == -1

    bad_reassign = client.patch(
        f"/api/votes/{created['id']}",
        json={"vote": "POSITIVE", "question_id": q["id"], "response_id": 1},
    )
    assert bad_reassign.status_code == 400

    forbidden_del = client.delete(f"/api/votes/{created['id']}?user_id={u2['id']}")
    assert forbidden_del.status_code == 403

    deleted = client.delete(f"/api/votes/{created['id']}?user_id={u1['id']}")
    assert deleted.status_code == 200
    assert deleted.get_json() == {
        "deleted": True,
        "vote_id": created["id"],
        "question_id": q["id"],
        "response_id": None,
        "score": 0,
    }

    assert client.get(f"/api/votes/{created['id']}").status_code == 404
    assert client.patch(f"/api/votes/{created['id']}", json={"vote": "POSITIVE"}).status_code == 404
    assert client.delete(f"/api/votes/{created['id']}").status_code == 404


def test_votes_xor_rule_duplicates_and_validation(client):
    u1, _, q, ans = _seed_voting_scenario(client)

    both = client.post(
        "/api/votes",
        json={
            "user_id": u1["id"],
            "vote": "POSITIVE",
            "question_id": q["id"],
            "response_id": ans["id"],
        },
    )
    assert both.status_code == 400
    assert both.get_json()["code"] == "bad_request"

    neither = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "POSITIVE"},
    )
    assert neither.status_code == 400
    assert neither.get_json()["code"] == "bad_request"

    list_both = client.get(f"/api/votes?question_id={q['id']}&response_id={ans['id']}")
    assert list_both.status_code == 400

    first = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "POSITIVE", "question_id": q["id"]},
    )
    assert first.status_code == 201
    vote_id = first.get_json()["id"]

    dup = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "NEGATIVE", "question_id": q["id"]},
    )
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "conflict"
    assert dup.get_json()["details"] == {"vote_id": vote_id}

    bad_type = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "NEUTRAL", "response_id": ans["id"]},
    )
    assert bad_type.status_code == 422

    missing_user = client.post(
        "/api/votes",
        json={"user_id": 9999, "vote": "POSITIVE", "question_id": q["id"]},
    )
    assert missing_user.status_code == 404

    missing_question = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "POSITIVE", "question_id": 9999},
    )
    assert missing_question.status_code == 404

    missing_response = client.post(
        "/api/votes",
        json={"user_id": u1["id"], "vote": "POSITIVE", "response_id": 9999},
    )
    assert missing_response.status_code == 404
