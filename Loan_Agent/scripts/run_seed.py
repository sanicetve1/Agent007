"""Run seed_test_cases.sql using loan_agent DB connection.

From Loan_Agent dir with deps installed:
  pip install psycopg python-dotenv  # if needed
  set PYTHONPATH=.  (Windows) or export PYTHONPATH=.  (Unix)
  python scripts/run_seed.py

Or with psql: PGPASSWORD=admin psql -h localhost -p 5432 -U admin -d loan_db -f DB/seed_test_cases.sql
"""
from pathlib import Path

from loan_agent.db import get_conn

def main():
    sql_path = Path(__file__).resolve().parent.parent / "DB" / "seed_test_cases.sql"
    sql = sql_path.read_text()
    statements = [
        s.strip() for s in sql.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                if not stmt:
                    continue
                cur.execute(stmt)
        conn.commit()
    print("Seed completed: 3 test cases (Alice Minimal, Bob Collateral, Carol Decline) inserted.")

if __name__ == "__main__":
    main()
