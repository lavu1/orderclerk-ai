# Access and eligibility

Rechecked on 11 September 2026 against the live [overview](https://hyperbloom-september.devpost.com/) and [rules](https://hyperbloom-september.devpost.com/rules).

Conditional: high-school/college student event; student status has not been confirmed.

- [ ] Confirm student eligibility.
- [ ] One working model API/provider and a locally configured credential. `OPENAI_API_KEY` was absent during implementation.
- [ ] Synthetic product catalogue and customer messages supplied in this workspace.

## Exact live-integration access needed

1. An OpenAI API key authorized for the Responses API, supplied only as `OPENAI_API_KEY` in the local shell.
2. Access to the configured `OPENAI_MODEL` (`gpt-5.2` by default; override for the authorized account if needed).
3. Outbound HTTPS access to `https://api.openai.com/v1/responses`.

Without that access the app automatically runs `fixture_unverified`; the interface and API label every resulting extraction. Fixture tests verify the surrounding business workflow but do not establish live model quality.

Do not copy credentials into tracked project files or submission materials. The checked-in `.env.example` contains names and defaults only; this app does not load `.env` files automatically.
