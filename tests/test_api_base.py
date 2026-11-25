import pytest

from is1_trabajo_grupo26 import create_app
from is1_trabajo_grupo26.api import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
    get_json_body,
    require_fields,
    require_int,
    require_non_empty_string,
    require_string_list,
)
from is1_trabajo_grupo26.config import TestingConfig


def test_api_base_route_and_health_registered(client):
    api_resp = client.get("/api")
    assert api_resp.status_code == 200
    assert api_resp.is_json
    assert api_resp.get_json() == {"status": "ok", "api": "v1"}

    api_slash_resp = client.get("/api/")
    assert api_slash_resp.status_code == 200
    assert api_slash_resp.get_json() == {"status": "ok", "api": "v1"}

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.get_json() == {"status": "ok"}


def test_create_app_can_register_api_multiple_times():
    app_one = create_app(TestingConfig)
    app_two = create_app(TestingConfig)

    assert "api" in app_one.blueprints
    assert "api" in app_two.blueprints
    assert "health" in app_one.blueprints
    assert "health" in app_two.blueprints


def test_api_http_errors_return_uniform_json(client):
    not_found_resp = client.get("/api/recurso-inexistente")
    assert not_found_resp.status_code == 404
    assert not_found_resp.is_json
    assert not_found_resp.get_json() == {
        "error": "Recurso no encontrado.",
        "code": "not_found",
        "status": 404,
    }

    method_resp = client.delete("/api")
    assert method_resp.status_code == 405
    assert method_resp.is_json
    assert method_resp.get_json() == {
        "error": "Método HTTP no permitido.",
        "code": "method_not_allowed",
        "status": 405,
    }


def test_non_api_404_does_not_force_json_response(client):
    web_404 = client.get("/ruta-web-inexistente")
    assert web_404.status_code == 404
    assert not web_404.is_json


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_code"),
    [
        (BadRequestError("Cuerpo inválido."), 400, "bad_request"),
        (NotFoundError("No existe la categoría."), 404, "not_found"),
        (ConflictError("La categoría ya existe."), 409, "conflict"),
        (
            ValidationError("Datos inválidos.", details={"title": "Obligatorio"}),
            422,
            "unprocessable_entity",
        ),
    ],
)
def test_api_error_subclasses_serialize_uniformly(exc, expected_status, expected_code):
    app = create_app(TestingConfig)

    @app.get("/api/_test-error")
    def raise_controlled_error():
        raise exc

    resp = app.test_client().get("/api/_test-error")
    assert resp.status_code == expected_status
    assert resp.is_json
    body = resp.get_json()
    assert body["error"] == exc.message
    assert body["code"] == expected_code
    assert body["status"] == expected_status
    if exc.details is not None:
        assert body["details"] == exc.details


def test_api_unexpected_exception_returns_500_json_without_leaking_trace():
    app = create_app(TestingConfig)
    app.testing = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/api/_test-error-500")
    def raise_unexpected():
        raise RuntimeError("detalle interno sensible")

    resp = app.test_client().get("/api/_test-error-500")
    assert resp.status_code == 500
    assert resp.is_json
    assert resp.get_json() == {
        "error": "Error interno del servidor.",
        "code": "internal_server_error",
        "status": 500,
    }
    assert "detalle interno sensible" not in resp.get_data(as_text=True)


def test_get_json_body_validation_via_http():
    app = create_app(TestingConfig)

    @app.post("/api/_test-json")
    def parse_json():
        data = get_json_body()
        return {"received": data}, 200

    client = app.test_client()

    no_ct = client.post("/api/_test-json", data='{"a": 1}')
    assert no_ct.status_code == 400
    assert no_ct.get_json()["code"] == "bad_request"

    broken = client.post(
        "/api/_test-json",
        data="{malformed",
        content_type="application/json",
    )
    assert broken.status_code == 400
    assert broken.get_json()["code"] == "bad_request"

    not_obj = client.post("/api/_test-json", json=["uno", "dos"])
    assert not_obj.status_code == 400
    assert not_obj.get_json()["code"] == "bad_request"

    valid = client.post("/api/_test-json", json={"nombre": "Flask"})
    assert valid.status_code == 200
    assert valid.get_json() == {"received": {"nombre": "Flask"}}


def test_validation_helpers_accept_valid_inputs_and_raise_422_on_invalid():
    require_fields({"title": "Hola", "body": "Mundo"}, ["title", "body"])
    with pytest.raises(ValidationError) as exc_missing:
        require_fields({"title": "Hola", "body": None}, ["title", "body", "author_id"])
    assert exc_missing.value.status_code == 422
    assert exc_missing.value.details == {"missing_fields": ["body", "author_id"]}

    assert require_non_empty_string({"title": "  Flask  "}, "title", max_length=20) == "Flask"
    with pytest.raises(ValidationError):
        require_non_empty_string({"title": "   "}, "title")
    with pytest.raises(ValidationError):
        require_non_empty_string({"title": "abcdef"}, "title", max_length=3)

    assert require_int({"category_id": 5}, "category_id", positive=True) == 5
    assert require_int({}, "category_id", optional=True) is None
    with pytest.raises(ValidationError):
        require_int({"category_id": True}, "category_id")
    with pytest.raises(ValidationError):
        require_int({"category_id": 0}, "category_id", positive=True)
    with pytest.raises(ValidationError):
        require_int({"category_id": "5"}, "category_id")

    assert require_string_list({"tags": [" #ia-help ", "python"]}, "tags") == [
        "#ia-help",
        "python",
    ]
    assert require_string_list({}, "tags", optional=True) == []
    with pytest.raises(ValidationError):
        require_string_list({"tags": "python"}, "tags")
    with pytest.raises(ValidationError):
        require_string_list({"tags": ["python", "   "]}, "tags")
