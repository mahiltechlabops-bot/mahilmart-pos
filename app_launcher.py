import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


_STDIO_STREAM = None


def _open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/")


def _setup_logging():
    log_dir = Path.home() / "MahilMartPOS" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "startup.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def _ensure_stdio():
    global _STDIO_STREAM
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_dir = Path.home() / "MahilMartPOS" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "startup.log"
    _STDIO_STREAM = open(log_file, "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _STDIO_STREAM
    if sys.stderr is None:
        sys.stderr = _STDIO_STREAM


def _ensure_database_exists():
    from django.conf import settings
    db = settings.DATABASES.get("default", {})
    if db.get("ENGINE") != "django.db.backends.postgresql":
        return
    db_name = db.get("NAME")
    if not db_name:
        return
    import psycopg2
    user = db.get("USER")
    host = db.get("HOST") or "localhost"
    port = db.get("PORT") or "5432"
    connect_kwargs = {
        "dbname": db_name,
        "user": user,
        "password": db.get("PASSWORD"),
        "host": host,
        "port": port,
    }
    try:
        conn = psycopg2.connect(**connect_kwargs)
        conn.close()
        logging.info("Database %s already exists.", db_name)
        return
    except psycopg2.OperationalError as exc:
        msg = str(exc).lower()
        if "does not exist" not in msg:
            if "could not connect to server" in msg or "connection refused" in msg:
                logging.error(
                    "Cannot connect to PostgreSQL at %s:%s. Is the service running?",
                    host,
                    port,
                )
            elif "password authentication failed" in msg or "authentication failed" in msg:
                logging.error("PostgreSQL authentication failed for user '%s'.", user)
            else:
                logging.exception("Database connection failed.")
            raise
    admin_db = os.environ.get("MAHILMARTPOS_ADMIN_DB", "postgres")
    logging.info("Database %s not found. Creating using %s.", db_name, admin_db)
    admin_kwargs = dict(connect_kwargs)
    admin_kwargs["dbname"] = admin_db
    admin_conn = psycopg2.connect(**admin_kwargs)
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        admin_conn.close()


def _run_migrations():
    from django.core.management import call_command
    call_command(
        "migrate",
        interactive=False,
        run_syncdb=True,
        verbosity=1,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def main():
    _setup_logging()
    _ensure_stdio()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MahilMartPOS.settings")
    if not sys.argv or not sys.argv[0]:
        sys.argv = ["MahilMartPOS"]

    if os.environ.get("MAHILMARTPOS_SKIP_MIGRATE") != "1":
        _ensure_database_exists()

    from django import setup as django_setup
    django_setup()

    if os.environ.get("MAHILMARTPOS_SKIP_MIGRATE") != "1":
        _run_migrations()

    threading.Thread(target=_open_browser, daemon=True).start()
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8000", "--noreload"])


if __name__ == "__main__":
    main()
