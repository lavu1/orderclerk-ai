const money = new Intl.NumberFormat("en-ZM", { style: "currency", currency: "ZMW" });
const scenarios = {
  clear: "Please pack 2 bags of rice and 1 bottle of oil.",
  missing: "I want rice.",
  stock: "Please pack 5 bottles of oil.",
};

const form = document.querySelector("#order-form");
const submitButton = document.querySelector("#submit-button");
const resultEmpty = document.querySelector("#result-empty");
const resultContent = document.querySelector("#result-content");

function nextReference() {
  return `COUNTER-${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

function formatMinor(value) {
  return money.format(value / 100);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function request(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed.");
  return payload;
}

function renderProvider(provider) {
  const pill = document.querySelector("#provider-pill");
  pill.textContent = provider.label;
  pill.classList.toggle("live", !provider.unverified);
}

function renderState(state) {
  renderProvider(state.provider);
  document.querySelector("#metric-messages").textContent = state.stats.total_messages;
  document.querySelector("#metric-orders").textContent = state.stats.reserved_orders;
  document.querySelector("#metric-review").textContent = state.stats.review_messages;
  document.querySelector("#catalogue").innerHTML = state.catalogue.map((item) => `
    <div class="catalogue-row">
      <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.sku)} / per ${escapeHtml(item.unit)}</small></div>
      <span class="price">${formatMinor(item.price_minor)}</span>
      <span class="stock-count">${item.available_quantity} left</span>
    </div>
  `).join("");

  const events = [
    ...state.orders.map((order) => ({
      id: `#${order.id}`,
      title: `${order.customer} / ${formatMinor(order.total_minor)}`,
      detail: `${order.line_count} line(s) reserved`,
      sort: order.created_at,
    })),
    ...state.reviews.map((review) => ({
      id: "REVIEW",
      title: review.customer,
      detail: review.review_items[0]?.message || "Needs clerk review",
      sort: review.created_at,
    })),
  ].sort((a, b) => b.sort.localeCompare(a.sort)).slice(0, 8);

  document.querySelector("#activity").innerHTML = events.length ? events.map((event) => `
    <div class="activity-item">
      <code>${escapeHtml(event.id)}</code>
      <strong>${escapeHtml(event.title)}</strong>
      <span>${escapeHtml(event.detail)}</span>
    </div>
  `).join("") : '<p class="activity-empty">No desk activity yet. Process the first message above.</p>';
}

function renderResult(result) {
  resultEmpty.hidden = true;
  resultContent.hidden = false;
  const replay = result.replayed ? " / replay returned without a duplicate" : "";
  const warning = result.extraction.unverified
    ? '<p class="fixture-warning">Fixture result: extraction behavior is an offline demo and has not been verified against a live model.</p>'
    : "";
  if (result.outcome === "reserved") {
    const lines = result.order.items.map((item) => `
      <div class="line-item">
        <div><strong>${item.quantity} x ${escapeHtml(item.name)}</strong><br><span>${escapeHtml(item.sku)} / ${formatMinor(item.unit_price_minor)} each</span></div>
        <strong>${formatMinor(item.line_total_minor)}</strong>
      </div>
    `).join("");
    resultContent.innerHTML = `
      <div class="decision-banner">Order #${result.order.id} reserved</div>
      <p class="decision-meta">${escapeHtml(result.message.external_ref)}${replay}</p>
      ${lines}
      <div class="total-row"><span>Total</span><strong>${formatMinor(result.order.total_minor)}</strong></div>
      <a class="download-link" href="/api/orders/${result.order.id}/picking-list.csv">Download picking list -&gt;</a>
      ${warning}
    `;
  } else {
    const notes = result.review_items.map((item) => `<p class="review-note">${escapeHtml(item.message)}</p>`).join("");
    resultContent.innerHTML = `
      <div class="decision-banner review">Clerk review required</div>
      <p class="decision-meta">${escapeHtml(result.message.external_ref)}${replay}</p>
      ${notes}
      ${warning}
    `;
  }
}

async function refresh() {
  try {
    renderState(await request("/api/state"));
  } catch (error) {
    document.querySelector("#provider-pill").textContent = "Service unavailable";
  }
}

document.querySelector("#external-ref").value = nextReference();
document.querySelectorAll(".scenario").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector("#message").value = scenarios[button.dataset.scenario];
    document.querySelector("#external-ref").value = nextReference();
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  submitButton.firstElementChild.textContent = "Checking message...";
  try {
    const result = await request("/api/orders/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        external_ref: document.querySelector("#external-ref").value,
        customer: document.querySelector("#customer").value,
        message: document.querySelector("#message").value,
      }),
    });
    renderResult(result);
    await refresh();
  } catch (error) {
    resultEmpty.hidden = true;
    resultContent.hidden = false;
    resultContent.innerHTML = `<div class="decision-banner review">Processing stopped</div><p class="review-note">${escapeHtml(error.message)}</p>`;
  } finally {
    submitButton.disabled = false;
    submitButton.firstElementChild.textContent = "Interpret & reserve";
  }
});

refresh();
