#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from orderclerk.core import DEFAULT_DB_PATH, OrderService, initialize_database
from orderclerk.server import build_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OrderClerk AI local application.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5184)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    initialize_database(args.db)
    service = OrderService(args.db)
    server = build_server(args.host, args.port, service)
    print(f"OrderClerk AI running at http://{args.host}:{server.server_port}")
    print(service.provider()["label"])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
