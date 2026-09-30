# EPS+ Pension Contribution Management System — System Design Document

**Organization:** NLPC PFA Limited  
**Project:** EPS+ (Customer Onboarding, BDRM & Contribution Management)  
**Deliverable:** System Architecture, Domain-Driven Design, Entity Modeling & Process Flows  

---

## 1. Solution Architecture Flow

The system employs a **Clean Layered Architecture** adhering to **Domain-Driven Design (DDD)** and **SOLID principles**. Presentation layers (Web UI and REST API) decouple from business orchestration (Services), domain models, and external storage engines.

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Integration Layer"]
        Browser["Desktop & Mobile Web Browser\n(Bootstrap 5 + Responsive UI)"]
        ExternalAPI["Third-Party Clients / Employers\n(REST API Consumers)"]
        Swagger["Swagger UI / Postman Client\n(/api/docs/)"]
    end

    subgraph PresentationLayer["Presentation Layer (Django / DRF)"]
        WebViews["Web Views & Controllers\n(Login, Dashboard, Statements)"]
        APIViewSets["REST API ViewSets\n(/api/v1/members, /contributions)"]
        Middlewares["Global Exception & Security Middleware\n(CSRF, Auth, Rate Limiting)"]
    end

    subgraph ApplicationLayer["Application & Business Logic Layer (Services)"]
        MemberService["Member & Onboarding Service\n(Age 18-70 & RSA PIN Generation)"]
        ContributionService["Contribution Service\n(1-per-month check & Statements)"]
        BenefitService["Benefit Eligibility Engine\n(Vesting & PRA 2014 Rules)"]
        JobService["Background Job Automation\n(Validation, Compounding ROI, Retries)"]
    end

    subgraph DomainLayer["Domain & Data Access Layer (ORM / Repository)"]
        MemberModel["Member & User Aggregate Root"]
        EmployerModel["Employer Entity"]
        ContributionModel["Contribution Entity (Constraints)"]
        BenefitModel["BenefitEligibility Entity"]
        JobLogModel["JobExecution & Notification Logs"]
    end

    subgraph StorageLayer["Data & Persistence Layer"]
        Database[("Relational Database\n(SQLite / PostgreSQL)")]
    end

    Browser -->|HTTP GET/POST| WebViews
    ExternalAPI -->|JSON REST Requests| APIViewSets
    Swagger -->|OpenAPI 3.0 Requests| APIViewSets

    WebViews --> Middlewares
    APIViewSets --> Middlewares

    Middlewares --> MemberService
    Middlewares --> ContributionService
    Middlewares --> BenefitService
    Middlewares --> JobService

    MemberService --> MemberModel
    ContributionService --> ContributionModel
    BenefitService --> BenefitModel
    JobService --> JobLogModel
    JobService --> ContributionModel

    MemberModel --> Database
    EmployerModel --> Database
    ContributionModel --> Database
    BenefitModel --> Database
    JobLogModel --> Database

    %% Highlight async background processing
    JobService -.->|Scheduled / Async Trigger| ContributionModel
    JobService -.->|Compounding Calculation| BenefitModel
```

---

## 2. Entity-Relationship Diagram (ERD)

The database schema models the lifecycle of contributors, their employers, mandatory and voluntary remittances, compounding returns, and benefit qualification.

```mermaid
erDiagram
    EMPLOYER ||--o{ MEMBER : "employs (1 : N)"
    MEMBER ||--o{ CONTRIBUTION : "remits (1 : N)"
    MEMBER ||--|| BENEFIT_ELIGIBILITY : "vests into (1 : 1)"
    MEMBER ||--o{ INTEREST_ACCRUAL : "earns (1 : N)"

    EMPLOYER {
        int id PK
        string company_name "Indexed"
        string registration_number UK "CAC / RC (Indexed)"
        string email UK
        string phone_number
        text address
        string status "ACTIVE | SUSPENDED"
        boolean is_active
        datetime created_at
        datetime updated_at
        boolean is_deleted "Soft-delete"
    }

    MEMBER {
        int id PK
        int user_id FK, UK "1:1 with CustomUser"
        int employer_id FK "Required for remittance"
        string rsa_pin UK "PEN10XXXXXXXX (Indexed)"
        string nin "11 numeric digits"
        date date_of_birth "Restricted: 18 - 70 years"
        string gender "MALE | FEMALE"
        text address
        string status "ACTIVE | SUSPENDED | RETIRED"
        boolean is_onboarded "KYC Flag"
        boolean is_deleted "Soft-delete"
        datetime deleted_at
    }

    CONTRIBUTION {
        int id PK
        int member_id FK "Indexed"
        string contribution_type "MONTHLY | VOLUNTARY"
        decimal amount "Amount > 0.00"
        int contribution_year
        int contribution_month "1 to 12"
        date payment_date "Must not be future date"
        string transaction_reference UK "Indexed"
        string status "PENDING | VALIDATED | FAILED"
        text failure_reason
        datetime validated_at
        boolean is_deleted "Soft-delete"
    }

    BENEFIT_ELIGIBILITY {
        int id PK
        int member_id FK, UK
        int months_contributed "Validated monthly count"
        decimal total_contributions_amount
        decimal total_interest_amount
        boolean is_eligible "Vested flag"
        string eligibility_type "MINIMUM_SERVICE | RETIREMENT | NONE"
        text status_notes
        datetime last_evaluated_at
    }

    INTEREST_ACCRUAL {
        int id PK
        int member_id FK
        int year
        int month
        decimal principal_balance
        decimal annual_rate_percent "e.g. 10.5%"
        decimal interest_amount "Monthly compounded ROI"
        decimal closing_balance
        datetime applied_at
    }
```

---

## 3. Process Flows (Sequence Diagrams)

### 3.1 Member Registration & Onboarding Process
This flow implements the 2-step onboarding pattern: simple initial registration followed by regulatory KYC verification (Age 18–70, 11-digit NIN, active employer association, and RSA PIN generation).

```mermaid
sequenceDiagram
    autonumber
    actor User as Contributor / Applicant
    participant Portal as Web Portal / API
    participant MemberSvc as MemberService
    participant DB as Relational Database

    User->>Portal: Submit Basic Info (Name, Email, Phone, Password)
    Portal->>MemberSvc: register_user(email, password, ...)
    MemberSvc->>DB: Check email uniqueness
    MemberSvc->>DB: Insert CustomUser & un-onboarded Member (is_onboarded=False)
    MemberSvc-->>Portal: User created & auto-logged in
    Portal-->>User: Redirect to Onboarding (KYC) Screen

    User->>Portal: Submit KYC (DOB, NIN, Select Employer, Address)
    Portal->>MemberSvc: complete_onboarding(member, dob, nin, employer_id)
    MemberSvc->>MemberSvc: Validate Age: 18 <= Age <= 70
    alt Under 18 or Over 70
        MemberSvc-->>Portal: Error: "Member must be between 18 and 70 years"
        Portal-->>User: Show validation alert
    else Valid Age & 11-digit NIN
        MemberSvc->>DB: Verify Employer is_active and status == ACTIVE
        MemberSvc->>MemberSvc: Generate unique RSA PIN (PEN10XXXXXXXX)
        MemberSvc->>DB: Update Member (is_onboarded=True, rsa_pin, status=ACTIVE)
        MemberSvc->>DB: Initialize BenefitEligibility record
        MemberSvc-->>Portal: Onboarding Successful
        Portal-->>User: Redirect to Dashboard with Welcome & RSA PIN
    end
```

---

### 3.2 Monthly Contribution Processing (1-Per-Month Enforced)

```mermaid
sequenceDiagram
    autonumber
    actor User as Contributor / Employer
    participant Portal as Web / API
    participant ContribSvc as ContributionService
    participant DB as Database
    participant JobRunner as Automation Engine

    User->>Portal: Submit Contribution (Type=MONTHLY, Amount, Month, Year, Date)
    Portal->>ContribSvc: record_contribution(member, MONTHLY, amount, month, year, date)
    ContribSvc->>ContribSvc: Validate amount > 0 and date <= today
    ContribSvc->>DB: Check existing MONTHLY contribution for (member, month, year)
    alt Monthly contribution already exists for this calendar month
        DB-->>ContribSvc: Existing record found
        ContribSvc-->>Portal: Error: "A monthly contribution for Month/Year already exists."
        Portal-->>User: Rejection message: Use Voluntary Contribution for extra deposits
    else No duplicate monthly record
        ContribSvc->>DB: Insert Contribution (status=PENDING, txn_ref=TXN-XXXXXXXX)
        ContribSvc->>JobRunner: Trigger Validation Worker
        JobRunner->>DB: Verify Employer is eligible and Member is active
        JobRunner->>DB: Update Contribution status=VALIDATED, validated_at=now
        JobRunner-->>Portal: Validated Successfully
        Portal-->>User: Confirmation: Contribution Validated & Credited to RSA
    end
```

---

### 3.3 Voluntary Contribution Processing (AVC - Multiple Allowed)

```mermaid
sequenceDiagram
    autonumber
    actor Contributor as Contributor
    participant Portal as Web / API
    participant ContribSvc as ContributionService
    participant DB as Database

    Contributor->>Portal: Submit Voluntary Contribution (Type=VOLUNTARY, Amount, Date)
    Portal->>ContribSvc: record_contribution(member, VOLUNTARY, amount, month, year, date)
    ContribSvc->>ContribSvc: Validate amount > 0 and date <= today
    Note over ContribSvc,DB: Multiple voluntary contributions permitted within same month
    ContribSvc->>DB: Insert Contribution (status=PENDING, type=VOLUNTARY)
    ContribSvc->>DB: Run background validation against active account
    DB-->>ContribSvc: Validated
    ContribSvc-->>Portal: Created & Validated
    Portal-->>Contributor: Voluntary contribution successfully added to RSA balance
```

---

### 3.4 Benefit Eligibility Calculation

```mermaid
sequenceDiagram
    autonumber
    actor Evaluator as Scheduled Job / Officer
    participant BenefitSvc as BenefitEligibility Engine
    participant DB as Database

    Evaluator->>BenefitSvc: evaluate_member_benefit(member_id)
    BenefitSvc->>DB: Query validated monthly contributions count
    BenefitSvc->>DB: Aggregate total validated contributions + accrued interest
    BenefitSvc->>DB: Fetch member Date of Birth (calculate age)
    
    alt Member Age >= 50 and Monthly Count >= 1
        BenefitSvc->>DB: Set is_eligible=True, type=RETIREMENT ("Retirement Age Qualified")
    else Monthly Count >= 60 (5 Years Minimum Service)
        BenefitSvc->>DB: Set is_eligible=True, type=MINIMUM_SERVICE ("60 Months Vesting Reached")
    else Under 60 Months & Under 50 Years Old
        BenefitSvc->>DB: Set is_eligible=False, type=NONE, record progress (X/60 months)
    end
    BenefitSvc-->>Evaluator: Updated Benefit Eligibility Record
```

---

### 3.5 Background Job Execution & Failure Handling

```mermaid
sequenceDiagram
    autonumber
    participant Scheduler as Background Job Engine
    participant JobService as BackgroundJobService
    participant DB as Database
    participant Notification as Notification Audit Log

    Scheduler->>JobService: validate_pending_contributions()
    JobService->>DB: Create JobExecutionLog (status=RUNNING)
    JobService->>DB: Fetch all Contribution records where status=PENDING
    loop For Each Pending Contribution
        JobService->>DB: Check Member.status and Employer.status
        alt Member or Employer Suspended / Inactive
            JobService->>DB: Set Contribution.status=FAILED, failure_reason="Employer/Member inactive"
            JobService->>Notification: Insert NotificationLog (type=CONTRIBUTION_FAILED)
        else All Checks Pass
            JobService->>DB: Set Contribution.status=VALIDATED, validated_at=now
            JobService->>Notification: Insert NotificationLog (type=CONTRIBUTION_VALIDATED)
            JobService->>DB: Recalculate BenefitEligibility for member
        end
    end
    JobService->>DB: Update JobExecutionLog (status=SUCCESS, items_processed=N)

    Scheduler->>JobService: retry_failed_transactions()
    JobService->>DB: Query FAILED contributions where Employer/Member is now ACTIVE
    JobService->>DB: Reset status=PENDING and re-run validation pipeline
```

---

## 4. Interview Follow-Up Questions (Detailed Rationale)

### Question 1: Architecture Decisions
- **Chosen Architecture:** Clean Layered Architecture with Domain-Driven Design (DDD). We partitioned the application into core domain aggregates (`Member`, `Employer`, `Contribution`, `BenefitEligibility`), isolated business services (`MemberService`, `ContributionService`, `BackgroundJobService`), and presentation entry points (Bootstrap UI views and REST ViewSets).
- **Alternative Approaches Considered:**
  1. *Microservices:* Considered separating Members, Contributions, and Background Jobs into distinct microservices. However, for a single cohesive pension domain, a microservices setup introduces unnecessary distributed transaction overhead, network latency, and deployment complexity.
  2. *Standard Monolithic Fat-Models:* Considered embedding all business rules in Django model methods or views. This was rejected because business logic quickly leaks into HTTP controllers, making unit testing fragile and violating Single Responsibility.
- **Design Patterns Implemented:**
  - **Service Layer Pattern:** Encapsulates transaction management, validation orchestrations, and event triggers.
  - **Aggregate Root & Value Objects:** `Member` acts as an aggregate root coordinating profile state, RSA PIN generation, and benefit recalculation.
  - **Soft-Delete Pattern:** Implemented via `BaseModel` and custom `SoftDeleteManager` to ensure regulatory auditability (PRA 2014 forbids hard deletion of financial records).

### Question 2: Technical Choices
- **Database & ORM Design:**
  - Composite unique constraint `UniqueConstraint(fields=['member', 'contribution_year', 'contribution_month'], condition=Q(contribution_type='MONTHLY'))` guarantees that no race condition can ever produce duplicate monthly contributions at the database engine level.
  - Indexing on `rsa_pin`, `transaction_reference`, `(member_id, status)`, and `registration_number` for fast lookups.
- **Background Jobs Strategy:**
  - Modeled with idempotent job runners that can execute via Celery/Huey workers, cron schedules, or the PFA Operations Portal.
  - Every job writes to `JobExecutionLog` and `NotificationLog` with execution duration, count of processed items, and explicit failure reasons.
- **Error Handling Strategy:**
  - Defensive model and serializer validation raising structured `ValidationError` with distinct field keys.
  - Global transaction rollbacks via `@transaction.atomic` ensure that no partial writes occur if onboarding or contribution validation fails midway.

### Question 3: Scalability Considerations
- **Database Optimization:**
  - Read queries utilize `select_related('user', 'employer')` to prevent the N+1 query problem across high-volume listings.
  - Pre-aggregated balance calculations and indexed temporal ranges for Statement of Account generation.
- **Handling Large Datasets:**
  - Batch chunking (`QuerySet.iterator(chunk_size=1000)`) for monthly interest accrual across hundreds of thousands of members.
  - Distributed background workers handling contribution validation queues concurrently without locking member rows.
- **Caching Strategy:**
  - Cache member dashboard balance summaries with TTL invalidation triggered only when new contributions are validated or interest is credited.

### Question 4: Security Implementation
- **Authentication & Authorization:**
  - Django's battle-tested session and PBKDF2/SHA256 password hashing.
  - Role-Based Access Control (RBAC): Contributors access only their own dashboard and statements; PFA Administrators access the Operations Portal and background job controls.
- **Data Protection:**
  - PII masking on National Identity Numbers (NIN) in public responses.
  - Complete CSRF token verification across all POST, PUT, and DELETE forms and API requests.
- **API Security:**
  - Input sanitization through DRF serializers, SQL parameterization via ORM to completely eliminate SQL injection, and rate-limiting throttling classes to prevent brute-force attacks.
