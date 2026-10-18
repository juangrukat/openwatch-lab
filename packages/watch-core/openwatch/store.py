"""Local SQLite observations. Explicit export; no network or vendor account."""

import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    """A per-user, deduplicating observation store."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY, device TEXT NOT NULL, kind TEXT NOT NULL,
                record_key TEXT NOT NULL, data TEXT NOT NULL,
                received_at TEXT NOT NULL
                    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                UNIQUE(device, kind, record_key));
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, adapter TEXT NOT NULL);
        """)
        self.db.commit()

    def remember(self, device: str, name: str, adapter: str) -> None:
        """Store the user's explicitly selected device for reconnect."""
        self.db.execute(
            "INSERT OR REPLACE INTO devices VALUES (?,?,?)", (device, name, adapter)
        )
        self.db.commit()

    def devices(self) -> list[dict[str, str]]:
        """Return locally known devices, without automatically connecting to them."""
        return [
            dict(zip(("id", "name", "adapter"), row, strict=True))
            for row in self.db.execute("SELECT id,name,adapter FROM devices")
        ]

    def put(self, device: str, kind: str, key: str, data: dict[str, Any]) -> None:
        """Update one observation without duplicating a repeated history sync."""
        self.db.execute(
            """INSERT INTO observations(device,kind,record_key,data)
            VALUES (?,?,?,?) ON CONFLICT(device,kind,record_key)
            DO UPDATE SET data=excluded.data""",
            (device, kind, key, json.dumps(data, allow_nan=False)),
        )
        self.db.commit()

    def history(
        self, device: str | None = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Return recent real observations, optionally scoped to one device."""
        query = "SELECT id,device,kind,data,received_at FROM observations"
        params: tuple[Any, ...] = ()
        if device:
            query += " WHERE device=?"
            params = (device,)
        query += " ORDER BY id DESC LIMIT ?"
        rows = self.db.execute(query, (*params, min(max(limit, 1), 5000))).fetchall()
        return [
            {
                "id": row[0],
                "device": row[1],
                "kind": row[2],
                "data": json.loads(row[3]),
                "received_at": row[4],
            }
            for row in rows
        ]

    def close(self) -> None:
        """Flush and close the local database."""
        self.db.close()
