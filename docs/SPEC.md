# Task specification

## User and outcome

A small shop owner processing batches of written customer orders.

Paste a message, use AI to extract a proposed order, validate against the catalogue and stock, then save and export valid orders.

## Agent or operator duties

1. Extract products and quantities from a pasted message using a real model.
2. Resolve only supported product aliases against the catalogue.
3. Ask for missing or ambiguous information.
4. Calculate prices from stored prices using integer minor currency units.
5. Reserve stock and generate a picking list for valid orders.

## Rules

- Do not invent prices, products, quantities, customers or discounts.
- Missing quantities require clarification.
- Price snapshots on order lines preserve the order's historical price.
- Duplicate message identifiers cannot create duplicate orders.
- Reserve stock transactionally; test concurrent requests before claiming overselling protection.
- No WhatsApp integration is included in the first prototype.
- The existing Duka application is separate; any future code reuse must be disclosed and comply with both events.

## Acceptance criteria

- [x] A clear message becomes persisted order lines and a picking list.
- [x] An ambiguous product or absent quantity becomes a review item.
- [x] Replaying a message does not create another order.
- [x] Money calculations use integer minor units and match the catalogue.
- [ ] The final demonstration includes a real model call; fixture results are labeled.

The first four criteria are implemented with automated coverage. The live-model criterion is blocked only by missing local `OPENAI_API_KEY` access; fixture output is labeled `fixture_unverified` throughout.

## Demonstration value

Show a messy order, a precise clarification, and reliable persistence after replay rather than only a generated response.

Use the [sample scenarios](../data/scenarios.json) to define expected behavior. Sample organizations, records and quantities are fictional. No measured impact, WhatsApp connection, or verified live model result is claimed.
