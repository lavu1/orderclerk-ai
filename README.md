# OrderClerk AI

**[Watch the public demo](https://youtu.be/7-kNizNMjG0) · [Browse source](https://github.com/lavu1/orderclerk-ai)**
**Status: working local prototype with four verified local-model scenarios and nine passing automated tests.**

Messages contain inconsistent product names and missing quantities, requiring repeated catalogue checks and corrections.

Target: [Hyperbloom September - AI/ML](https://hyperbloom-september.devpost.com/) · [Official rules](https://hyperbloom-september.devpost.com/rules)  
Track: AI/ML  
Deadline: **2026-09-14 23:00 Africa/Lusaka (UTC+2)**, checked 11 September 2026.  
Rewards: Advertised $1,710 value comprises memberships, domains and platform credits in the prize descriptions; no cash payout established.

**Eligibility:** The saved Devpost profile identifies the entrant as a college student; event registration and required agreement remain pending.

**Focused build estimate:** 4–6 hours for one working input-to-order flow with an available model API; allow additional recording time. This is a planning estimate, not a promise of completion or a prize.

## What is built

Paste a message, extract a proposed order, validate exact aliases and quantities against the catalogue, reserve stock transactionally, and export a picking list. Missing quantities, unsupported products, and shortages become review items. Replaying an external message reference returns the original result without changing stock.

Audience: A small shop owner processing batches of written customer orders.

The verified AI path uses Ollama with `qwen2.5:3b`. The model identifies order lines; code extracts explicit quantities adjacent to a supported product alias in the original message, reads prices from the catalogue and transactionally reserves stock. A model-invented quantity cannot supply a missing number. Conservative quantity matching currently supports digits or English one through ten; unsupported or ambiguous phrasing stays in review. See [live evidence](submission/LIVE_MODEL_EVIDENCE.json).

## Run locally

Requires Python 3.11+ and no third-party packages.

```sh
cd orderclerk-ai
python3 run.py --port 5184
```

Open `http://127.0.0.1:5184`. The database is created at `var/orderclerk.db`.

For the verified local AI path, install Ollama from its official distribution, start `ollama serve`, then:

```sh
ollama pull qwen2.5:3b
export ORDERCLERK_PROVIDER=ollama
export ORDERCLERK_MODEL=qwen2.5:3b
python3 run.py --port 5184
```

This needs sufficient memory for the approximately 1.9 GB model and runtime. No paid API key is required. Without a configured provider, the application uses a visibly labeled deterministic fixture parser. The optional OpenAI Responses integration (`OPENAI_API_KEY`, `OPENAI_MODEL`) remains implemented but has not been live-verified. Do not commit credentials.

## Test

```sh
python3 scripts/verify.py
```

The runner covers clear orders, review, replay, shortages, concurrent reservations, quantity grounding, database migration and HTTP. It writes `submission/TEST_EVIDENCE.json`. To reproduce four isolated real-model cases while Ollama is running, run `python3 scripts/verify_live.py`. Live model results are kept separately from offline tests.

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

