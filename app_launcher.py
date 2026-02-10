import logging
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
import configparser
import hashlib
import platform


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


def _ensure_license():
    license_path = Path(os.environ.get("PROGRAMDATA", r"C:\\ProgramData")) / "MahilMartPOS" / "license.ini"
    if not license_path.exists():
        logging.error("License file not found at %s", license_path)
        raise SystemExit("License not found. Please reinstall and activate this copy.")

    parser = configparser.ConfigParser()
    parser.read(license_path)
    if "license" not in parser:
        logging.error("License file missing [license] section.")
        raise SystemExit("License invalid. Please reinstall and activate this copy.")

    section = parser["license"]
    email = section.get("email", "").strip()
    machine_id = section.get("machine_id", "").strip()
    issued_at = section.get("issued_at", "").strip()
    stored_key = section.get("license_key", "").strip().upper()

    if not email or not stored_key or not machine_id:
        logging.error("License file missing required fields.")
        raise SystemExit("License incomplete. Please reinstall and activate this copy.")

    current_machine = platform.node().strip().lower() or os.environ.get("COMPUTERNAME", "").strip().lower()
    if machine_id and current_machine and machine_id.lower() != current_machine:
        logging.error("License machine_id %s does not match current machine %s.", machine_id, current_machine)
        raise SystemExit("License not valid for this machine.")

    seed = f"{email}|{machine_id}|{issued_at}"
    expected_key = hashlib.sha1(seed.encode()).hexdigest().upper()[:24]
    if expected_key != stored_key:
        logging.error("License integrity check failed. Expected %s, found %s.", expected_key, stored_key)
        raise SystemExit("License validation failed.")

    logging.info("License validated for %s on machine %s.", email, machine_id)


def _send_pending_activation_email():
    notice_path = Path(os.environ.get("PROGRAMDATA", r"C:\\ProgramData")) / "MahilMartPOS" / "license_activation_pending.ini"
    if not notice_path.exists():
        return

    parser = configparser.ConfigParser()
    parser.read(notice_path)
    if "activation" not in parser:
        logging.error("Activation notice file missing [activation] section: %s", notice_path)
        return

    section = parser["activation"]
    email = section.get("email", "").strip()
    machine_id = section.get("machine_id", "").strip()
    issued_at = section.get("issued_at", "").strip()
    license_key = section.get("license_key", "").strip().upper()
    if not email or not machine_id or not issued_at or not license_key:
        logging.error("Activation notice file missing required fields: %s", notice_path)
        return

    from django.conf import settings
    from django.core.mail import send_mail

    try:
        from MahilMartPOS_App.utils.email_config import apply_email_settings
        apply_email_settings()
    except Exception:
        logging.exception("Failed to apply dynamic email settings. Falling back to static settings.")

    recipients = ["mahiltechlab.ops@gmail.com"]

    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    if not from_email:
        from_email = (getattr(settings, "EMAIL_HOST_USER", None) or "").strip()
    if not from_email:
        logging.warning("Activation email skipped because sender is not configured.")
        return

    subject = "MahilMart POS License Activated"
    body = (
        "A new MahilMart POS license was activated.\n\n"
        f"Email: {email}\n"
        f"Machine: {machine_id}\n"
        f"Issued At: {issued_at}\n"
        f"License Key: {license_key}\n"
    )

    try:
        send_mail(subject, body, from_email, recipients, fail_silently=False)
        notice_path.unlink(missing_ok=True)
        logging.info("Activation email sent to %s.", ", ".join(recipients))
    except Exception:
        # Keep pending file so startup can retry when email settings are fixed.
        logging.exception("Failed to send activation email. Will retry on next startup.")


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

    _ensure_license()

    if os.environ.get("MAHILMARTPOS_SKIP_MIGRATE") != "1":
        _ensure_database_exists()

    from django import setup as django_setup
    django_setup()

    if os.environ.get("MAHILMARTPOS_SKIP_MIGRATE") != "1":
        _run_migrations()

    _send_pending_activation_email()

    threading.Thread(target=_open_browser, daemon=True).start()
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8000", "--noreload"])


if __name__ == "__main__":
    main()
