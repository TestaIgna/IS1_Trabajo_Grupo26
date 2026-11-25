from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.tag import Tag
from is1_trabajo_grupo26.services.ai_answer_service import (
    generate_ai_response_for_question,
)
from is1_trabajo_grupo26.services.strategy import Strategy


def _seed_base_entities(client):
    cat_sw = client.post("/api/categories", json={"name": "Ingeniería"}).get_json()
    cat_db = client.post("/api/categories", json={"name": "Bases de Datos"}).get_json()
    author = client.post(
        "/api/users",
        json={
            "name": "Matías",
            "email": "matias@grupo26.local",
            "password": "password123",
        },
    ).get_json()
    responder = client.post(
        "/api/users",
        json={
            "name": "Milena",
            "email": "milena@grupo26.local",
            "password": "password123",
        },
    ).get_json()
    return cat_sw, cat_db, author, responder


def test_questions_create_list_filter_detail_patch_and_delete(client):
    cat_sw, cat_db, author, _ = _seed_base_entities(client)

    q1_resp = client.post(
        "/api/questions",
        json={
            "title": "Duda sobre Flask Blueprints",
            "body": "¿Cómo organizar prefijos /api?",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tags": ["flask", "python"],
        },
    )
    assert q1_resp.status_code == 201
    q1 = q1_resp.get_json()
    assert q1["category"]["name"] == "Ingeniería"
    assert q1["author"]["name"] == "Matías"
    assert "password_hash" not in q1["author"]
    assert {t["title"] for t in q1["tags"]} == {"flask", "python"}
    assert q1["answers"] == []
    assert q1["score"] == 0

    q2_resp = client.post(
        "/api/questions",
        json={
            "title": "SQLite Foreign Keys",
            "body": "¿Por qué PRAGMA foreign_keys=ON?",
            "category_id": cat_db["id"],
            "author_id": author["id"],
            "tags": ["sqlite", "python"],
        },
    )
    assert q2_resp.status_code == 201
    q2 = q2_resp.get_json()

    all_q = client.get("/api/questions")
    assert all_q.status_code == 200
    assert [q["id"] for q in all_q.get_json()["questions"]] == [q1["id"], q2["id"]]

    by_cat_id = client.get(f"/api/questions?category_id={cat_db['id']}")
    assert [q["id"] for q in by_cat_id.get_json()["questions"]] == [q2["id"]]

    by_cat_name = client.get("/api/questions?category=ingeniería")
    assert [q["id"] for q in by_cat_name.get_json()["questions"]] == [q1["id"]]

    by_tag = client.get("/api/questions?tag=SQLITE")
    assert [q["id"] for q in by_tag.get_json()["questions"]] == [q2["id"]]

    flask_tag_id = next(t["id"] for t in q1["tags"] if t["title"] == "flask")
    by_tag_id = client.get(f"/api/questions?tag_id={flask_tag_id}")
    assert [q["id"] for q in by_tag_id.get_json()["questions"]] == [q1["id"]]

    bad_filter = client.get("/api/questions?category_id=abc")
    assert bad_filter.status_code == 422
    assert bad_filter.get_json()["code"] == "unprocessable_entity"

    detail = client.get(f"/api/questions/{q1['id']}")
    assert detail.status_code == 200
    assert detail.get_json()["id"] == q1["id"]

    patch_resp = client.patch(
        f"/api/questions/{q1['id']}",
        json={
            "title": "Duda actualizada sobre Blueprints",
            "category_id": cat_db["id"],
            "tags": ["flask", "arquitectura"],
        },
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.get_json()
    assert patched["title"] == "Duda actualizada sobre Blueprints"
    assert patched["category"]["id"] == cat_db["id"]
    assert {t["title"] for t in patched["tags"]} == {"flask", "arquitectura"}

    empty_patch = client.patch(f"/api/questions/{q1['id']}", json={})
    assert empty_patch.status_code == 422

    del_resp = client.delete(f"/api/questions/{q1['id']}")
    assert del_resp.status_code == 204
    assert client.get(f"/api/questions/{q1['id']}").status_code == 404


def test_questions_validation_and_missing_foreign_keys(client):
    cat_sw, _, author, _ = _seed_base_entities(client)

    missing_cat = client.post(
        "/api/questions",
        json={
            "title": "Sin categoría",
            "body": "Detalle",
            "category_id": 9999,
            "author_id": author["id"],
        },
    )
    assert missing_cat.status_code == 404

    missing_author = client.post(
        "/api/questions",
        json={
            "title": "Sin autor",
            "body": "Detalle",
            "category_id": cat_sw["id"],
            "author_id": 9999,
        },
    )
    assert missing_author.status_code == 404

    bad_tag_id = client.post(
        "/api/questions",
        json={
            "title": "Tag inexistente",
            "body": "Detalle",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tag_ids": [9999],
        },
    )
    assert bad_tag_id.status_code == 404

    bad_provider = client.post(
        "/api/questions",
        json={
            "title": "Proveedor malo",
            "body": "Detalle",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "ai_provider": "anthropic",
        },
    )
    assert bad_provider.status_code == 422


def test_answers_create_list_and_accept_lifecycle(client):
    cat_sw, _, author, responder = _seed_base_entities(client)

    q = client.post(
        "/api/questions",
        json={
            "title": "¿Cómo funciona accept?",
            "body": "Necesito marcar una única respuesta aceptada.",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
        },
    ).get_json()

    a1_resp = client.post(
        f"/api/questions/{q['id']}/answers",
        json={"body": "Primera respuesta", "author_id": responder["id"]},
    )
    assert a1_resp.status_code == 201
    a1 = a1_resp.get_json()
    assert a1["is_accepted"] is False

    a2 = client.post(
        f"/api/questions/{q['id']}/answers",
        json={"body": "Segunda respuesta", "author_id": responder["id"]},
    ).get_json()

    list_ans = client.get(f"/api/questions/{q['id']}/answers")
    assert list_ans.status_code == 200
    assert [a["id"] for a in list_ans.get_json()["answers"]] == [a1["id"], a2["id"]]

    forbidden = client.patch(
        f"/api/answers/{a1['id']}/accept",
        json={"author_id": responder["id"]},
    )
    assert forbidden.status_code == 403
    assert forbidden.get_json()["code"] == "forbidden"

    accept_1 = client.patch(
        f"/api/answers/{a1['id']}/accept",
        json={"author_id": author["id"]},
    )
    assert accept_1.status_code == 200
    assert accept_1.get_json()["is_accepted"] is True

    accept_2 = client.patch(f"/api/answers/{a2['id']}/accept")
    assert accept_2.status_code == 200
    assert accept_2.get_json()["is_accepted"] is True

    all_after = client.get(f"/api/questions/{q['id']}/answers").get_json()["answers"]
    assert [a["is_accepted"] for a in all_after] == [False, True]

    assert client.patch("/api/answers/9999/accept").status_code == 404
    assert client.get("/api/questions/9999/answers").status_code == 404


def test_question_creation_triggers_llm_strategy_only_for_ia_help(client):
    cat_sw, _, author, _ = _seed_base_entities(client)

    with_ia = client.post(
        "/api/questions",
        json={
            "title": "Duda con Strategy",
            "body": "¿Cómo se integra con Flask?",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tags": ["#ia-help", "python"],
        },
    )
    assert with_ia.status_code == 201
    q_ia = with_ia.get_json()
    assert len(q_ia["answers"]) == 1
    bot_answer = q_ia["answers"][0]
    assert bot_answer["author"]["role"] == "BOT"
    assert bot_answer["author"]["name"] == "Local Bot"
    assert "[Local] Respuesta para 'Duda con Strategy'" in bot_answer["body"]

    with_openai = client.post(
        "/api/questions",
        json={
            "title": "Duda con OpenAI",
            "body": "Probar selector",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tags": ["#IA-HELP"],
            "ai_provider": "openai",
        },
    )
    assert with_openai.status_code == 201
    assert with_openai.get_json()["answers"][0]["author"]["name"] == "OpenAI Bot"
    assert "[OpenAI]" in with_openai.get_json()["answers"][0]["body"]

    disabled_ia = client.post(
        "/api/questions",
        json={
            "title": "IA desactivada",
            "body": "Tiene el tag pero auto_answer_ai es false",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tags": ["#ia-help"],
            "auto_answer_ai": False,
        },
    )
    assert disabled_ia.status_code == 201
    assert disabled_ia.get_json()["answers"] == []


def test_ai_answer_service_supports_injected_and_failing_strategies(app, db_session):
    class FakeStrategy(Strategy):
        def createResponse(self, title: str, body: str) -> str:
            return f"FakeBot: {title} | {body}"

    class FailingStrategy(Strategy):
        def createResponse(self, title: str, body: str) -> str:
            raise RuntimeError("timeout LLM")

    cat = Category(name="Arquitectura")
    tag_ia = Tag(title="#ia-help")

    user = Author(
        name="Ignacio",
        email="ignacio@grupo26.local",
        password="password123",
        role=TipoRol.USERGRAL,
    )
    question = Question(
        title="¿Cómo probar IA?",
        body="Usando inyección de dependencias",
        category=cat,
        author=user,
        tags=[tag_ia],
    )
    db_session.add_all([cat, tag_ia, user, question])
    db_session.flush()

    resp_ok = generate_ai_response_for_question(
        question,
        strategy=FakeStrategy(),
        bot_name="FakeBot",
    )
    assert resp_ok is not None
    assert resp_ok.body == "FakeBot: ¿Cómo probar IA? | Usando inyección de dependencias"
    assert resp_ok.author.name == "FakeBot"

    resp_err = generate_ai_response_for_question(
        question,
        strategy=FailingStrategy(),
        bot_name="FailBot",
    )
    assert resp_err is not None
    assert "No se pudo generar la respuesta: timeout LLM" in resp_err.body
    db_session.commit()


def test_questions_api_enforces_title_and_tag_max_lengths(client):
    cat_sw, _, author, _ = _seed_base_entities(client)

    title_too_long = client.post(
        "/api/questions",
        json={
            "title": "a" * 201,
            "body": "Cuerpo válido",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
        },
    )
    assert title_too_long.status_code == 422
    assert title_too_long.get_json()["code"] == "unprocessable_entity"
    assert client.get("/api/questions").get_json()["questions"] == []

    tag_too_long = client.post(
        "/api/questions",
        json={
            "title": "Título válido",
            "body": "Cuerpo válido",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tags": ["python", "t" * 21],
        },
    )
    assert tag_too_long.status_code == 422
    assert tag_too_long.get_json()["code"] == "unprocessable_entity"
    assert client.get("/api/questions").get_json()["questions"] == []
    assert client.get("/api/tags").get_json()["tags"] == []

    boundary_ok = client.post(
        "/api/questions",
        json={
            "title": "b" * 200,
            "body": "Cuerpo válido en el límite",
            "category_id": cat_sw["id"],
            "author_id": author["id"],
            "tags": ["z" * 20],
        },
    )
    assert boundary_ok.status_code == 201
    created = boundary_ok.get_json()
    assert len(created["title"]) == 200
    assert [tag["title"] for tag in created["tags"]] == ["z" * 20]

    patch_bad_title = client.patch(
        f"/api/questions/{created['id']}",
        json={"title": "c" * 201},
    )
    assert patch_bad_title.status_code == 422

    patch_bad_tag = client.patch(
        f"/api/questions/{created['id']}",
        json={"tags": ["u" * 21]},
    )
    assert patch_bad_tag.status_code == 422

    still_intact = client.get(f"/api/questions/{created['id']}").get_json()
    assert still_intact["title"] == "b" * 200
    assert [tag["title"] for tag in still_intact["tags"]] == ["z" * 20]
