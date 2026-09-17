from app.crud.user import create_user
from app.models.user import UserRole


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_asset(client, token, **overrides):
    payload = {"name": "Test Asset", "asset_type": "web_app", "business_criticality": "critical", "business_value": 10_000_000, "internet_exposure": True}
    payload.update(overrides)
    resp = client.post("/api/v1/assets", json=payload, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_risk_config_has_sane_defaults(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.get("/api/v1/risks/config", headers=_auth(token))
    assert resp.status_code == 200
    params = resp.json()["parameters"]
    assert params["exploitability_likelihood"]["actively_exploited"] > params["exploitability_likelihood"]["theoretical"]
    assert params["criticality_multiplier"]["critical"] > params["criticality_multiplier"]["low"]
    assert sum(params["financial_impact_weights"].values()) <= 1.01  # roughly sums to 1.0


def test_only_admin_ciso_can_update_config(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="analyst@test.example", password="Analyst@123", role=UserRole.RISK_ANALYST, organization_id=org.id)
    analyst_token = _login(client, "analyst@test.example", "Analyst@123")

    resp = client.put("/api/v1/risks/config", json={"parameters": {"internet_exposure_multiplier": 2.0}}, headers=_auth(analyst_token))
    assert resp.status_code == 403

    admin_token = _login(client, "admin@test.example", "TestAdmin@123")
    resp = client.put("/api/v1/risks/config", json={"parameters": {"internet_exposure_multiplier": 2.0}}, headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["parameters"]["internet_exposure_multiplier"] == 2.0
    # untouched keys should survive the partial merge
    assert "exploitability_likelihood" in resp.json()["parameters"]


def test_recalculate_creates_risk_with_no_vulnerabilities(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    asset = _create_asset(client, token, internet_exposure=False)

    resp = client.post(f"/api/v1/risks/recalculate?asset_id={asset['id']}", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    risk = resp.json()[0]
    assert risk["asset_id"] == asset["id"]
    assert 0.0 < risk["likelihood"] <= 0.95
    assert risk["financial_impact_given_incident"] > 0
    assert risk["primary_vulnerability_id"] is None  # no vulns attached


def test_critical_actively_exploited_vuln_raises_risk_sharply(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")

    safe_asset = _create_asset(client, token, name="Safe Asset", internet_exposure=False)
    exposed_asset = _create_asset(client, token, name="Exposed Asset", internet_exposure=True)

    vuln_resp = client.post(
        "/api/v1/vulnerabilities",
        json={
            "title": "Critical RCE", "cvss_score": 9.8, "exploitability": "actively_exploited",
            "affected_asset_ids": [exposed_asset["id"]],
        },
        headers=_auth(token),
    )
    assert vuln_resp.status_code == 201

    client.post(f"/api/v1/risks/recalculate?asset_id={safe_asset['id']}", headers=_auth(token))
    client.post(f"/api/v1/risks/recalculate?asset_id={exposed_asset['id']}", headers=_auth(token))

    safe_risk = client.get(f"/api/v1/risks/{safe_asset['id']}", headers=_auth(token)).json()
    exposed_risk = client.get(f"/api/v1/risks/{exposed_asset['id']}", headers=_auth(token)).json()

    assert exposed_risk["risk_score"] > safe_risk["risk_score"]
    assert exposed_risk["expected_annual_loss"] > safe_risk["expected_annual_loss"]
    assert exposed_risk["primary_vulnerability_id"] is not None
    assert len(exposed_risk["risk_drivers"]) > 0
    assert any(d["factor"].startswith("Internet exposure") for d in exposed_risk["risk_drivers"])


def test_financial_impact_breakdown_sums_to_total(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    asset = _create_asset(client, token, business_value=1_000_000)

    client.post(f"/api/v1/risks/recalculate?asset_id={asset['id']}", headers=_auth(token))
    risk = client.get(f"/api/v1/risks/{asset['id']}", headers=_auth(token)).json()

    fi = risk["financial_impact"]
    component_sum = (
        fi["business_interruption"] + fi["data_loss"] + fi["recovery_cost"]
        + fi["incident_response"] + fi["legal_regulatory"] + fi["revenue_impact"] + fi["other_cost"]
    )
    assert abs(component_sum - fi["total_impact"]) < 0.01
    assert abs(fi["total_impact"] - risk["financial_impact_given_incident"]) < 0.01


def test_recalculate_all_assets_in_org(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset(client, token, name="Asset A")
    _create_asset(client, token, name="Asset B")

    resp = client.post("/api/v1/risks/recalculate", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_financial_risk_summary_aggregates_correctly(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset(client, token, name="Asset A", business_value=1_000_000)
    _create_asset(client, token, name="Asset B", business_value=2_000_000)
    client.post("/api/v1/risks/recalculate", headers=_auth(token))

    resp = client.get("/api/v1/financial-risk/summary", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_count"] == 2
    assert body["total_expected_annual_loss"] > 0
    assert body["total_financial_exposure"] > 0
    assert len(body["top_risks"]) <= 5


def test_executive_can_read_but_not_recalculate(client, db_session, seeded_admin):
    org, admin = seeded_admin
    create_user(db_session, email="exec@test.example", password="Exec@12345", role=UserRole.EXECUTIVE, organization_id=org.id)
    admin_token = _login(client, "admin@test.example", "TestAdmin@123")
    _create_asset(client, admin_token, name="Asset A")
    client.post("/api/v1/risks/recalculate", headers=_auth(admin_token))

    exec_token = _login(client, "exec@test.example", "Exec@12345")
    resp = client.get("/api/v1/financial-risk/summary", headers=_auth(exec_token))
    assert resp.status_code == 200

    resp = client.post("/api/v1/risks/recalculate", headers=_auth(exec_token))
    assert resp.status_code == 403


def test_get_risk_404_before_recalculation(client, seeded_admin):
    org, admin = seeded_admin
    token = _login(client, "admin@test.example", "TestAdmin@123")
    asset = _create_asset(client, token)

    resp = client.get(f"/api/v1/risks/{asset['id']}", headers=_auth(token))
    assert resp.status_code == 404
