from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_DIR / "var" / "orderclerk.db"
SCHEMA_PATH = PROJECT_DIR / "db" / "schema.sql"
SEED_PATH = PROJECT_DIR / "db" / "seed.sql"
WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class OrderClerkError(Exception):
    """A safe, user-facing workflow error."""


class ModelAccessError(OrderClerkError):
    """The configured live model could not complete extraction."""


@dataclass(frozen=True)
class Extraction:
    items: list[dict[str, Any]]
    notes: list[str]
    mode: str
    model: str
    unverified: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "notes": self.notes,
            "mode": self.mode,
            "model": self.model,
            "unverified": self.unverified,
        }


def normalize_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def connect_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=8, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 8000")
    return connection


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(db_path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        stored = connection.execute("SELECT sql FROM sqlite_master WHERE name='incoming_messages'").fetchone()[0]
        if "'ollama'" not in stored:
            new_definition = SCHEMA_PATH.read_text().split("CREATE TABLE IF NOT EXISTS incoming_messages (", 1)[1].split(");", 1)[0]
            connection.execute("PRAGMA foreign_keys = OFF")
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("CREATE TABLE incoming_messages_new (" + new_definition + ")")
                connection.execute("INSERT INTO incoming_messages_new SELECT * FROM incoming_messages")
                connection.execute("DROP TABLE incoming_messages")
                connection.execute("ALTER TABLE incoming_messages_new RENAME TO incoming_messages")
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise OrderClerkError("Database upgrade failed its relationship checks.")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        product_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            connection.executescript(SEED_PATH.read_text(encoding="utf-8"))


class FixtureExtractor:
    """Small deterministic parser for offline demos. It is not a model."""

    mode = "fixture_unverified"
    model = "fixture-v1"
    unverified = True

    def extract(self, message: str, catalogue: list[dict[str, Any]]) -> Extraction:
        lowered = normalize_alias(message)
        items: list[dict[str, Any]] = []
        by_product: dict[int, list[str]] = {}
        names: dict[int, str] = {}
        for row in catalogue:
            by_product.setdefault(row["id"], []).append(row["alias"])
            names[row["id"]] = row["name"]

        number_words = "|".join(WORD_NUMBERS)
        quantity_token = rf"(?P<qty>\d+|{number_words})"
        unit_words = r"(?:bags?|bottles?|packs?|units?|pieces?|pcs?)"
        for product_id, aliases in by_product.items():
            matched_quantity: int | None = None
            matched = False
            for alias in sorted(aliases, key=len, reverse=True):
                alias_pattern = re.escape(normalize_alias(alias)).replace(r"\ ", r"\s+")
                pattern = rf"(?:{quantity_token}\s*(?:{unit_words}\s*)?(?:of\s+)?)?\b{alias_pattern}s?\b"
                found = re.search(pattern, lowered, re.IGNORECASE)
                if not found:
                    continue
                matched = True
                token = found.groupdict().get("qty")
                if token is not None:
                    matched_quantity = int(token) if token.isdigit() else WORD_NUMBERS[token]
                break
            if matched:
                items.append({"product": names[product_id], "quantity": matched_quantity})

        notes = ["Offline fixture parser used; a live model call has not been verified."]
        return Extraction(items, notes, self.mode, self.model, self.unverified)


class OpenAIExtractor:
    mode = "openai"
    unverified = False

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def extract(self, message: str, catalogue: list[dict[str, Any]]) -> Extraction:
        accepted_aliases = sorted({row["alias"] for row in catalogue}, key=str.casefold)
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product": {"type": "string"},
                            "quantity": {"type": ["integer", "null"]},
                        },
                        "required": ["product", "quantity"],
                        "additionalProperties": False,
                    },
                },
                "notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["items", "notes"],
            "additionalProperties": False,
        }
        payload = {
            "model": self.model,
            "instructions": (
                "Extract order lines from the customer message. Use only a listed catalogue alias. "
                "Never infer a missing quantity; use null. Do not invent products, prices, customers, "
                "discounts, or substitutions. Notes should briefly flag ambiguity."
            ),
            "input": (
                "Catalogue aliases:\n"
                + json.dumps(accepted_aliases, ensure_ascii=False)
                + "\n\nCustomer message:\n"
                + message
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "order_extraction",
                    "strict": True,
                    "schema": schema,
                }
            },
            "store": False,
        }
        request = Request(
            f"{self.base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise ModelAccessError(f"OpenAI extraction failed with HTTP {error.code}.") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ModelAccessError("OpenAI extraction could not be completed.") from error

        output_text = data.get("output_text")
        if not output_text:
            for item in data.get("output", []):
                if item.get("type") != "message":
                    continue
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        output_text = content.get("text")
                        break
        if not output_text:
            raise ModelAccessError("OpenAI returned no structured extraction text.")
        try:
            parsed = json.loads(output_text)
            items = parsed["items"]
            notes = parsed["notes"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ModelAccessError("OpenAI returned an unusable structured extraction.") from error
        return Extraction(items, notes, self.mode, self.model, self.unverified)


def configured_extractor() -> Any:
    if os.environ.get("ORDERCLERK_PROVIDER") == "ollama":
        from .ollama_provider import OllamaExtractor
        return OllamaExtractor(os.environ.get("ORDERCLERK_MODEL", "qwen2.5:3b"),
                               os.environ.get("ORDERCLERK_OLLAMA_HOST", "http://127.0.0.1:11434"))
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return FixtureExtractor()
    model = os.environ.get("OPENAI_MODEL", "gpt-5.2").strip() or "gpt-5.2"
    base_url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").strip()
    return OpenAIExtractor(api_key, model, base_url)


class OrderService:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH, extractor: Any | None = None) -> None:
        self.db_path = Path(db_path)
        self.extractor = extractor or configured_extractor()

    def provider(self) -> dict[str, Any]:
        return {
            "mode": self.extractor.mode,
            "model": self.extractor.model,
            "unverified": self.extractor.unverified,
            "label": (
                "Offline fixture parser - live AI unverified"
                if self.extractor.unverified
                else f"{self.extractor.mode.title()} model - {self.extractor.model}"
            ),
        }

    def _catalogue(self, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT p.id,p.sku,p.name,p.unit,p.price_minor,a.alias
            FROM products p JOIN product_aliases a ON a.product_id=p.id
            WHERE p.active=1 ORDER BY p.id,length(a.alias) DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _validate_extraction(
        self, extraction: Extraction, catalogue: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        aliases: dict[str, dict[str, Any]] = {}
        for row in catalogue:
            aliases[normalize_alias(row["alias"])] = row
            aliases[normalize_alias(row["name"])] = row
            aliases[normalize_alias(row["sku"])] = row

        combined: dict[int, dict[str, Any]] = {}
        issues: list[dict[str, str]] = []
        for index, raw_item in enumerate(extraction.items):
            product_text = str(raw_item.get("product", "")).strip()
            product = aliases.get(normalize_alias(product_text))
            if product is None:
                issues.append(
                    {
                        "kind": "unsupported_product",
                        "message": f"Line {index + 1}: '{product_text or 'blank'}' is not a supported catalogue alias.",
                    }
                )
                continue
            quantity = raw_item.get("quantity")
            if quantity is None:
                issues.append(
                    {
                        "kind": "missing_quantity",
                        "message": f"How many {product['unit']}s of {product['name']} are required?",
                    }
                )
                continue
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                issues.append(
                    {
                        "kind": "invalid_quantity",
                        "message": f"Quantity for {product['name']} must be a positive whole number.",
                    }
                )
                continue
            if product["id"] not in combined:
                combined[product["id"]] = {**product, "quantity": 0}
            combined[product["id"]]["quantity"] += quantity

        if not combined and not issues:
            issues.append(
                {
                    "kind": "no_supported_product",
                    "message": "No supported catalogue product could be matched. Ask the customer to name a listed item.",
                }
            )
        return list(combined.values()), issues

    def submit(self, external_ref: str, customer_name: str, body: str) -> dict[str, Any]:
        external_ref = external_ref.strip()
        customer_name = customer_name.strip()
        body = body.strip()
        if not external_ref or len(external_ref) > 100:
            raise OrderClerkError("Message reference is required and must be at most 100 characters.")
        if not customer_name or len(customer_name) > 120:
            raise OrderClerkError("Customer name is required and must be at most 120 characters.")
        if not body or len(body) > 5000:
            raise OrderClerkError("Customer message is required and must be at most 5,000 characters.")

        with connect_database(self.db_path) as connection:
            existing = connection.execute(
                "SELECT id FROM incoming_messages WHERE external_ref=?", (external_ref,)
            ).fetchone()
            if existing:
                return self._result(connection, existing["id"], replayed=True)
            catalogue = self._catalogue(connection)

        extraction = self.extractor.extract(body, catalogue)
        validated_items, issues = self._validate_extraction(extraction, catalogue)
        body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

        with connect_database(self.db_path) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT id FROM incoming_messages WHERE external_ref=?", (external_ref,)
                ).fetchone()
                if existing:
                    connection.commit()
                    return self._result(connection, existing["id"], replayed=True)

                customer = connection.execute(
                    "SELECT id FROM customers WHERE display_name=?", (customer_name,)
                ).fetchone()
                if customer:
                    customer_id = customer["id"]
                else:
                    customer_id = connection.execute(
                        "INSERT INTO customers (display_name) VALUES (?)", (customer_name,)
                    ).lastrowid
                message_id = connection.execute(
                    """
                    INSERT INTO incoming_messages
                    (external_ref,customer_id,body,body_sha256,extraction_mode,model_name,extraction_json)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        external_ref,
                        customer_id,
                        body,
                        body_sha256,
                        extraction.mode,
                        extraction.model,
                        json.dumps(extraction.as_dict(), separators=(",", ":")),
                    ),
                ).lastrowid

                if issues:
                    connection.execute(
                        "UPDATE incoming_messages SET status='review',review_reason=? WHERE id=?",
                        (json.dumps(issues, separators=(",", ":")), message_id),
                    )
                    connection.commit()
                    return self._result(connection, message_id, replayed=False)

                shortages: list[dict[str, str]] = []
                for item in validated_items:
                    availability = connection.execute(
                        "SELECT available_quantity FROM product_availability WHERE product_id=?",
                        (item["id"],),
                    ).fetchone()["available_quantity"]
                    if availability < item["quantity"]:
                        shortages.append(
                            {
                                "kind": "insufficient_stock",
                                "message": (
                                    f"{item['name']} needs {item['quantity']} {item['unit']}(s), "
                                    f"but only {availability} are available."
                                ),
                            }
                        )
                if shortages:
                    connection.execute(
                        "UPDATE incoming_messages SET status='review',review_reason=? WHERE id=?",
                        (json.dumps(shortages, separators=(",", ":")), message_id),
                    )
                    connection.commit()
                    return self._result(connection, message_id, replayed=False)

                order_id = connection.execute(
                    "INSERT INTO orders (message_id,status) VALUES (?,'draft')", (message_id,)
                ).lastrowid
                for item in validated_items:
                    order_item_id = connection.execute(
                        """
                        INSERT INTO order_items (order_id,product_id,quantity,unit_price_minor)
                        VALUES (?,?,?,?)
                        """,
                        (order_id, item["id"], item["quantity"], item["price_minor"]),
                    ).lastrowid
                    connection.execute(
                        "INSERT INTO stock_reservations (order_item_id,status) VALUES (?,'active')",
                        (order_item_id,),
                    )
                connection.execute("UPDATE orders SET status='reserved' WHERE id=?", (order_id,))
                connection.execute(
                    "INSERT INTO order_events (order_id,event_type,detail) VALUES (?,?,?)",
                    (order_id, "reserved", f"Reserved {len(validated_items)} catalogue line(s)."),
                )
                connection.execute(
                    "UPDATE incoming_messages SET status='processed' WHERE id=?", (message_id,)
                )
                connection.commit()
                return self._result(connection, message_id, replayed=False)
            except Exception:
                connection.rollback()
                raise

    def _result(
        self, connection: sqlite3.Connection, message_id: int, replayed: bool
    ) -> dict[str, Any]:
        message = connection.execute(
            """
            SELECT m.*,c.display_name FROM incoming_messages m
            JOIN customers c ON c.id=m.customer_id WHERE m.id=?
            """,
            (message_id,),
        ).fetchone()
        review_items = json.loads(message["review_reason"] or "[]")
        extraction = json.loads(message["extraction_json"])
        order = connection.execute(
            """
            SELECT o.id,o.status,o.currency,o.created_at,t.total_minor
            FROM orders o JOIN order_totals t ON t.order_id=o.id WHERE o.message_id=?
            """,
            (message_id,),
        ).fetchone()
        order_payload: dict[str, Any] | None = None
        picking_list: list[dict[str, Any]] = []
        if order:
            lines = connection.execute(
                """
                SELECT p.sku,p.name,p.unit,i.quantity,i.unit_price_minor,
                       i.quantity*i.unit_price_minor AS line_total_minor,r.status AS reservation_status
                FROM order_items i JOIN products p ON p.id=i.product_id
                JOIN stock_reservations r ON r.order_item_id=i.id
                WHERE i.order_id=? ORDER BY p.name
                """,
                (order["id"],),
            ).fetchall()
            order_payload = {**dict(order), "items": [dict(line) for line in lines]}
            picking_list = [
                {
                    "sku": line["sku"],
                    "name": line["name"],
                    "quantity": line["quantity"],
                    "unit": line["unit"],
                }
                for line in lines
            ]
        return {
            "outcome": "reserved" if order else "review",
            "replayed": replayed,
            "message": {
                "id": message["id"],
                "external_ref": message["external_ref"],
                "customer": message["display_name"],
                "body": message["body"],
                "status": message["status"],
                "created_at": message["created_at"],
            },
            "extraction": extraction,
            "review_items": review_items,
            "order": order_payload,
            "picking_list": picking_list,
        }

    def state(self) -> dict[str, Any]:
        with connect_database(self.db_path) as connection:
            catalogue = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT p.id,p.sku,p.name,p.unit,p.price_minor,a.available_quantity
                    FROM products p JOIN product_availability a ON a.product_id=p.id
                    WHERE p.active=1 ORDER BY p.name
                    """
                ).fetchall()
            ]
            orders = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT o.id,o.status,o.created_at,t.currency,t.total_minor,
                           c.display_name AS customer,m.external_ref,COUNT(i.id) AS line_count
                    FROM orders o JOIN order_totals t ON t.order_id=o.id
                    JOIN incoming_messages m ON m.id=o.message_id
                    JOIN customers c ON c.id=m.customer_id
                    LEFT JOIN order_items i ON i.order_id=o.id
                    GROUP BY o.id ORDER BY o.id DESC LIMIT 12
                    """
                ).fetchall()
            ]
            reviews = []
            for row in connection.execute(
                """
                SELECT m.id,m.external_ref,m.created_at,m.review_reason,c.display_name AS customer
                FROM incoming_messages m JOIN customers c ON c.id=m.customer_id
                WHERE m.status='review' ORDER BY m.id DESC LIMIT 8
                """
            ).fetchall():
                review = dict(row)
                review["review_items"] = json.loads(review.pop("review_reason") or "[]")
                reviews.append(review)
            counts = dict(
                connection.execute(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM orders WHERE status='reserved') AS reserved_orders,
                      (SELECT COUNT(*) FROM incoming_messages WHERE status='review') AS review_messages,
                      (SELECT COUNT(*) FROM incoming_messages) AS total_messages
                    """
                ).fetchone()
            )
        return {
            "provider": self.provider(),
            "catalogue": catalogue,
            "orders": orders,
            "reviews": reviews,
            "stats": counts,
        }

    def picking_list_csv(self, order_id: int) -> str:
        with connect_database(self.db_path) as connection:
            order = connection.execute(
                "SELECT id FROM orders WHERE id=?", (order_id,)
            ).fetchone()
            if not order:
                raise OrderClerkError("Order not found.")
            lines = connection.execute(
                """
                SELECT p.sku,p.name,i.quantity,p.unit
                FROM order_items i JOIN products p ON p.id=i.product_id
                WHERE i.order_id=? ORDER BY p.name
                """,
                (order_id,),
            ).fetchall()
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["order_id", "sku", "product", "quantity", "unit"])
        for line in lines:
            writer.writerow([order_id, line["sku"], line["name"], line["quantity"], line["unit"]])
        return output.getvalue()
