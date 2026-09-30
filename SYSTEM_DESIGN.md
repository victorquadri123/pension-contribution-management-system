# EPS+ System Design Notes

**Project:** EPS+ Pension Contribution Management System  
**Developer:** Victor Ayomide  
**Role:** Junior Backend Developer (NLPC PFA Assessment)

---

## 1. Solution Architecture Flow

I structured the project using a simple 3-tier pattern to keep logic clean and easy to test:
- **Presentation:** Django Web Views (Bootstrap 5) and REST API (Django REST Framework).
- **Service Layer:** Business rules (age 18–70 checks, 1-per-month contribution rule, benefit vesting, interest accrual).
- **Data Layer:** Django ORM models with database-level constraints.

```mermaid
flowchart TD
    Client["Browser / REST API Client"] --> WebLayer["Web Views & API ViewSets"]
    WebLayer --> ServiceLayer["Services (Member, Contribution, Benefit, Jobs)"]
    ServiceLayer --> ORM["Django ORM Models"]
    ORM --> DB[("Database (SQLite / PostgreSQL)")]
    
    %% Background tasks
    Jobs["Background Jobs (run_jobs CLI / Admin Trigger)"] --> ServiceLayer
```

---

## 2. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    EMPLOYER ||--o{ MEMBER : "employs"
    MEMBER ||--o{ CONTRIBUTION : "remits"
    MEMBER ||--|| BENEFIT_ELIGIBILITY : "tracks"
    MEMBER ||--o{ INTEREST_ACCRUAL : "earns"

    EMPLOYER {
        int id PK
        string company_name
        string registration_number UK
        string status "ACTIVE | SUSPENDED"
        boolean is_deleted
    }

    MEMBER {
        int id PK
        int user_id FK
        int employer_id FK
        string rsa_pin UK
        string nin
        date date_of_birth "18-70 years"
        boolean is_onboarded
        boolean is_deleted
    }

    CONTRIBUTION {
        int id PK
        int member_id FK
        string contribution_type "MONTHLY | VOLUNTARY"
        decimal amount "amount > 0"
        int contribution_year
        int contribution_month "1-12"
        string transaction_reference UK
        string status "PENDING | VALIDATED | FAILED"
        boolean is_deleted
    }

    BENEFIT_ELIGIBILITY {
        int id PK
        int member_id FK
        int months_contributed
        decimal total_contributions_amount
        decimal total_interest_amount
        boolean is_eligible
        string eligibility_type "MINIMUM_SERVICE | RETIREMENT"
    }

    INTEREST_ACCRUAL {
        int id PK
        int member_id FK
        int year
        int month
        decimal principal_balance
        decimal interest_amount
        decimal closing_balance
    }
```

> **Design note:** Models inherit from `BaseModel` for soft-deletion (`is_deleted = True`), ensuring financial audit history is never lost.

---

## 3. Process Flows (Sequence Diagrams)

### 3.1 Member Registration & KYC
```mermaid
sequenceDiagram
    autonumber
    actor User as Member
    participant Svc as MemberService
    participant DB as Database

    User->>Svc: Sign up (Email, Password)
    Svc->>DB: Create User & un-onboarded Member
    User->>Svc: Submit KYC (DOB, 11-digit NIN, Employer)
    Svc->>Svc: Verify Age (18 <= Age <= 70)
    alt Invalid Age
        Svc-->>User: Return error (Must be 18 to 70)
    else Valid
        Svc->>DB: Verify active Employer & generate RSA PIN (PEN10...)
        Svc->>DB: Save Member (is_onboarded = True) & create Benefit record
        Svc-->>User: Setup complete, redirect to Dashboard
    end
```

### 3.2 Monthly Contribution Processing
```mermaid
sequenceDiagram
    autonumber
    actor Contributor as Contributor
    participant Svc as ContributionService
    participant DB as Database

    Contributor->>Svc: Submit Monthly Contribution
    Svc->>Svc: Check amount > 0 and date <= today
    Svc->>DB: Check if MONTHLY contribution already exists for this month/year
    alt Already exists
        Svc-->>Contributor: Error: Monthly contribution already submitted for this period
    else First contribution
        Svc->>DB: Save as PENDING
        Svc->>DB: Validate Employer & Member active -> mark VALIDATED
        Svc-->>Contributor: Success: Contribution credited
    end
```

### 3.3 Voluntary Contribution Processing
```mermaid
sequenceDiagram
    autonumber
    actor Contributor as Contributor
    participant Svc as ContributionService
    participant DB as Database

    Contributor->>Svc: Submit Voluntary Contribution (Amount, Date)
    Svc->>Svc: Validate amount > 0 and date <= today
    Note over Svc,DB: Multiple voluntary contributions allowed in the same month
    Svc->>DB: Save as PENDING -> Validate -> mark VALIDATED
    Svc-->>Contributor: Success: Added to balance
```

### 3.4 Basic Benefit Calculation
```mermaid
sequenceDiagram
    autonumber
    actor System as Job / Admin
    participant Svc as BenefitService
    participant DB as Database

    System->>Svc: evaluate_member_benefit(member)
    Svc->>DB: Count validated monthly contributions & calculate member age
    alt Age >= 50 and Monthly Count >= 1
        Svc->>DB: Set is_eligible = True ("RETIREMENT")
    else Monthly Count >= 60 (5 Years Service)
        Svc->>DB: Set is_eligible = True ("MINIMUM_SERVICE")
    else Not Yet Vested
        Svc->>DB: Set is_eligible = False (track progress X/60)
    end
```

### 3.5 Background Job Execution & Retries
```mermaid
sequenceDiagram
    autonumber
    actor Runner as Job Runner / Admin
    participant Svc as BackgroundJobService
    participant DB as Database

    Runner->>Svc: Run pending contributions check
    Svc->>DB: Fetch PENDING contributions
    loop For each contribution
        alt Member or Employer is inactive
            Svc->>DB: Mark FAILED + log failure reason
        else Valid
            Svc->>DB: Mark VALIDATED + update member totals
        end
    end
    Svc->>DB: Save JobExecutionLog (counts & status)
```

