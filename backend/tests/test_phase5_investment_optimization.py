from app.crud.user import create_user
from app.models.user import UserRole


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_asset_with_partial_mitigation(client, token, name="Test Asset"):
    """Creates an asset with a critical vulnerability and NO controls, so
    there's plenty of headroom for candidate investments to matter."""
    resp = client.post(
        "/api/v1/assets",
        json={"name": name, "asset_type": "web_app", "business_criticality": "critical", "business_value": 10_000_000, "internet_exposure": True},
        headers=_auth(token),
    )
    asset = resp.json()
    client.post(
        "/api/v1/vulnerabilities",
        json={"title": "Critical bug", "cvss_score": 9.5, "exploitability": "actively_exploited", "affected_asset_ids": [asset["id"]]},
        headers=_auth(token),
    )
    return asset


def _create_inactive_control(client, token, name, cost, effectiveness):
    # Controls are created via a direct DB insert path in seed.py, but there's
    # no public "create inactive control" API — so tests use the seeded
    # inactive controls from conftest's fresh org instead. This helper is a
    # placeholder documenting that constraint.
    pass


def test_no_candidates_returns_400(client, seeded_admin):
    """A fresh org with no inactive controls has nothing to recommend."""
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset_with_partial_mitigation(client, token)

    resp = client.post("/api/v1/optimization/recommend", json={}, headers=_auth(token))
    assert resp.status_code == 400


def test_recommend_requires_write_role(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="exec@test.example", password="Exec@12345", role=UserRole.EXECUTIVE, organization_id=org.id)
    exec_token = _login(client, "exec@test.example", "Exec@12345")

    resp = client.post("/api/v1/optimization/recommend", json={}, headers=_auth(exec_token))
    assert resp.status_code == 403


def test_investments_list_empty_before_any_run(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.get("/api/v1/investments", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_recommendations_history_starts_empty(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.get("/api/v1/optimization/recommendations", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_full_optimization_flow_with_inactive_control(client, db_session, seeded_admin):
    """
    Full flow using a directly-inserted inactive control (bypassing the API
    since there's no public 'create inactive control' endpoint — controls
    are always created active in this phase; inactive candidates are a
    seed-data / future-phase concept). This verifies the optimizer picks it
    up, respects budget, and produces internally consistent numbers.
    """
    from app.models.security_control import SecurityControl
    from app.models.enums import ControlType

    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset_with_partial_mitigation(client, token)

    candidate = SecurityControl(
        organization_id=org.id, name="Candidate EDR", control_type=ControlType.EDR,
        annual_cost=100_000.0, effectiveness_score=0.40, is_active=False,
    )
    db_session.add(candidate)
    db_session.commit()

    resp = client.post("/api/v1/optimization/recommend", json={"budget": 500_000}, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["total_investment"] <= 500_000
    assert body["total_risk_reduction"] <= body["baseline_total_eal"]  # never exceeds baseline
    assert body["remaining_risk"] == round(body["baseline_total_eal"] - body["total_risk_reduction"], 2)
    assert len(body["selected_investments"]) == 1
    assert body["selected_investments"][0]["control_name"] == "Candidate EDR"


def test_zero_budget_selects_nothing(client, db_session, seeded_admin):
    from app.models.security_control import SecurityControl
    from app.models.enums import ControlType

    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset_with_partial_mitigation(client, token)

    candidate = SecurityControl(
        organization_id=org.id, name="Expensive Control", control_type=ControlType.EDR,
        annual_cost=1_000_000.0, effectiveness_score=0.40, is_active=False,
    )
    db_session.add(candidate)
    db_session.commit()

    resp = client.post("/api/v1/optimization/recommend", json={"budget": 0}, headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_investment"] == 0.0
    assert body["total_risk_reduction"] == 0.0
    assert body["selected_investments"] == []


def test_budget_constraint_excludes_unaffordable_candidates(client, db_session, seeded_admin):
    from app.models.security_control import SecurityControl
    from app.models.enums import ControlType

    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset_with_partial_mitigation(client, token)

    cheap = SecurityControl(organization_id=org.id, name="Cheap Control", control_type=ControlType.MFA, annual_cost=50_000.0, effectiveness_score=0.20, is_active=False)
    expensive = SecurityControl(organization_id=org.id, name="Expensive Control", control_type=ControlType.EDR, annual_cost=2_000_000.0, effectiveness_score=0.40, is_active=False)
    db_session.add_all([cheap, expensive])
    db_session.commit()

    resp = client.post("/api/v1/optimization/recommend", json={"budget": 100_000}, headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_investment"] <= 100_000
    selected_names = {s["control_name"] for s in body["selected_investments"]}
    assert "Expensive Control" not in selected_names


def test_defaults_to_org_annual_cyber_budget_when_omitted(client, db_session, seeded_admin):
    from app.models.security_control import SecurityControl
    from app.models.enums import ControlType

    org, admin = seeded_admin
    org.annual_cyber_budget = 75_000.0  # deliberately small
    db_session.commit()

    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset_with_partial_mitigation(client, token)

    candidate = SecurityControl(organization_id=org.id, name="Mid Control", control_type=ControlType.EDR, annual_cost=100_000.0, effectiveness_score=0.30, is_active=False)
    db_session.add(candidate)
    db_session.commit()

    resp = client.post("/api/v1/optimization/recommend", json={}, headers=_auth(token))  # no budget in payload
    assert resp.status_code == 200
    body = resp.json()
    assert body["budget"] == 75_000.0
    assert body["total_investment"] == 0.0  # too expensive for the small org budget


def test_recommendation_appears_in_history(client, db_session, seeded_admin):
    from app.models.security_control import SecurityControl
    from app.models.enums import ControlType

    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset_with_partial_mitigation(client, token)

    candidate = SecurityControl(organization_id=org.id, name="History Control", control_type=ControlType.EDR, annual_cost=50_000.0, effectiveness_score=0.30, is_active=False)
    db_session.add(candidate)
    db_session.commit()

    client.post("/api/v1/optimization/recommend", json={"budget": 100_000}, headers=_auth(token))

    resp = client.get("/api/v1/optimization/recommendations", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
