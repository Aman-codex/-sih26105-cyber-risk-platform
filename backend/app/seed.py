"""
Idempotent seed script for local/demo environments.

Run automatically by docker-compose on backend startup (after migrations).
Can also be run manually:

    python -m app.seed
"""
from datetime import date, datetime, timedelta, timezone

from app.core.config import settings
from app.crud.user import create_user, get_user_by_email
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.enums import (
    BusinessCriticality,
    ControlType,
    Exploitability,
    Severity,
    VulnerabilityStatus,
)
from app.models.organization import Organization
from app.models.security_control import SecurityControl, asset_controls
from app.models.threat import Threat, ThreatEvent, threat_asset_relevance
from app.models.user import UserRole
from app.models.vulnerability import Vulnerability, asset_vulnerabilities
from app.crud.risk import recalculate_all_risks
from app.models.compliance import ComplianceFramework, ComplianceMapping, ComplianceRequirement, ComplianceStatus


def run():
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == settings.SEED_ORG_NAME).first()
        if not org:
            org = Organization(
                name=settings.SEED_ORG_NAME,
                industry="Banking & Financial Services",
                country="India",
                annual_cyber_budget=5_000_000.0,  # INR, used from Phase 5 onward
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"[seed] Created organization: {org.name} (id={org.id})")
        else:
            print(f"[seed] Organization already exists: {org.name} (id={org.id})")

        demo_users = [
            (settings.SEED_ADMIN_EMAIL, settings.SEED_ADMIN_PASSWORD, UserRole.ADMIN, "Platform Admin"),
            ("ciso@sih2026.example", "Ciso@12345", UserRole.CISO, "Chief Information Security Officer"),
            ("analyst@sih2026.example", "Analyst@12345", UserRole.RISK_ANALYST, "Risk Analyst"),
            ("compliance@sih2026.example", "Compliance@12345", UserRole.COMPLIANCE_OFFICER, "Compliance Officer"),
            ("exec@sih2026.example", "Exec@12345", UserRole.EXECUTIVE, "Chief Financial Officer"),
        ]

        for email, password, role, full_name in demo_users:
            if get_user_by_email(db, email):
                print(f"[seed] User already exists: {email}")
                continue
            create_user(db, email=email, password=password, role=role, organization_id=org.id, full_name=full_name)
            print(f"[seed] Created user: {email} ({role.value})")

        seed_demo_scenario(db, org.id)

    finally:
        db.close()


def seed_demo_scenario(db, org_id: int) -> None:
    """
    Seeds a coherent, realistic Phase 2 demo dataset: assets, vulnerabilities,
    threats and controls for a fictional bank, matching the SIH demo scenario
    (a new critical vulnerability appears on an internet-facing, business
    critical asset that is also under active threat-actor targeting).
    Idempotent: skipped entirely if any asset already exists for this org.
    """
    if db.query(Asset).filter(Asset.organization_id == org_id).first():
        print("[seed] Demo assets/vulnerabilities/threats/controls already exist, skipping")
        return

    # --- Assets ---
    core_db = Asset(
        organization_id=org_id, name="Core Banking Database", asset_type="database",
        description="Primary system of record for accounts, balances and transactions.",
        business_criticality=BusinessCriticality.CRITICAL, business_value=100_000_000.0, internet_exposure=False,
    )
    online_banking = Asset(
        organization_id=org_id, name="Online Banking Portal", asset_type="web_app",
        description="Customer-facing web and mobile banking application.",
        business_criticality=BusinessCriticality.CRITICAL, business_value=50_000_000.0, internet_exposure=True,
    )
    hr_portal = Asset(
        organization_id=org_id, name="Employee HR Portal", asset_type="web_app",
        description="Internal HR self-service application, exposed for remote employee access.",
        business_criticality=BusinessCriticality.MEDIUM, business_value=5_000_000.0, internet_exposure=True,
    )
    file_server = Asset(
        organization_id=org_id, name="Internal File Server", asset_type="server",
        description="Departmental file storage, internal network only.",
        business_criticality=BusinessCriticality.LOW, business_value=1_000_000.0, internet_exposure=False,
    )
    db.add_all([core_db, online_banking, hr_portal, file_server])
    db.commit()
    for a in (core_db, online_banking, hr_portal, file_server):
        db.refresh(a)

    online_banking.depends_on = [core_db]
    db.commit()
    print("[seed] Created 4 demo assets")

    # --- Vulnerabilities ---
    critical_vuln = Vulnerability(
        organization_id=org_id, cve_id="CVE-2026-11001",
        title="Remote Code Execution in Web Login Module",
        description="Unauthenticated RCE in the online banking login flow, actively exploited in the wild.",
        cvss_score=9.8, severity=Severity.CRITICAL, exploitability=Exploitability.ACTIVELY_EXPLOITED,
        status=VulnerabilityStatus.OPEN, published_date=date.today(),
    )
    sqli_vuln = Vulnerability(
        organization_id=org_id, cve_id="CVE-2025-08842",
        title="SQL Injection in Legacy Reporting Module",
        description="Authenticated SQL injection in the HR portal's reporting export feature.",
        cvss_score=7.5, severity=Severity.HIGH, exploitability=Exploitability.FUNCTIONAL,
        status=VulnerabilityStatus.OPEN, published_date=date.today() - timedelta(days=120),
    )
    tls_vuln = Vulnerability(
        organization_id=org_id, cve_id="CVE-2024-04471",
        title="Outdated TLS Configuration",
        description="Deprecated TLS 1.0/1.1 ciphers still accepted on the internal file server.",
        cvss_score=5.3, severity=Severity.MEDIUM, exploitability=Exploitability.THEORETICAL,
        status=VulnerabilityStatus.MITIGATED, published_date=date.today() - timedelta(days=400),
    )
    db.add_all([critical_vuln, sqli_vuln, tls_vuln])
    db.commit()
    for v in (critical_vuln, sqli_vuln, tls_vuln):
        db.refresh(v)

    critical_vuln.affected_assets = [online_banking]
    sqli_vuln.affected_assets = [hr_portal]
    tls_vuln.affected_assets = [file_server]
    db.commit()
    print("[seed] Created 3 demo vulnerabilities")

    # --- Threats ---
    apt_kestrel = Threat(
        organization_id=org_id, name="APT-Kestrel", threat_actor="Financially motivated APT group",
        mitre_technique_id="T1190", mitre_tactic="Initial Access",
        description="Known for exploiting public-facing web application vulnerabilities in the BFSI sector.",
    )
    ransomware = Threat(
        organization_id=org_id, name="Generic Ransomware Campaign", threat_actor="Opportunistic criminal group",
        mitre_technique_id="T1486", mitre_tactic="Impact",
        description="Encrypts critical data stores and demands ransom for decryption keys.",
    )
    db.add_all([apt_kestrel, ransomware])
    db.commit()
    for t in (apt_kestrel, ransomware):
        db.refresh(t)

    db.execute(threat_asset_relevance.insert().values(threat_id=apt_kestrel.id, asset_id=online_banking.id, relevance_score=0.9))
    db.execute(threat_asset_relevance.insert().values(threat_id=apt_kestrel.id, asset_id=hr_portal.id, relevance_score=0.6))
    db.execute(threat_asset_relevance.insert().values(threat_id=ransomware.id, asset_id=core_db.id, relevance_score=0.7))
    db.execute(threat_asset_relevance.insert().values(threat_id=ransomware.id, asset_id=file_server.id, relevance_score=0.5))
    db.commit()

    demo_event = ThreatEvent(
        organization_id=org_id, threat_id=apt_kestrel.id, asset_id=online_banking.id,
        event_type="active_exploitation_detected", severity=Severity.CRITICAL,
        description="Threat intel feed reports APT-Kestrel actively exploiting CVE-2026-11001 against BFSI targets.",
        detected_at=datetime.now(timezone.utc),
    )
    db.add(demo_event)
    db.commit()
    print("[seed] Created 2 demo threats + 1 threat event (the SIH demo trigger)")

    # --- Security Controls ---
    mfa = SecurityControl(
        organization_id=org_id, name="Multi-Factor Authentication", control_type=ControlType.MFA,
        description="MFA enforced on customer and employee login flows.",
        annual_cost=200_000.0, effectiveness_score=0.35, is_active=True,
    )
    edr = SecurityControl(
        organization_id=org_id, name="Endpoint Detection & Response", control_type=ControlType.EDR,
        description="EDR agents on servers and databases for real-time threat detection.",
        annual_cost=500_000.0, effectiveness_score=0.40, is_active=True,
    )
    waf = SecurityControl(
        organization_id=org_id, name="Web Application Firewall", control_type=ControlType.FIREWALL,
        description="WAF in front of internet-facing web applications.",
        annual_cost=300_000.0, effectiveness_score=0.30, is_active=True,
    )
    backup = SecurityControl(
        organization_id=org_id, name="Automated Immutable Backup", control_type=ControlType.BACKUP,
        description="Daily immutable backups for critical data stores.",
        annual_cost=150_000.0, effectiveness_score=0.25, is_active=True,
    )
    patching = SecurityControl(
        organization_id=org_id, name="Patch Management Program", control_type=ControlType.PATCH_MANAGEMENT,
        description="Scheduled patching SLA across all assets.",
        annual_cost=100_000.0, effectiveness_score=0.30, is_active=True,
    )
    db.add_all([mfa, edr, waf, backup, patching])
    db.commit()
    for c in (mfa, edr, waf, backup, patching):
        db.refresh(c)

    # Coverage percentages are deliberately left with headroom below the
    # risk model's max_control_mitigation cap (0.85 by default) on every
    # asset — a fully-saturated asset would leave the Phase 5 Investment
    # Optimizer nothing to recommend, which defeats the point of the demo.
    coverage = [
        (mfa, online_banking, 100.0), (mfa, hr_portal, 100.0),
        (waf, online_banking, 50.0), (waf, hr_portal, 50.0),
        (edr, core_db, 100.0), (edr, file_server, 50.0),
        (backup, core_db, 100.0), (backup, file_server, 100.0),
        (patching, online_banking, 50.0), (patching, hr_portal, 50.0),
        (patching, core_db, 50.0), (patching, file_server, 50.0),
    ]
    for control, asset, pct in coverage:
        db.execute(asset_controls.insert().values(control_id=control.id, asset_id=asset.id, coverage_percentage=pct))
    db.commit()
    print("[seed] Created 5 demo security controls with asset coverage mappings")

    # --- Phase 5: not-yet-deployed candidate controls for Investment Optimization ---
    ztna = SecurityControl(
        organization_id=org_id, name="Zero Trust Network Access (ZTNA)", control_type=ControlType.IAM,
        description="Proposed: replaces perimeter-based access with per-session, identity-verified access.",
        annual_cost=350_000.0, effectiveness_score=0.28, is_active=False,
    )
    soc = SecurityControl(
        organization_id=org_id, name="24x7 Security Operations Centre (SOC)", control_type=ControlType.MONITORING,
        description="Proposed: outsourced round-the-clock monitoring and alert triage.",
        annual_cost=600_000.0, effectiveness_score=0.32, is_active=False,
    )
    awareness = SecurityControl(
        organization_id=org_id, name="Security Awareness Training Program", control_type=ControlType.OTHER,
        description="Proposed: quarterly phishing simulations and staff training.",
        annual_cost=80_000.0, effectiveness_score=0.15, is_active=False,
    )
    dlp = SecurityControl(
        organization_id=org_id, name="Data Loss Prevention (DLP)", control_type=ControlType.MONITORING,
        description="Proposed: content-inspection controls to block sensitive data exfiltration.",
        annual_cost=220_000.0, effectiveness_score=0.20, is_active=False,
    )
    db.add_all([ztna, soc, awareness, dlp])
    db.commit()
    print("[seed] Created 4 not-yet-deployed candidate controls for investment optimization")

    # --- Phase 3: initial risk calculation ---
    risks = recalculate_all_risks(db, org_id)
    print(f"[seed] Calculated risk for {len(risks)} assets:")
    for r in sorted(risks, key=lambda x: x.risk_score, reverse=True):
        asset = db.get(Asset, r.asset_id)
        print(f"[seed]   {asset.name}: risk_score={r.risk_score}, EAL=${r.expected_annual_loss:,.0f}")

    # --- Phase 4: compliance frameworks, requirements, and demo mappings ---
    seed_compliance(db, org_id, mfa=mfa, edr=edr, backup=backup, patching=patching)


def seed_compliance(db, org_id: int, mfa, edr, backup, patching) -> None:
    """
    Seeds reference frameworks/requirements (shared across all orgs, so
    skipped entirely if they already exist) and a realistic mixed demo
    compliance posture for this organization: some requirements compliant,
    some partial, some non-compliant, and a few deliberately left
    'not assessed' to demonstrate that default state.

    NOTE: this data is illustrative for the SIH demo and does not
    constitute an official compliance certification or audit finding.
    """
    if db.query(ComplianceFramework).first():
        print("[seed] Compliance frameworks already exist, skipping framework/requirement seed")
    else:
        frameworks_data = [
            ("NIST Cybersecurity Framework", "NIST_CSF", "2.0", [
                ("ID.AM-1", "Identify", "Physical devices and systems within the organization are inventoried"),
                ("PR.AC-1", "Protect", "Identities and credentials are issued, managed, verified, revoked, and audited"),
                ("PR.DS-1", "Protect", "Data-at-rest is protected"),
                ("DE.CM-1", "Detect", "The network is monitored to detect potential cybersecurity events"),
                ("RS.RP-1", "Respond", "Response plan is executed during or after an incident"),
            ]),
            ("ISO/IEC 27001", "ISO_27001", "2022", [
                ("A.5.1", None, "Policies for information security"),
                ("A.8.2", None, "Privileged access rights"),
                ("A.8.13", None, "Information backup"),
                ("A.5.24", None, "Information security incident management planning"),
            ]),
            ("CIS Controls", "CIS_CONTROLS", "v8", [
                ("CIS-4", None, "Secure Configuration of Enterprise Assets and Software"),
                ("CIS-5", None, "Account Management"),
                ("CIS-6", None, "Access Control Management"),
                ("CIS-11", None, "Data Recovery"),
            ]),
            ("RBI Cyber Security Framework", "RBI_CSF", "2016", [
                ("RBI-2.1", None, "Multi-factor authentication for privileged and sensitive access"),
                ("RBI-3.1", None, "Continuous security monitoring / Security Operations Centre"),
                ("RBI-4.1", None, "Incident response and reporting to RBI"),
            ]),
            ("SEBI Cyber Resilience Framework", "SEBI_CSCRF", "2024", [
                ("SEBI-1", None, "Cyber resilience framework governance"),
                ("SEBI-2", None, "Vulnerability Assessment and Penetration Testing (VAPT)"),
                ("SEBI-3", None, "Data localisation and backup"),
            ]),
        ]

        for name, code, version, reqs in frameworks_data:
            framework = ComplianceFramework(name=name, short_code=code, version=version)
            db.add(framework)
            db.commit()
            db.refresh(framework)
            for req_code, category, title in reqs:
                db.add(ComplianceRequirement(framework_id=framework.id, code=req_code, category=category, title=title))
            db.commit()
        print(f"[seed] Created {len(frameworks_data)} compliance frameworks with their requirements")

    def _req(code: str) -> ComplianceRequirement:
        return db.query(ComplianceRequirement).filter(ComplianceRequirement.code == code).first()

    if db.query(ComplianceMapping).filter(ComplianceMapping.organization_id == org_id).first():
        print("[seed] Demo compliance mappings already exist, skipping")
        return

    demo_mappings = [
        ("ID.AM-1", ComplianceStatus.COMPLIANT, None, "Asset inventory maintained in the platform"),
        ("PR.AC-1", ComplianceStatus.COMPLIANT, mfa.id, None),
        ("PR.DS-1", ComplianceStatus.COMPLIANT, backup.id, None),
        ("DE.CM-1", ComplianceStatus.PARTIALLY_COMPLIANT, edr.id, "EDR deployed on core assets only; network-wide monitoring pending"),
        ("RS.RP-1", ComplianceStatus.NON_COMPLIANT, None, "No formal incident response plan documented yet"),
        ("A.5.1", ComplianceStatus.PARTIALLY_COMPLIANT, None, "Policy drafted, pending board approval"),
        ("A.8.2", ComplianceStatus.NON_COMPLIANT, None, "Privileged access reviews not yet formalized"),
        ("A.8.13", ComplianceStatus.COMPLIANT, backup.id, None),
        ("CIS-4", ComplianceStatus.COMPLIANT, patching.id, None),
        ("CIS-6", ComplianceStatus.COMPLIANT, mfa.id, None),
        ("CIS-11", ComplianceStatus.COMPLIANT, backup.id, None),
        ("RBI-2.1", ComplianceStatus.COMPLIANT, mfa.id, None),
        ("RBI-3.1", ComplianceStatus.PARTIALLY_COMPLIANT, edr.id, None),
        ("RBI-4.1", ComplianceStatus.NON_COMPLIANT, None, "No formal RBI incident reporting process in place"),
        ("SEBI-2", ComplianceStatus.NON_COMPLIANT, None, "VAPT not conducted in the last 12 months"),
        ("SEBI-3", ComplianceStatus.PARTIALLY_COMPLIANT, backup.id, "Backup in place; data localisation review pending"),
        # A.5.24, CIS-5, SEBI-1 deliberately left unmapped to demonstrate the "not assessed" default state.
    ]

    for code, status, control_id, notes in demo_mappings:
        req = _req(code)
        if req:
            db.add(ComplianceMapping(organization_id=org_id, requirement_id=req.id, status=status, control_id=control_id, notes=notes))
    db.commit()
    print(f"[seed] Created {len(demo_mappings)} demo compliance mappings across 5 frameworks")


if __name__ == "__main__":
    run()
