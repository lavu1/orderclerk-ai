PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS customers (
 id INTEGER PRIMARY KEY, display_name TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY, sku TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 unit TEXT NOT NULL, price_minor INTEGER NOT NULL CHECK(price_minor >= 0),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS product_aliases (
 alias TEXT PRIMARY KEY COLLATE NOCASE,
 product_id INTEGER NOT NULL REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS stock_movements (
 id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id),
 quantity_delta INTEGER NOT NULL CHECK(quantity_delta <> 0),
 reason TEXT NOT NULL CHECK(reason IN ('opening','receipt','adjustment','sale')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS incoming_messages (
 id INTEGER PRIMARY KEY, external_ref TEXT NOT NULL UNIQUE,
 customer_id INTEGER NOT NULL REFERENCES customers(id), body TEXT NOT NULL,
 body_sha256 TEXT NOT NULL,
 extraction_mode TEXT NOT NULL CHECK(extraction_mode IN ('openai','ollama','fixture_unverified')),
 model_name TEXT NOT NULL,
 extraction_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','review','processed')),
 review_reason TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS orders (
 id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL UNIQUE REFERENCES incoming_messages(id),
 currency TEXT NOT NULL DEFAULT 'ZMW' CHECK(length(currency)=3),
 status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','reserved','collected','cancelled')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS order_items (
 id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
 product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL CHECK(quantity>0),
 unit_price_minor INTEGER NOT NULL CHECK(unit_price_minor>=0),
 UNIQUE(order_id,product_id)
);
CREATE TABLE IF NOT EXISTS stock_reservations (
 order_item_id INTEGER PRIMARY KEY REFERENCES order_items(id),
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','released','fulfilled'))
);
CREATE TABLE IF NOT EXISTS order_events (
 id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
 event_type TEXT NOT NULL, detail TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS stock_product_idx ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS order_item_product_idx ON order_items(product_id);
CREATE INDEX IF NOT EXISTS message_customer_idx ON incoming_messages(customer_id);
CREATE INDEX IF NOT EXISTS message_status_idx ON incoming_messages(status);
CREATE VIEW IF NOT EXISTS order_totals AS
 SELECT o.id AS order_id, o.currency, COALESCE(SUM(i.quantity*i.unit_price_minor),0) AS total_minor
 FROM orders o LEFT JOIN order_items i ON i.order_id=o.id GROUP BY o.id;
CREATE VIEW IF NOT EXISTS product_availability AS
 SELECT p.id AS product_id,
 COALESCE((SELECT SUM(m.quantity_delta) FROM stock_movements m WHERE m.product_id=p.id),0)
 - COALESCE((SELECT SUM(i.quantity) FROM order_items i JOIN stock_reservations r ON r.order_item_id=i.id WHERE i.product_id=p.id AND r.status='active'),0) AS available_quantity
 FROM products p;
