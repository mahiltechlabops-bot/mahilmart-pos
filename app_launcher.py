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
import socket


_STDIO_STREAM = None


def _detect_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe_socket:
            probe_socket.connect(("8.8.8.8", 80))
            local_ip = probe_socket.getsockname()[0].strip()
            if local_ip:
                return local_ip
    except OSError:
        pass

    try:
        local_ip = socket.gethostbyname(socket.gethostname()).strip()
        if local_ip:
            return local_ip
    except OSError:
        pass

    return "127.0.0.1"


def _normalize_port(value):
    candidate = (value or "").strip()
    if not candidate.isdigit():
        return "8002"

    numeric_port = int(candidate)
    if numeric_port < 1 or numeric_port > 65535:
        return "8002"

    return str(numeric_port)


def _get_server_host_port():
    fixed_host = (os.environ.get("MAHILMARTPOS_HOST") or "").strip()
    bind_host = (os.environ.get("MAHILMARTPOS_BIND_HOST") or "").strip()
    browser_host = (os.environ.get("MAHILMARTPOS_BROWSER_HOST") or "").strip()
    port = _normalize_port(os.environ.get("MAHILMARTPOS_PORT") or "8002")

    if fixed_host:
        bind_host = fixed_host
        browser_host = fixed_host
    else:
        if not bind_host:
            bind_host = "0.0.0.0"
        if not browser_host:
            if bind_host in ("0.0.0.0", "::"):
                browser_host = _detect_local_ip()
            else:
                browser_host = bind_host

    logging.info(
        "Launcher network config: bind_host=%s, browser_host=%s, port=%s",
        bind_host,
        browser_host,
        port,
    )
    return bind_host, browser_host, port


def _open_browser(browser_host, port):
    time.sleep(1.5)
    webbrowser.open(f"http://{browser_host}:{port}/")


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
        "connect_timeout": int(os.environ.get("MAHILMARTPOS_DB_CONNECT_TIMEOUT", "5")),
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


def _build_checksum_value(seed, multiplier, offset):
    total = 0
    modulus = 16777215
    for index, char in enumerate(seed, start=1):
        total = (total + (ord(char) + offset) * (index + multiplier)) % modulus
    return total


def _build_checksum_key(seed):
    modulus = 16777215
    part_a = _build_checksum_value(seed, 3, 11)
    part_b = _build_checksum_value(seed, 7, 19)
    part_c = (part_a * 31 + part_b * 17 + len(seed) * 97) % modulus
    part_d = (part_a + part_b + part_c + len(seed) * 13) % modulus
    return f"{part_a:06X}{part_b:06X}{part_c:06X}{part_d:06X}"


def _generate_license_key(email, machine_id):
    uppercase_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lowercase_chars = "abcdefghijkmnopqrstuvwxyz"
    number_chars = "23456789"
    special_chars = "@#$%&*!?"
    modulus = 16777215
    seed = f"{email.strip().upper()}|{machine_id.strip().upper()}"
    state = (
        _build_checksum_value(seed, 3, 11)
        + _build_checksum_value(seed, 7, 19)
        + len(seed) * 97
    ) % modulus

    base_chars = []
    for index in range(30):
        state = (state * 73 + 19 + index * 131) % modulus
        if index % 3 == 0:
            charset = uppercase_chars
        elif index % 3 == 1:
            charset = lowercase_chars
        else:
            charset = number_chars
        base_chars.append(charset[state % len(charset)])

    base_key = "".join(base_chars)
    state = (state * 73 + 17) % modulus
    special_a = special_chars[state % len(special_chars)]
    state = (state * 73 + 29) % modulus
    special_b = special_chars[state % len(special_chars)]
    return f"{base_key[:10]}{special_a}{base_key[10:20]}{special_b}{base_key[20:]}"


def _generate_legacy_short_license_key(email, machine_id):
    seed = f"{email.strip().upper()}|{machine_id.strip().upper()}"
    return _build_checksum_key(seed)[:10]


def _generate_staged_license_key(email, machine_id, issued_at):
    seed = f"{email.strip().upper()}|{machine_id.strip().upper()}|{issued_at.strip()}"
    return _build_checksum_key(seed)[:10]


def _generate_transition_license_key(email, machine_id, issued_at):
    seed = f"{email.strip().upper()}|{machine_id.strip().upper()}|{issued_at.strip()}"
    return _build_checksum_key(seed)


def _generate_legacy_license_key(email, machine_id, issued_at):
    seed = f"{email}|{machine_id}|{issued_at}"
    return hashlib.sha1(seed.encode()).hexdigest().upper()[:24]


def _ensure_license():
    license_path = Path(os.environ.get("PROGRAMDATA", r"C:\\ProgramData")) / "MahilMartPOS" / "license.ini"
    if not license_path.exists():
        logging.error("License file not found at %s", license_path)
        raise SystemExit("License not found. Please reinstall and activate this copy.")

    parser = configparser.ConfigParser(interpolation=None)
    parser.read(license_path)
    if "license" not in parser:
        logging.error("License file missing [license] section.")
        raise SystemExit("License invalid. Please reinstall and activate this copy.")

    section = parser["license"]
    email = section.get("email", "").strip()
    machine_id = section.get("machine_id", "").strip()
    issued_at = section.get("issued_at", "").strip()
    stored_key_raw = section.get("license_key", "").strip()
    stored_key_upper = stored_key_raw.upper()

    if not email or not stored_key_raw or not machine_id:
        logging.error("License file missing required fields.")
        raise SystemExit("License incomplete. Please reinstall and activate this copy.")

    current_machine = platform.node().strip().lower() or os.environ.get("COMPUTERNAME", "").strip().lower()
    if machine_id and current_machine and machine_id.lower() != current_machine:
        logging.error("License machine_id %s does not match current machine %s.", machine_id, current_machine)
        raise SystemExit("License not valid for this machine.")

    expected_key = _generate_license_key(email, machine_id)
    legacy_short_key = _generate_legacy_short_license_key(email, machine_id)
    staged_key = _generate_staged_license_key(email, machine_id, issued_at) if issued_at else ""
    transition_key = _generate_transition_license_key(email, machine_id, issued_at) if issued_at else ""
    legacy_expected_key = _generate_legacy_license_key(email, machine_id, issued_at) if issued_at else ""

    valid_keys_sensitive = {expected_key}
    valid_keys_upper = {legacy_short_key}
    if staged_key:
        valid_keys_upper.add(staged_key)
    if transition_key:
        valid_keys_upper.add(transition_key)
    if legacy_expected_key:
        valid_keys_upper.add(legacy_expected_key)

    if stored_key_raw not in valid_keys_sensitive and stored_key_upper not in valid_keys_upper:
        logging.error(
            "License integrity check failed. Expected one of %s (case-sensitive) or %s (legacy uppercase), found %s.",
            ", ".join(sorted(valid_keys_sensitive)),
            ", ".join(sorted(valid_keys_upper)),
            stored_key_raw,
        )
        raise SystemExit("License validation failed.")

    logging.info("License validated for %s on machine %s.", email, machine_id)


def _send_pending_activation_email():
    notice_path = Path(os.environ.get("PROGRAMDATA", r"C:\\ProgramData")) / "MahilMartPOS" / "license_activation_pending.ini"
    if not notice_path.exists():
        return

    parser = configparser.ConfigParser(interpolation=None)
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

    from django.core.mail import get_connection, send_mail

    license_email = (os.environ.get("MAHILMARTPOS_LICENSE_ALERT_EMAIL") or "mahiltechlab.ops@gmail.com").strip()
    license_app_password = (
        os.environ.get("MAHILMARTPOS_LICENSE_ALERT_APP_PASSWORD") or "fbopbtqzaqvedzkg"
    ).strip()
    if not license_email or not license_app_password:
        logging.warning("Activation email skipped because dedicated license email credentials are missing.")
        return

    recipients = [license_email]
    from_email = license_email
    smtp_timeout_raw = os.environ.get("MAHILMARTPOS_LICENSE_EMAIL_TIMEOUT", "8").strip()
    try:
        smtp_timeout = float(smtp_timeout_raw)
    except ValueError:
        smtp_timeout = 8.0

    subject = "MahilMart POS License Activated"
    body = (
        "A new MahilMart POS license was activated.\n\n"
        f"Email: {email}\n"
        f"Machine: {machine_id}\n"
        f"Issued At: {issued_at}\n"
        f"License Key: {license_key}\n"
    )

    try:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host="smtp.gmail.com",
            port=587,
            username=license_email,
            password=license_app_password,
            use_tls=True,
            timeout=smtp_timeout,
            fail_silently=False,
        )
        send_mail(subject, body, from_email, recipients, fail_silently=False, connection=connection)
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


def _has_pending_migrations():
    from django.db import connections, DEFAULT_DB_ALIAS
    from django.db.migrations.executor import MigrationExecutor

    connection = connections[DEFAULT_DB_ALIAS]
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    return bool(plan)


def main():
    _setup_logging()
    _ensure_stdio()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MahilMartPOS.settings")
    if not sys.argv or not sys.argv[0]:
        sys.argv = ["MahilMartPOS"]

    _ensure_license()

    should_migrate = os.environ.get("MAHILMARTPOS_SKIP_MIGRATE") != "1"
    if should_migrate:
        _ensure_database_exists()

    from django import setup as django_setup
    django_setup()

    if should_migrate:
        try:
            if _has_pending_migrations():
                _run_migrations()
            else:
                logging.info("No pending migrations. Skipping migrate step.")
        except Exception:
            logging.exception("Pending migration check failed; running migrate for safety.")
            _run_migrations()

    bind_host, browser_host, port = _get_server_host_port()
    threading.Thread(target=_open_browser, args=(browser_host, port), daemon=True).start()
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", f"{bind_host}:{port}", "--noreload"])


if __name__ == "__main__":
    main()
