# OrderClerk AI

**Status: working local prototype; fixture workflow implemented and live model verification awaiting an authorized API key.**

Messages contain inconsistent product names and missing quantities, requiring repeated catalogue checks and corrections.

Target: [Hyperbloom September - AI/ML](https://hyperbloom-september.devpost.com/) · [Official rules](https://hyperbloom-september.devpost.com/rules)  
Track: AI/ML  
Deadline: **2026-09-14 23:00 Africa/Lusaka (UTC+2)**, checked 11 September 2026.  
Rewards: Advertised $1,710 value comprises memberships, domains and platform credits in the prize descriptions; no cash payout established.

**Eligibility:** Conditional: high-school/college student event; student status has not been confirmed.

**Focused build estimate:** 4–6 hours for one working input-to-order flow with an available model API; allow additional recording time. This is a planning estimate, not a promise of completion or a prize.

## What is built

Paste a message, extract a proposed order, validate exact aliases and quantities against the catalogue, reserve stock transactionally, and export a picking list. Missing quantities, unsupported products, and shortages become review items. Replaying an external message reference returns the original result without changing stock.

Audience: A small shop owner processing batches of written customer orders.

The current machine has no `OPENAI_API_KEY`, so local evidence uses a deterministic fixture parser that is prominently labeled **unverified** in the UI and API. When an authorized key is available, the application calls the OpenAI Responses API with a strict JSON Schema; all catalogue, price, idempotency, and stock decisions remain in domain code.

## Run locally

Requires Python 3.11+ and no third-party packages.

```sh
cd orderclerk-ai
python3 run.py --port 5184
```

Open `http://127.0.0.1:5184`. The database is created at `var/orderclerk.db`.

For live extraction, configure credentials in the shell (do not add them to tracked files):

```sh
export OPENAI_API_KEY="your-authorized-key"
export OPENAI_MODEL="gpt-5.2"
python3 run.py --port 5184
```

## Test

```sh
python3 scripts/verify.py
```

The runner covers the clear, clarification, replay, shortage, concurrent reservation, and HTTP smoke paths, then writes `submission/TEST_EVIDENCE.json`.

## Files

- [Task specification](docs/SPEC.md)
- [Build plan](docs/BUILD_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Access checklist](docs/ACCESS.md)
- [Demo scenarios](data/scenarios.json)
- [Submission checklist](submission/CHECKLIST.md)
- [Normalized schema](db/schema.sql)
- [Synthetic seed data](db/seed.sql)
- [Constraint checks](db/constraints.json)
- [Submission description](submission/DESCRIPTION.md)
- [Live integration status](docs/ACCESS.md)

## Safety boundaries

- Prices come only from stored integer minor units.
- Supported aliases resolve exactly; the model cannot write directly to the database.
- Missing quantities never receive a silent default.
- `BEGIN IMMEDIATE` serializes reservation decisions against current availability.
- Unique external references and message-to-order constraints make replay idempotent.
- The catalogue and demo messages are synthetic; WhatsApp and production customer data are not connected.

