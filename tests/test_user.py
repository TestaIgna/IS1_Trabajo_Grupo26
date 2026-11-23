import pytest

def test_registro_user_valido(client):
    response = client.post(
        "/users/registro",
        data = {
            "nombre":"Bruno Diaz",
            "email":"bruno@ejemplo.com",
            "password":"password123"
        }
    )

    assert response.status_code == 302

def test_registro_password_corta(client):
    response = client.post(
        "/users/registro",
        data = {
            "nombre":"Matias Lopez",
            "email":"matilopez@gmail.com",
            "password":"123",
        }
    )
    assert response.status_code == 200
    assert "8" in response.get_data(as_text = True) 


def test_registro_campos_vacios(client):
    response = client.post(
        "/users/registro",
        data = {
            "nombre":"",
            "email":"",
            "password":""
        }
    )

    assert response.status_code == 200
    assert "required" in response.get_data(as_text = True)

def test_registro_email_invalid(client):
    response = client.post(
        "/users/registro",
        data = {
            "nombre":"Ana Ruiz",
            "email":"ana@gmail",
            "password":"pswrd347"
        }
    )

    assert response.status_code == 200
    assert "not valid" in response.get_data(as_text = True)

def test_registro_email_dup(client):
    payload = {
        "nombre":"Juan Perez",
        "email":"duplicado@ejemplo.com",
        "password":"passwrd487"
        }
    
    response_1 = client.post("/users/registro", data = payload)
    assert response_1.status_code == 302

    response_2 = client.post(
        "/users/registro",
        data = {
            "nombre":"Diaz Gutierrez",
            "email":"duplicado@ejemplo.com",
            "password":"password764"
        }
    )

    assert response_2.status_code == 200
    assert "already" in response_2.get_data(as_text= True)
