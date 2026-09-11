# OrderClerk AI

Small shops often receive orders as casual messages: "two rice, an oil," a misspelled product, or a request with no quantity at all. Turning those notes into reliable orders means repeatedly checking a catalogue, asking follow-up questions, calculating totals, and confirming stock. OrderClerk AI is a counter-desk workflow that turns that messy text into a pick-ready order without letting an AI guess become a business fact.

The clerk pastes a message and supplies a stable message reference. A structured extractor proposes product aliases and quantities. Deterministic domain code then accepts only exact catalogue aliases, rejects missing or invalid quantities, reads prices from stored integer minor units, and checks stock. Valid orders are persisted with historical price snapshots, stock is reserved in a SQLite write transaction, and a CSV picking list is available immediately. Unsupported products, ambiguity, and shortages become precise review prompts instead of silent substitutions. Replaying a message reference returns its original result and never reserves stock twice.

The prototype includes a responsive browser interface, a Python HTTP API, a normalized SQLite catalogue and order ledger, and automated tests for clear orders, missing quantities, replay, shortages, concurrent oversell protection, and the HTTP workflow. The synthetic demo catalogue uses Zambian kwacha and contains no real customer data.

AI is meaningful but deliberately bounded: it handles the flexible language problem, while conventional code owns money, inventory, and persistence. The live path uses the OpenAI Responses API with strict JSON Schema structured output. The implementation session did not have an authorized `OPENAI_API_KEY`, so current local evidence uses a deterministic offline fixture parser and labels those results `fixture_unverified`; no live-model performance claim is made.

AI tools disclosure: OpenAI Codex assisted with implementation and documentation. The application includes an OpenAI Responses API integration for order-line extraction. Fixture-based validation is disclosed separately from the still-required live demonstration.
