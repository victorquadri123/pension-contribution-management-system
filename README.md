# EPS+ Pension Contribution Management System

A pension contribution and member management platform built with Django, Django REST Framework, and SQLite for the NLPC PFA technical assessment.

It covers contributor onboarding (KYC), employer tracking, monthly and voluntary contribution remittances, Nigerian Pension Reform Act (PRA 2014) benefit eligibility, background jobs for automated validation and interest calculation, and a RESTful API with OpenAPI/Swagger docs.

---

## Quickstart

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations and seed sample data
python manage.py migrate
python manage.py seed_demo_data

# 4. Start the server
python manage.py runserver
```

Once running, access the platform at:
- **Web App:** http://127.0.0.1:8000/
- **Operations Portal (Admin):** http://127.0.0.1:8000/portal/
- **Swagger API Docs:** http://127.0.0.1:8000/api/docs/
- **ReDoc API Docs:** http://127.0.0.1:8000/api/redoc/
- **Django Admin:** http://127.0.0.1:8000/admin/

---

## Demo Accounts

The `seed_demo_data` command creates sample employers (Dangote, Zenith Bank, MTN, NLPC PFA) and accounts with seeded history:

| Account | Email | Password | Role / Notes |
|:---|:---|:---|:---|
| **Admin** | `victorayomide319@gmail.com` | `moneySTAND123@` | Full access to Operations Portal & background jobs |
| **Contributor** | `moneystand123@gmail.com` | `moneySTAND123@` | Primary contributor account |
| **Admin (Backup)** | `admin@nlpcpfa.com` | `moneySTAND123@` | Standard PFA admin officer |
| **Contributor (Active)** | `olumide.adebayo@gmail.com` | `moneySTAND123@` | Active contributor, 24 months history |
| **Contributor (Retirement)** | `babajide.sanusi@outlook.com` | `moneySTAND123@` | Age 54, 65 months history (Vested / Qualified) |
| **Contributor (Younger)** | `chioma.okonkwo@yahoo.com` | `moneySTAND123@` | 12 months history |



---

## System Design & Architecture
For the complete solution architecture diagram, entity relationship diagram (ERD), and process sequence flows, see [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md).

---

## Core Engineering Decisions

### 1. Database-Enforced Contribution Rules
- **Monthly Contributions:** Enforced via a database `UniqueConstraint` on `(member, contribution_year, contribution_month)` where `contribution_type='MONTHLY'` and `is_deleted=False`. This guarantees at the database level that race conditions cannot insert duplicate monthly contributions for the same calendar month.
- **Voluntary Contributions (AVC):** Multiple voluntary contributions are permitted within the same period.
- **Validation:** Amounts must be strictly $> 0.00$, and payment dates cannot be in the future.

### 2. Benefit Eligibility (PRA 2014)
- Contributor eligibility is evaluated against two legal rules:
  1. **Minimum Service:** 60 validated contribution months (5 years).
  2. **Retirement Age:** Age $\ge 50$ years with active contributions.
- Real-time progress tracking calculates percentage toward vesting threshold.

### 3. Progressive Onboarding & Security
- **Guided Onboarding:** New users can sign up and immediately land on their dashboard. If KYC is incomplete, an action banner prompts them to complete their profile (Employer, DOB, 11-digit NIN), while remittance actions remain guarded until an official `PEN10...` RSA PIN is generated.
- **Admin Endpoint Protection:** Non-admin users attempting to open `/portal/` receive a real HTTP 404 Not Found rather than a redirect, preventing unauthorized endpoint enumeration.

### 4. Background Jobs Engine
Background jobs can be run via CLI, REST API, or the web operations portal:
- **Validation Job:** Verifies pending contributions against active employer and member status.
- **Interest Accrual:** Computes periodic compound return on investment (ROI) across active balances.
- **Retry Job:** Retries previously failed remittances once employer/member status is restored.
- **Audit Logs:** Every execution and alert is logged in `JobExecutionLog` and `NotificationLog`.

Run jobs via CLI:
```bash
python manage.py run_jobs --job=all         # Run all jobs
python manage.py run_jobs --job=validate    # Run contribution validation
python manage.py run_jobs --job=interest    # Accrue monthly interest
python manage.py run_jobs --job=retry       # Retry failed transactions
```

---

## API & Postman

- **Interactive Docs:** Visit `/api/docs/` for Swagger UI with test payloads and schema definitions.
- **Postman:** A ready-to-import [`postman_collection.json`](./postman_collection.json) is included in the project root with pre-configured requests and environments for all endpoints.

---

## Testing & Coverage

Run the test suite with coverage:
```bash
coverage run -m pytest
coverage report -m
```

All 36 tests pass across member validation, contribution constraints, benefit calculations, background automation, web views, and REST endpoints (current test coverage: **86%**).

---

## Docker Setup (Optional)

To run the application containerized:
```bash
docker-compose up --build
```
The app will be available at `http://localhost:8000`.
