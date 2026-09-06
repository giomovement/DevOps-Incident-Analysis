"""Initialize and verify the configured PostgreSQL database without printing secrets."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.database import db, init_db, using_postgres  # noqa: E402


def main() -> int:
    if not using_postgres():
        print(json.dumps({"connected": False, "error": "DIAS_DATABASE_URL is not configured"}))
        return 1

    try:
        init_db()
        with db() as connection:
            info = connection.execute(
                "SELECT current_database() AS database_name, "
                "(SELECT count(*) FROM information_schema.tables WHERE table_schema='public') AS table_count"
            ).fetchone()
            required = connection.execute(
                "SELECT count(*) AS table_count FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN "
                "('users','sessions','incidents','files','runs','workflow_events','log_events',"
                "'evidence','findings','recommendations','cookbooks','audit_events')"
            ).fetchone()["table_count"]
            records = connection.execute(
                "SELECT (SELECT count(*) FROM users) AS users, "
                "(SELECT count(*) FROM incidents) AS incidents, "
                "(SELECT count(*) FROM sessions) AS sessions"
            ).fetchone()
    except Exception as exc:
        print(json.dumps({"connected": False, "error": type(exc).__name__}))
        return 1

    print(
        json.dumps(
            {
                "connected": True,
                "database": info["database_name"],
                "public_tables": info["table_count"],
                "required_tables_present": required == 12,
                "records": dict(records),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
