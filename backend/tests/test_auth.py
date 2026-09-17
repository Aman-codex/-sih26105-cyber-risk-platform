def test_login_success(client, seeded_admin):
    org, user = seeded_admin
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.example", "password": "TestAdmin@123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["user"]["email"] == "admin@test.example"
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client, seeded_admin):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.example", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, seeded_admin):
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.example", "password": "TestAdmin@123"},
    )
    token = login.json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.example"


def test_register_requires_admin_role(client, db_session, seeded_admin):
    from app.crud.user import create_user
    from app.models.user import UserRole

    org, admin = seeded_admin
    analyst = create_user(
        db_session,
        email="analyst@test.example",
        password="Analyst@123",
        role=UserRole.RISK_ANALYST,
        organization_id=org.id,
    )

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "analyst@test.example", "password": "Analyst@123"},
    )
    token = login.json()["access_token"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new@test.example", "password": "New@12345", "role": "risk_analyst"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_register_success_as_admin(client, seeded_admin):
    org, admin = seeded_admin
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.example", "password": "TestAdmin@123"},
    )
    token = login.json()["access_token"]

    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new@test.example", "password": "New@12345", "role": "ciso", "full_name": "New CISO"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "ciso"


def test_refresh_token_flow(client, seeded_admin):
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.example", "password": "TestAdmin@123"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
