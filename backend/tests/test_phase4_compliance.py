from app.crud.user import create_user
from app.models.compliance import ComplianceFramework, ComplianceMapping, ComplianceRequirement, ComplianceStatus
from app.models.user import UserRole


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_framework(db_session):
    framework = ComplianceFramework(name="Test Framework", short_code="TEST_FW", version="1.0")
    db_session.add(framework)
    db_session.commit()
    db_session.refresh(framework)

    reqs = [
        ComplianceRequirement(framework_id=framework.id, code="T-1", title="Requirement one"),
        ComplianceRequirement(framework_id=framework.id, code="T-2", title="Requirement two"),
        ComplianceRequirement(framework_id=framework.id, code="T-3", title="Requirement three"),
        ComplianceRequirement(framework_id=framework.id, code="T-4", title="Requirement four"),
    ]
    db_session.add_all(reqs)
    db_session.commit()
    for r in reqs:
        db_session.refresh(r)
    return framework, reqs


def test_list_frameworks_shows_requirement_counts(client, db_session, seeded_admin):
    org, admin = seeded_admin
    _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.get("/api/v1/compliance/frameworks", headers=_auth(token))
    assert resp.status_code == 200
    frameworks = resp.json()
    assert len(frameworks) == 1
    assert frameworks[0]["requirement_count"] == 4


def test_unmapped_requirements_default_to_not_assessed(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.get(f"/api/v1/compliance/frameworks/{framework.id}/mappings", headers=_auth(token))
    assert resp.status_code == 200
    mappings = resp.json()
    assert len(mappings) == 4
    assert all(m["status"] == "not_assessed" for m in mappings)
    assert all(m["id"] is None for m in mappings)  # nothing persisted yet


def test_upsert_mapping_creates_and_updates(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    resp = client.post(
        "/api/v1/compliance/mappings",
        json={"requirement_id": reqs[0].id, "status": "compliant", "notes": "All good"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "compliant"
    assert body["id"] is not None
    mapping_id = body["id"]

    # Update the same requirement — should update, not create a duplicate
    resp2 = client.post(
        "/api/v1/compliance/mappings",
        json={"requirement_id": reqs[0].id, "status": "partially_compliant", "notes": "Downgraded"},
        headers=_auth(token),
    )
    assert resp2.status_code == 200
    assert resp2.json()["id"] == mapping_id
    assert resp2.json()["status"] == "partially_compliant"


def test_only_write_roles_can_upsert_mapping(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    create_user(db_session, email="exec@test.example", password="Exec@12345", role=UserRole.EXECUTIVE, organization_id=org.id)
    create_user(db_session, email="compliance@test.example", password="Comp@12345", role=UserRole.COMPLIANCE_OFFICER, organization_id=org.id)

    exec_token = _login(client, "exec@test.example", "Exec@12345")
    resp = client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[0].id, "status": "compliant"}, headers=_auth(exec_token))
    assert resp.status_code == 403

    compliance_token = _login(client, "compliance@test.example", "Comp@12345")
    resp = client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[1].id, "status": "compliant"}, headers=_auth(compliance_token))
    assert resp.status_code == 200


def test_add_evidence_requires_existing_mapping(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    # No mapping exists yet for a nonsense id
    resp = client.post("/api/v1/compliance/mappings/9999/evidence", json={"description": "test"}, headers=_auth(token))
    assert resp.status_code == 404

    mapping_resp = client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[0].id, "status": "compliant"}, headers=_auth(token))
    mapping_id = mapping_resp.json()["id"]

    resp = client.post(
        f"/api/v1/compliance/mappings/{mapping_id}/evidence",
        json={"description": "Policy document attached", "url": "https://example.com/policy.pdf"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["description"] == "Policy document attached"


def test_gap_analysis_score_and_gaps(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    # T-1 compliant, T-2 partially_compliant, T-3 non_compliant, T-4 left not_assessed
    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[0].id, "status": "compliant"}, headers=_auth(token))
    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[1].id, "status": "partially_compliant"}, headers=_auth(token))
    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[2].id, "status": "non_compliant"}, headers=_auth(token))

    resp = client.get(f"/api/v1/compliance/frameworks/{framework.id}/gap-analysis", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    # score = (1 compliant + 0.5*1 partial) / 4 applicable * 100 = 37.5
    assert body["compliance_score"] == 37.5
    assert body["compliant_count"] == 1
    assert body["partially_compliant_count"] == 1
    assert body["non_compliant_count"] == 1
    assert body["not_assessed_count"] == 1
    # gaps should include partial, non_compliant, and not_assessed (3 total), not the compliant one
    assert len(body["gaps"]) == 3
    gap_codes = {g["requirement"]["code"] for g in body["gaps"]}
    assert gap_codes == {"T-2", "T-3", "T-4"}


def test_not_applicable_excluded_from_score_denominator(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[0].id, "status": "compliant"}, headers=_auth(token))
    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[1].id, "status": "not_applicable"}, headers=_auth(token))
    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[2].id, "status": "not_applicable"}, headers=_auth(token))
    client.post("/api/v1/compliance/mappings", json={"requirement_id": reqs[3].id, "status": "not_applicable"}, headers=_auth(token))

    resp = client.get(f"/api/v1/compliance/frameworks/{framework.id}/gap-analysis", headers=_auth(token))
    body = resp.json()
    # only 1 applicable requirement, and it's compliant -> 100%
    assert body["compliance_score"] == 100.0
    assert body["not_applicable_count"] == 3


def test_overall_summary_averages_all_frameworks(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    token = _login(client, "admin@test.example", "TestAdmin@123")

    for r in reqs:
        client.post("/api/v1/compliance/mappings", json={"requirement_id": r.id, "status": "compliant"}, headers=_auth(token))

    resp = client.get("/api/v1/compliance/summary", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_score"] == 100.0
    assert len(body["frameworks"]) == 1


def test_executive_can_read_frameworks_and_gap_analysis(client, db_session, seeded_admin):
    org, admin = seeded_admin
    framework, reqs = _seed_framework(db_session)
    create_user(db_session, email="exec2@test.example", password="Exec@12345", role=UserRole.EXECUTIVE, organization_id=org.id)
    token = _login(client, "exec2@test.example", "Exec@12345")

    resp = client.get("/api/v1/compliance/frameworks", headers=_auth(token))
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/compliance/frameworks/{framework.id}/gap-analysis", headers=_auth(token))
    assert resp.status_code == 200
