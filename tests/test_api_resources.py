from is1_trabajo_grupo26 import create_app
from is1_trabajo_grupo26.config import TestingConfig
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author_model import Author


def test_categories_crud_list_get_create_and_conflicts(client):
    empty_resp = client.get("/api/categories")
    assert empty_resp.status_code == 200
    assert empty_resp.get_json() == {"categories": []}

    created = client.post("/api/categories", json={"name": "  Ingeniería de Software  "})
    assert created.status_code == 201
    cat = created.get_json()
    assert cat["id"] >= 1
    assert cat["name"] == "Ingeniería de Software"

    list_resp = client.get("/api/categories")
    assert list_resp.status_code == 200
    assert list_resp.get_json() == {"categories": [cat]}

    detail_resp = client.get(f"/api/categories/{cat['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json() == cat

    not_found = client.get("/api/categories/9999")
    assert not_found.status_code == 404
    assert not_found.get_json()["code"] == "not_found"

    dup_exact = client.post("/api/categories", json={"name": "Ingeniería de Software"})
    assert dup_exact.status_code == 409
    assert dup_exact.get_json()["code"] == "conflict"

    dup_case = client.post("/api/categories", json={"name": "ingeniería de software"})
    assert dup_case.status_code == 409
    assert dup_case.get_json()["code"] == "conflict"

    invalid = client.post("/api/categories", json={"name": "   "})
    assert invalid.status_code == 422
    assert invalid.get_json()["code"] == "unprocessable_entity"

    bad_json = client.post(
        "/api/categories",
        data="{invalido",
        content_type="application/json",
    )
    assert bad_json.status_code == 400
    assert bad_json.get_json()["code"] == "bad_request"


def test_tags_crud_list_get_create_and_conflicts(client):
    empty_resp = client.get("/api/tags")
    assert empty_resp.status_code == 200
    assert empty_resp.get_json() == {"tags": []}

    created = client.post("/api/tags", json={"title": " #ia-help "})
    assert created.status_code == 201
    tag = created.get_json()
    assert tag["id"] >= 1
    assert tag["title"] == "#ia-help"

    list_resp = client.get("/api/tags")
    assert list_resp.status_code == 200
    assert list_resp.get_json() == {"tags": [tag]}

    detail_resp = client.get(f"/api/tags/{tag['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json() == tag

    not_found = client.get("/api/tags/9999")
    assert not_found.status_code == 404
    assert not_found.get_json()["code"] == "not_found"

    dup = client.post("/api/tags", json={"title": "#IA-HELP"})
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "conflict"

    too_long = client.post("/api/tags", json={"title": "x" * 61})
    assert too_long.status_code == 422
    assert too_long.get_json()["code"] == "unprocessable_entity"


def test_users_crud_never_exposes_credentials_and_validates_roles(client, db_session):
    empty_resp = client.get("/api/users")
    assert empty_resp.status_code == 200
    assert empty_resp.get_json() == {"users": []}

    human_resp = client.post(
        "/api/users",
        json={
            "name": "Matías",
            "email": "MATIAS@Grupo26.local",
            "password": "password123",
        },
    )
    assert human_resp.status_code == 201
    human = human_resp.get_json()
    assert human == {
        "id": human["id"],
        "name": "Matías",
        "email": "matias@grupo26.local",
        "role": "USERGRAL",
    }
    assert "password" not in human
    assert "password_hash" not in human

    admin_resp = client.post(
        "/api/users",
        json={
            "name": "Brisa",
            "email": "brisa@grupo26.local",
            "password": "adminpassword",
            "role": "admin",
        },
    )
    assert admin_resp.status_code == 201
    assert admin_resp.get_json()["role"] == "ADMIN"

    bot_resp = client.post(
        "/api/users",
        json={"name": "GeminiBot", "role": "BOT"},
    )
    assert bot_resp.status_code == 201
    bot = bot_resp.get_json()
    assert bot["role"] == "BOT"
    assert bot["email"] is None
    assert "password" not in bot
    assert "password_hash" not in bot

    stored_human = db_session.get(Author, human["id"])
    assert stored_human is not None
    assert stored_human.check_password("password123") is True

    list_resp = client.get("/api/users")
    assert list_resp.status_code == 200
    users_list = list_resp.get_json()["users"]
    assert len(users_list) == 3
    for item in users_list:
        assert "password" not in item
        assert "password_hash" not in item

    bots_only = client.get("/api/users?role=BOT")
    assert bots_only.status_code == 200
    assert [u["name"] for u in bots_only.get_json()["users"]] == ["GeminiBot"]

    bad_role_filter = client.get("/api/users?role=SUPERUSER")
    assert bad_role_filter.status_code == 422
    assert bad_role_filter.get_json()["code"] == "unprocessable_entity"

    detail_resp = client.get(f"/api/users/{human['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json() == human

    not_found = client.get("/api/users/9999")
    assert not_found.status_code == 404
    assert not_found.get_json()["code"] == "not_found"


def test_users_post_rejects_duplicates_and_invalid_payloads(client):
    first = client.post(
        "/api/users",
        json={
            "name": "Milena",
            "email": "milena@grupo26.local",
            "password": "password123",
        },
    )
    assert first.status_code == 201

    dup = client.post(
        "/api/users",
        json={
            "name": "Otra",
            "email": "MILENA@grupo26.local",
            "password": "password123",
        },
    )
    assert dup.status_code == 409
    assert dup.get_json()["code"] == "conflict"

    bad_email = client.post(
        "/api/users",
        json={"name": "Ale", "email": "ale-invalido", "password": "password123"},
    )
    assert bad_email.status_code == 422
    assert bad_email.get_json()["code"] == "unprocessable_entity"

    short_pw = client.post(
        "/api/users",
        json={"name": "Ale", "email": "ale@grupo26.local", "password": "123"},
    )
    assert short_pw.status_code == 422
    assert short_pw.get_json()["code"] == "unprocessable_entity"

    bad_role = client.post(
        "/api/users",
        json={
            "name": "Ale",
            "email": "ale@grupo26.local",
            "password": "password123",
            "role": "MODERATOR",
        },
    )
    assert bad_role.status_code == 422
    assert bad_role.get_json()["code"] == "unprocessable_entity"


def test_multiple_create_app_calls_mount_resource_sub_blueprints():
    app_one = create_app(TestingConfig)
    app_two = create_app(TestingConfig)

    with app_one.app_context():
        db.create_all()
        assert app_one.test_client().get("/api/categories").status_code == 200
        assert app_one.test_client().get("/api/tags").status_code == 200
        assert app_one.test_client().get("/api/users").status_code == 200

    with app_two.app_context():
        db.create_all()
        assert app_two.test_client().get("/api/categories").status_code == 200
        assert app_two.test_client().get("/api/tags").status_code == 200
        assert app_two.test_client().get("/api/users").status_code == 200
