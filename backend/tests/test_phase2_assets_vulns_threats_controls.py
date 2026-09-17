from app.crud.user import create_user
from app.models.user import UserRole


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_analyst_can_create_asset(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="analyst@test.example", password="Analyst@123", role=UserRole.RISK_ANALYST, organization_id=org.id)
    token = _login(client, "analyst@test.example", "Analyst@123")

    resp = client.post(
        "/api/v1/assets",
        json={
            "name": "Online Banking Portal",
            "asset_type": "web_app",
            "business_criticality": "critical",
            "business_value": 50_000_000,
            "internet_exposure": True,
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Online Banking Portal"
    assert body["organization_id"] == org.id


def test_executive_cannot_create_asset(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="exec@test.example", password="Exec@12345", role=UserRole.EXECUTIVE, organization_id=org.id)
    token = _login(client, "exec@test.example", "Exec@12345")

    resp = client.post(
        "/api/v1/assets",
        json={"name": "Should Fail", "asset_type": "server"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 403


def test_executive_can_read_assets(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="exec2@test.example", password="Exec@12345", role=UserRole.EXECUTIVE, organization_id=org.id)
    admin_token = _login(client, "admin@test.example", "TestAdmin@123")
    client.post("/api/v1/assets", json={"name": "Asset A", "asset_type": "server"}, headers=_auth_headers(admin_token))

    exec_token = _login(client, "exec2@test.example", "Exec@12345")
    resp = client.get("/api/v1/assets", headers=_auth_headers(exec_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_asset_dependency_mapping(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    db_resp = client.post("/api/v1/assets", json={"name": "Core DB", "asset_type": "database"}, headers=_auth_headers(token))
    db_id = db_resp.json()["id"]

    app_resp = client.post(
        "/api/v1/assets",
        json={"name": "Web App", "asset_type": "web_app", "depends_on_ids": [db_id]},
        headers=_auth_headers(token),
    )
    assert app_resp.status_code == 201
    assert app_resp.json()["depends_on_ids"] == [db_id]


def test_create_vulnerability_auto_derives_severity(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    asset_resp = client.post("/api/v1/assets", json={"name": "Target App", "asset_type": "web_app"}, headers=_auth_headers(token))
    asset_id = asset_resp.json()["id"]

    resp = client.post(
        "/api/v1/vulnerabilities",
        json={"title": "Critical RCE", "cvss_score": 9.9, "affected_asset_ids": [asset_id]},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["severity"] == "critical"  # auto-derived from cvss_score, not explicitly passed
    assert body["affected_asset_ids"] == [asset_id]


def test_threat_event_requires_valid_threat(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.post(
        "/api/v1/threats/events",
        json={"threat_id": 9999, "event_type": "active_exploitation_detected"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 404


def test_threat_and_event_flow(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    asset_resp = client.post("/api/v1/assets", json={"name": "Portal", "asset_type": "web_app"}, headers=_auth_headers(token))
    asset_id = asset_resp.json()["id"]

    threat_resp = client.post(
        "/api/v1/threats",
        json={
            "name": "APT-Test",
            "mitre_technique_id": "T1190",
            "relevant_assets": [{"asset_id": asset_id, "relevance_score": 0.8}],
        },
        headers=_auth_headers(token),
    )
    assert threat_resp.status_code == 201, threat_resp.text
    threat_id = threat_resp.json()["id"]
    assert threat_resp.json()["relevant_asset_ids"] == [asset_id]

    event_resp = client.post(
        "/api/v1/threats/events",
        json={"threat_id": threat_id, "asset_id": asset_id, "event_type": "active_exploitation_detected", "severity": "critical"},
        headers=_auth_headers(token),
    )
    assert event_resp.status_code == 201
    assert event_resp.json()["severity"] == "critical"


def test_control_with_asset_coverage(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    asset_resp = client.post("/api/v1/assets", json={"name": "Portal", "asset_type": "web_app"}, headers=_auth_headers(token))
    asset_id = asset_resp.json()["id"]

    resp = client.post(
        "/api/v1/controls",
        json={
            "name": "MFA",
            "control_type": "mfa",
            "annual_cost": 200000,
            "effectiveness_score": 0.35,
            "protected_assets": [{"asset_id": asset_id, "coverage_percentage": 100}],
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["protected_asset_ids"] == [asset_id]


def test_delete_asset_requires_admin_or_ciso(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="analyst2@test.example", password="Analyst@123", role=UserRole.RISK_ANALYST, organization_id=org.id)
    analyst_token = _login(client, "analyst2@test.example", "Analyst@123")

    asset_resp = client.post("/api/v1/assets", json={"name": "Temp", "asset_type": "server"}, headers=_auth_headers(analyst_token))
    asset_id = asset_resp.json()["id"]

    # Risk analyst can create but not delete
    del_resp = client.delete(f"/api/v1/assets/{asset_id}", headers=_auth_headers(analyst_token))
    assert del_resp.status_code == 403

    admin_token = _login(client, "admin@test.example", "TestAdmin@123")
    del_resp = client.delete(f"/api/v1/assets/{asset_id}", headers=_auth_headers(admin_token))
    assert del_resp.status_code == 204
