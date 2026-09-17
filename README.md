# SIH26105 — AI-Powered Continuous Cyber Risk Quantification and Investment Optimization Platform

SIH 2026 prototype. Built incrementally, phase by phase. **This README covers Phase 1.**

## Phase 1 scope

- Project scaffolding (backend + frontend) and Docker Compose orchestration
- PostgreSQL database + Alembic migrations
- Redis (wired up, not yet used for background jobs — arrives with async
  recalculation in a later phase)
- JWT authentication (access + refresh tokens)
- Role-Based Access Control (RBAC) with 5 roles: `admin`, `ciso`,
  `risk_analyst`, `compliance_officer`, `executive`
- Seed script that creates a demo organization and one user per role
- Audit logging of login/registration events
- A minimal React login → protected dashboard flow proving the auth loop
  end-to-end
- Backend test suite (pytest, SQLite in-memory) covering login, RBAC-gated
  registration, token refresh, and `/me`

## Architecture (Phase 1 slice)

```
                 ┌─────────────────────┐
                 │   React + Vite SPA   │  (JWT stored client-side,
                 │  Login → Dashboard   │   axios interceptor auto-refreshes)
                 └──────────┬───────────┘
                            │ REST (JSON) — /api/v1
                            ▼
                 ┌─────────────────────┐
                 │   FastAPI backend    │
                 │  ┌────────────────┐ │
                 │  │ auth router    │ │  login / refresh / register / me
                 │  ├────────────────┤ │
                 │  │ core/security  │ │  bcrypt hashing, JWT encode/decode
                 │  │ core/deps      │ │  get_current_user, require_roles()
                 │  └────────────────┘ │
                 └──────────┬───────────┘
                            │ SQLAlchemy ORM
                            ▼
                 ┌─────────────────────┐      ┌───────────┐
                 │     PostgreSQL       │      │   Redis    │ (reserved for
                 │ organizations, users,│      │ (idle in   │  background
                 │     audit_logs       │      │  Phase 1)  │  jobs, Phase 3+)
                 └─────────────────────┘      └───────────┘
```

Every table beyond `organizations`/`users`/`audit_logs` (Asset, Vulnerability,
Threat, SecurityControl, Risk, ComplianceFramework, Investment, ...) is added
in later phases by dropping new model files into `backend/app/models/`,
importing them in `app/db/base.py`, and generating a new Alembic revision —
Phase 1's auth/RBAC layer does not need to change.

## Running Phase 1 locally

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env      # already done for you; edit if you want different secrets
docker compose up --build
```

This starts Postgres, Redis, the FastAPI backend (auto-runs Alembic
migrations + the seed script on boot), and the Vite dev server.

- API: http://localhost:8000 (interactive docs at `/docs`)
- Frontend: http://localhost:5173
- Health check: `GET http://localhost:8000/health`

### Option B — run backend without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point DATABASE_URL at your own Postgres instance, then:
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

### Running the frontend without Docker

```bash
cd frontend
npm install
npm run dev
```

### Running backend tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

All 8 tests should pass; they run against an isolated in-memory SQLite
database and don't require Postgres to be running.

## Seeded demo accounts

| Email | Password | Role |
|---|---|---|
| admin@sih2026.example | Admin@12345 | admin |
| ciso@sih2026.example | Ciso@12345 | ciso |
| analyst@sih2026.example | Analyst@12345 | risk_analyst |
| compliance@sih2026.example | Compliance@12345 | compliance_officer |
| exec@sih2026.example | Exec@12345 | executive |

## API examples (Phase 1)

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@sih2026.example&password=Admin@12345"

# Use the returned access_token
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Register a new user (admin-only — enforced by RBAC)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"email":"newanalyst@sih2026.example","password":"NewPass@123","role":"risk_analyst","full_name":"New Analyst"}'

# Refresh an expired access token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<REFRESH_TOKEN>"}'
```

## What's next

- **Phase 3**: Risk quantification engine and financial-impact model
  (configurable parameters, EAL, scenario VaR)
- ...through Phase 10 (integration testing, SIH demo scenario)

Nothing in this phase's auth/RBAC/database layer will need to be rewritten
as later phases are added — only extended.

---

## Phase 2 — Asset, Vulnerability, Threat & Security Control management

Adds the core inventory the Risk Engine (Phase 3) will consume.

### What's new

- **Models**: `Asset` (with self-referential dependency mapping),
  `Vulnerability` (CVSS score auto-derives severity if not given),
  `Threat` + `ThreatEvent` (MITRE ATT&CK technique/tactic fields, with a
  relevance score per asset), `SecurityControl` (cost + effectiveness,
  with a per-asset coverage percentage)
- **APIs**: `/api/v1/assets`, `/api/v1/vulnerabilities`,
  `/api/v1/threats` (+ `/api/v1/threats/events`), `/api/v1/controls` —
  full CRUD, all scoped to the caller's organization
- **RBAC**: `admin`, `ciso`, `risk_analyst` can create/update;
  `admin`/`ciso` only can delete; every role (including `executive`,
  `compliance_officer`) can read
- **Migration**: `0002_phase2_asset_vuln_threat_control` — safe to run on
  top of an existing Phase 1 database with `alembic upgrade head`
- **Seed data**: a realistic demo scenario for a fictional bank — 4 assets
  (an internet-facing Online Banking Portal that depends on a Core Banking
  Database, an HR Portal, an internal file server), 3 vulnerabilities
  (including a critical, actively-exploited CVE on the banking portal), 2
  threats with MITRE mappings and a live threat event, and 5 security
  controls with per-asset coverage — this is the exact dataset the Phase 3
  risk engine and later phases' "before/after" demo will use
- **Frontend**: Assets/Vulnerabilities/Threats/Controls tabs added to the
  dashboard. Assets supports create + delete (RBAC-aware buttons); the
  others are read-only tables for now
- **Tests**: 9 new tests covering CRUD, RBAC enforcement, CVSS→severity
  derivation, dependency mapping, and asset-coverage mapping (17/17 total
  passing)

### Running Phase 2 on top of your existing Phase 1 setup

If you already have Phase 1 running locally (per the instructions above),
you only need to re-run the migration and reseed:

```bash
cd backend
# with your venv activated
alembic upgrade head      # applies the new Phase 2 tables
python -m app.seed        # adds the demo assets/vulnerabilities/threats/controls
                           # (safe to re-run — it's idempotent per phase)
uvicorn app.main:app --reload
```

No frontend dependency changes were needed — just restart `npm run dev` if
it's not already running, and open http://localhost:5173 to see the new
Assets / Vulnerabilities / Threats / Controls tabs.

### API examples (Phase 2)

```bash
# List assets
curl http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Create an asset (admin/ciso/risk_analyst only)
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Payments API","asset_type":"api","business_criticality":"critical","business_value":20000000,"internet_exposure":true}'

# Create a vulnerability affecting that asset (severity auto-derived from cvss_score if omitted)
curl -X POST http://localhost:8000/api/v1/vulnerabilities \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"cve_id":"CVE-2026-99999","title":"Auth bypass in Payments API","cvss_score":9.1,"affected_asset_ids":[<ASSET_ID>]}'

# Record a threat event (the trigger for future continuous recalculation)
curl -X POST http://localhost:8000/api/v1/threats/events \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"threat_id":1,"asset_id":<ASSET_ID>,"event_type":"active_exploitation_detected","severity":"critical","description":"Observed in the wild"}'

# List security controls
curl http://localhost:8000/api/v1/controls \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### What's next after Phase 2

- **Phase 3**: Risk quantification engine + financial-impact model,
  consuming exactly the assets/vulnerabilities/threats/controls seeded
  here to compute risk scores, incident probability, and Expected Annual
  Loss (EAL)

---

## Phase 3 — Risk Quantification Engine & Financial-Impact Model

This is where the platform starts actually *calculating* things: attack
likelihood, a 0-100 risk score, Expected Annual Loss (EAL), and
scenario-based Value at Risk (VaR) — all derived from the assets,
vulnerabilities, threats and controls seeded in Phase 2, using
**configurable, transparent parameters** (nothing hard-coded or invented).

### What's new

- **`RiskModelConfig`**: one editable parameter set per organization —
  exploitability→likelihood mapping, criticality multipliers, internet
  exposure multiplier, threat-relevance weight, control-mitigation cap,
  financial-impact category weights, and VaR simulation settings. Auto-created
  with sane defaults on first use; visible via `GET /api/v1/risks/config`
  and tunable via `PUT` (admin/ciso only)
- **Risk Engine** (`app/services/risk_engine.py`): for each asset, finds the
  worst open vulnerability, applies severity/exposure/threat-relevance
  multipliers, subtracts control mitigation (effectiveness × coverage,
  capped), and produces a likelihood, a 0-100 risk score, and an ordered
  **risk driver breakdown** showing exactly what moved the number and by
  how much (e.g. "Internet exposure: +30%", "Security control coverage: -85%")
- **Financial Quantification**: business value × configurable category
  weights (business interruption, data loss, recovery cost, incident
  response, legal/regulatory, revenue impact) → cost if an incident is
  fully realized; **EAL = likelihood × that cost**
- **Scenario-based VaR**: a deterministic (fixed-seed) Monte Carlo
  simulation of the loss distribution, reporting the loss value at the
  organization's configured confidence level (95% by default)
- **New models**: `RiskModelConfig`, `Risk`, `FinancialImpact`,
  `RiskScenario` (the last one gives Phase 6's what-if simulator somewhere
  to store alternative scenarios later, alongside the "current" one Phase 3 creates)
- **APIs**: `GET/PUT /api/v1/risks/config`, `POST /api/v1/risks/recalculate`
  (single asset via `?asset_id=` or the whole org), `GET /api/v1/risks`,
  `GET /api/v1/risks/{asset_id}`, `GET /api/v1/financial-risk/summary`
  (dashboard-ready aggregate: total EAL, total VaR, total exposure, risk-band counts)
- **RBAC**: admin/ciso/risk_analyst can recalculate; admin/ciso only can
  edit the model config; every role can read
- **Migration**: `0003_phase3_risk_engine`
- **Seed data**: now runs an initial risk calculation on the Phase 2 demo
  assets — the Online Banking Portal (critical, actively-exploited CVE,
  internet-exposed, actively targeted by APT-Kestrel) correctly comes out
  as by far the highest risk and highest EAL, exactly matching the SIH
  demo narrative
- **Frontend**: new "Risk Overview" tab (now the default landing tab) —
  summary cards (total exposure, EAL, VaR, risk-band counts), a sortable
  risk table, and an expandable per-asset view showing the risk driver
  breakdown and financial impact breakdown side by side
- **Tests**: 9 new tests covering config defaults/RBAC, recalculation
  (single + org-wide), driver correctness (exposed+vulnerable asset scores
  higher than a safe one), financial breakdown consistency, and the
  summary aggregate (26/26 total passing)

### Running Phase 3 on top of your existing setup

```bash
cd backend
# with your venv activated
alembic upgrade head      # applies the new Phase 3 tables
python -m app.seed        # runs an initial risk calculation on your seeded assets
uvicorn app.main:app --reload
```

Frontend: no new dependencies — just restart `npm run dev` if needed. The
dashboard now opens on the **Risk Overview** tab by default.

### API examples (Phase 3)

```bash
# View the current risk model parameters
curl http://localhost:8000/api/v1/risks/config \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Tune a parameter (admin/ciso only) — partial merge, other keys untouched
curl -X PUT http://localhost:8000/api/v1/risks/config \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"internet_exposure_multiplier": 1.5}}'

# Recalculate risk for every asset in the organization
curl -X POST http://localhost:8000/api/v1/risks/recalculate \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Get the risk detail (drivers + financial breakdown) for one asset
curl http://localhost:8000/api/v1/risks/<ASSET_ID> \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Dashboard aggregate: total EAL, VaR, exposure, risk-band counts
curl http://localhost:8000/api/v1/financial-risk/summary \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### What's next after Phase 3

- **Phase 4**: Compliance mapping (NIST CSF, ISO 27001, CIS Controls, RBI,
  SEBI) and gap analysis, linking security controls to framework
  requirements with evidence attachment

---

## Phase 4 — Compliance Mapping & Gap Analysis

Maps your security posture against five industry/regulatory frameworks and
shows exactly where the gaps are. **This module reports a self-assessed
mapping status — it does not constitute, and should never be presented as,
an official regulatory certification or audit finding.**

### What's new

- **Reference data (shared across all orgs)**: 5 frameworks seeded with a
  representative subset of requirements each — NIST Cybersecurity
  Framework 2.0, ISO/IEC 27001:2022, CIS Controls v8, RBI Cyber Security
  Framework, and SEBI Cyber Resilience Framework
- **Per-organization mapping**: each requirement gets a status — Compliant,
  Partially Compliant, Non-Compliant, Not Applicable, or Not Assessed (the
  default for anything nobody has looked at yet, computed on the fly
  without cluttering the database with untouched rows)
- **Evidence attachment**: notes and/or a URL can be attached to any
  assessed requirement (no file upload in this phase — text/link evidence
  only)
- **Gap analysis per framework**: a 0-100 compliance score (partially
  compliant counts as half credit; Not Applicable items are excluded from
  the denominator so they can't be gamed either way) plus the list of
  everything that isn't fully compliant
- **Overall summary**: averages the score across all 5 frameworks — the
  number the Management Dashboard (Phase 9) will show
- **APIs**: `GET /api/v1/compliance/frameworks`,
  `GET /api/v1/compliance/frameworks/{id}/mappings`,
  `GET /api/v1/compliance/frameworks/{id}/gap-analysis`,
  `GET /api/v1/compliance/summary`,
  `POST /api/v1/compliance/mappings` (upsert status),
  `POST /api/v1/compliance/mappings/{id}/evidence`
- **RBAC**: admin/ciso/compliance_officer can set statuses and attach
  evidence; every role can read
- **Migration**: `0004_phase4_compliance`
- **Seed data**: a realistic mixed compliance posture for the demo bank —
  16 mappings across the 5 frameworks (some compliant, some partial, some
  non-compliant), with a handful of requirements deliberately left
  unassessed to demonstrate that default state, linked to the same
  security controls seeded in Phase 2 where relevant
- **Frontend**: new "Compliance" tab — framework picker, score/status
  summary cards, and an editable requirement table (status dropdown for
  write-capable roles, read-only badges for everyone else)
- **Tests**: 9 new tests covering framework listing, the not-assessed
  default, mapping upsert (create + update), RBAC, evidence attachment,
  gap-analysis scoring math (including the Not Applicable exclusion), and
  the overall summary (35/35 total passing)

### Running Phase 4 on top of your existing setup

```bash
cd backend
# with your venv activated
alembic upgrade head      # applies the new Phase 4 tables
python -m app.seed        # adds the 5 frameworks/requirements + demo mappings
uvicorn app.main:app --reload
```

Frontend: `npm install` (no new packages, but safe to re-run) then
`npm run dev` — a new "Compliance" tab appears in the dashboard nav.

### API examples (Phase 4)

```bash
# List available frameworks
curl http://localhost:8000/api/v1/compliance/frameworks \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# See NIST CSF gap analysis (framework id from the list above)
curl http://localhost:8000/api/v1/compliance/frameworks/1/gap-analysis \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Mark a requirement compliant, optionally linking a control (admin/ciso/compliance_officer only)
curl -X POST http://localhost:8000/api/v1/compliance/mappings \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"requirement_id": 9, "status": "compliant", "control_id": 1, "notes": "MFA enforced org-wide"}'

# Attach evidence to that mapping (use the "id" returned above)
curl -X POST http://localhost:8000/api/v1/compliance/mappings/<MAPPING_ID>/evidence \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"description": "MFA policy document", "url": "https://example.com/mfa-policy.pdf"}'

# Overall compliance posture across every framework
curl http://localhost:8000/api/v1/compliance/summary \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### What's next after Phase 4

- **Phase 5**: Investment Optimization using Google OR-Tools — given a
  fixed cybersecurity budget, recommend which security controls to invest
  in for the best risk reduction, using the exact cost/effectiveness
  numbers already seeded in Phase 2

---

## Phase 5 — Investment Optimization (Google OR-Tools)

Given a fixed cybersecurity budget, recommends which not-yet-deployed
security controls to invest in for the best risk reduction — solved
exactly with Google OR-Tools' CP-SAT solver as a 0/1 knapsack problem, not
a greedy heuristic.

### What's new

- **Candidate estimation**: every inactive (`is_active=False`) control is
  a candidate investment. Its estimated risk reduction is computed by
  literally re-running the Phase 3 Risk Engine as if that control alone
  were deployed at 100% coverage across every asset, then comparing to the
  current baseline total EAL — the same engine used everywhere else in the
  platform, not a separate ad-hoc formula
- **Exact optimization**: `POST /api/v1/optimization/recommend` builds a
  0/1 knapsack model (maximize total risk reduction subject to
  `sum(cost) <= budget`) and solves it exactly with OR-Tools CP-SAT
- **No double-counting**: a subtle but important correctness fix — two
  candidates each independently "filling" the same risk-mitigation
  headroom don't combine to more than that headroom's worth of benefit.
  The API uses each candidate's solo reduction as CP-SAT's selection
  heuristic, but then re-runs the Risk Engine once more against the exact
  combined effect of the final selected set, so the totals reported are
  always internally consistent (total reduction can never exceed the
  baseline — this was caught and fixed during testing)
- **Output**: recommended controls, total investment, total risk
  reduction, remaining risk, and ROSI (Return on Security Investment)
- **New models**: `Investment` (the candidate catalog, upserted on every
  run) and `Recommendation` (an immutable snapshot of each optimization run)
- **APIs**: `GET /api/v1/investments` (candidate catalog),
  `POST /api/v1/optimization/recommend` (run the optimizer; budget
  defaults to the organization's `annual_cyber_budget` if omitted),
  `GET /api/v1/optimization/recommendations` (run history)
- **RBAC**: admin/ciso/risk_analyst can run the optimizer; every role can
  view candidates and history
- **Migration**: `0005_phase5_investment_optimization`
- **Seed data update**: 4 new not-yet-deployed candidate controls (Zero
  Trust Network Access, 24x7 SOC, Security Awareness Training, DLP).
  **Note:** the Phase 2 seed's existing-control coverage percentages were
  also reduced from their original values — the original numbers left
  every asset already saturated at the risk model's mitigation cap, which
  meant the optimizer correctly but unhelpfully had zero headroom to ever
  recommend anything. The new coverage leaves realistic gaps, which also
  makes Online Banking Portal's risk score noticeably higher than before
  (a more compelling, defensible demo scenario, not a regression)
- **Tests**: 9 new tests covering the no-candidates case, RBAC, budget
  constraints (including zero budget and defaulting to the org budget),
  and — critically — that reported totals never exceed the baseline
  (44/44 total passing)
- **Frontend**: new "Investments" tab — a budget input, a "Run
  optimization" button, summary cards (investment / risk reduction /
  remaining risk / ROSI), and a candidate table that highlights which
  controls were recommended, with an explicit note that solo reduction
  figures don't simply add up

### Running Phase 5 on top of your existing setup

```bash
cd backend
# with your venv activated
alembic upgrade head      # applies the new Phase 5 tables
python -m app.seed        # adds the 4 candidate controls (skips if already seeded)
uvicorn app.main:app --reload
```

**Important:** if you seeded your database before this phase, your
existing Phase 2 control coverage is the old (over-saturated) version.
Delete `sih_dev.db` and re-run `alembic upgrade head` + `python -m
app.seed` from scratch to get the corrected coverage and a working
optimizer demo — otherwise every asset will already be at the mitigation
cap and the optimizer will have nothing meaningful to recommend.

Frontend: `npm install` (no new packages) then `npm run dev` — a new
"Investments" tab appears in the dashboard nav.

### API examples (Phase 5)

```bash
# List current investment candidates
curl http://localhost:8000/api/v1/investments \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Run the optimizer with a specific budget (admin/ciso/risk_analyst only)
curl -X POST http://localhost:8000/api/v1/optimization/recommend \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"budget": 500000}'

# Run with no budget specified — defaults to the org's annual_cyber_budget
curl -X POST http://localhost:8000/api/v1/optimization/recommend \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'

# View past optimization runs
curl http://localhost:8000/api/v1/optimization/recommendations \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### What's next after Phase 5

- **Phase 6**: The What-If Simulator — let users interactively simulate
  adding/removing a control, fixing a vulnerability, or changing the
  budget, and see the before/after risk, EAL, compliance, and investment
  numbers side by side, reusing the exact same Risk Engine and Optimizer
  built in Phases 3 and 5
