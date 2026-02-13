import logging
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
import configparser
import hashlib
import ipaddress
import platform
import socket


_STDIO_STREAM = None
_AUTO_HOST_KEYWORDS = {"auto", "dhcp", "current", "system"}
_DEFAULT_SERVER_PORT = "0608"
_DEFAULT_LICENSE_WINDOW_MINUTES = 10


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


def _normalize_host_value(value):
    host_value = (value or "").strip()
    if not host_value:
        return ""
    if "://" in host_value:
        host_value = host_value.split("://", 1)[1]
    host_value = host_value.split("/", 1)[0].strip()
    if host_value.startswith("["):
        end_index = host_value.find("]")
        if end_index > 0:
            return host_value[1:end_index].strip()
    if host_value.count(":") == 1:
        left, right = host_value.split(":", 1)
        if right.isdigit():
            host_value = left
    return host_value.strip()


def _split_hosts(value):
    tokens = []
    seen = set()
    raw_value = str(value or "").replace(";", ",")
    for item in raw_value.split(","):
        host = _normalize_host_value(item)
        if host and host not in seen:
            seen.add(host)
            tokens.append(host)
    return tokens


def _resolve_auto_host_tokens(value):
    raw_tokens = _split_hosts(value)
    if not raw_tokens:
        return ""

    resolved = []
    detected_local_ip = _detect_local_ip()
    for token in raw_tokens:
        normalized = token.strip().lower()
        if normalized in _AUTO_HOST_KEYWORDS:
            if detected_local_ip and detected_local_ip not in resolved:
                resolved.append(detected_local_ip)
            continue
        if token not in resolved:
            resolved.append(token)

    return ",".join(resolved)


def _resolve_local_ipv4_addresses():
    addresses = {"127.0.0.1", _detect_local_ip()}
    try:
        _, _, host_ips = socket.gethostbyname_ex(socket.gethostname())
        for ip in host_ips:
            ip = (ip or "").strip()
            if ip:
                addresses.add(ip)
    except OSError:
        pass

    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = (item[4][0] or "").strip()
            if ip:
                addresses.add(ip)
    except OSError:
        pass

    return {value for value in addresses if value}


def _is_host_local(host, local_ipv4_set):
    normalized = _normalize_host_value(host).lower()
    if not normalized:
        return False
    if normalized in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "::"}:
        return True

    try:
        parsed = ipaddress.ip_address(normalized)
        if parsed.version == 4:
            return normalized in local_ipv4_set
        return parsed.is_loopback
    except ValueError:
        pass

    try:
        resolved = {
            (item[4][0] or "").strip()
            for item in socket.getaddrinfo(normalized, None, socket.AF_INET)
        }
        return any(ip and ip in local_ipv4_set for ip in resolved)
    except OSError:
        return False


def _normalize_port(value):
    candidate = (value or "").strip()
    if not candidate.isdigit():
        return _DEFAULT_SERVER_PORT

    numeric_port = int(candidate)
    if numeric_port < 1 or numeric_port > 65535:
        return _DEFAULT_SERVER_PORT

    return str(numeric_port)


def _candidate_server_config_paths():
    env_path = (os.environ.get("MAHILMARTPOS_SERVER_CONFIG") or "").strip()
    if env_path:
        yield Path(env_path)

    project_root = Path(__file__).resolve().parent
    yield project_root / "server_config.ini"
    yield project_root / "server_config.local.ini"

    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        yield Path(programdata) / "MahilMartPOS" / "server_config.ini"

    yield Path.home() / "MahilMartPOS" / "server_config.ini"


def _load_server_config():
    for path in _candidate_server_config_paths():
        if not path or not path.is_file():
            continue

        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(path)
        except (OSError, configparser.Error):
            continue

        if not parser.has_section("server"):
            continue

        section = parser["server"]
        data = {
            "host": section.get("host", "").strip(),
            "bind_host": section.get("bind_host", "").strip(),
            "browser_host": section.get("browser_host", "").strip(),
            "port": section.get("port", "").strip(),
        }
        if any(data.values()):
            data["__path__"] = str(path)
            return data
    return {}


def _apply_server_config_overrides():
    config_data = _load_server_config()
    if not config_data:
        return

    env_mapping = {
        "host": "MAHILMARTPOS_HOST",
        "bind_host": "MAHILMARTPOS_BIND_HOST",
        "browser_host": "MAHILMARTPOS_BROWSER_HOST",
        "port": "MAHILMARTPOS_PORT",
    }
    applied_items = []
    for key, env_key in env_mapping.items():
        value = (config_data.get(key) or "").strip()
        if key in {"host", "bind_host", "browser_host"}:
            value = _resolve_auto_host_tokens(value)
        existing = (os.environ.get(env_key) or "").strip()
        if value and not existing:
            os.environ[env_key] = value
            applied_items.append(f"{env_key}={value}")

    if applied_items:
        logging.info(
            "Applied server config from %s: %s",
            config_data.get("__path__", ""),
            ", ".join(applied_items),
        )


def _get_server_host_port():
    fixed_hosts = _split_hosts(_resolve_auto_host_tokens(os.environ.get("MAHILMARTPOS_HOST")))
    bind_hosts = _split_hosts(_resolve_auto_host_tokens(os.environ.get("MAHILMARTPOS_BIND_HOST")))
    browser_hosts = _split_hosts(_resolve_auto_host_tokens(os.environ.get("MAHILMARTPOS_BROWSER_HOST")))

    fixed_host = fixed_hosts[0] if fixed_hosts else ""
    bind_host = bind_hosts[0] if bind_hosts else ""
    browser_host = browser_hosts[0] if browser_hosts else ""
    port = _normalize_port(os.environ.get("MAHILMARTPOS_PORT") or _DEFAULT_SERVER_PORT)
    local_ipv4_set = _resolve_local_ipv4_addresses()

    if fixed_host:
        if not browser_host:
            browser_host = fixed_host
        if not bind_host:
            bind_host = fixed_host
        if bind_host != "0.0.0.0" and not _is_host_local(bind_host, local_ipv4_set):
            logging.warning(
                "Configured bind host '%s' is not local. Falling back to 0.0.0.0 while keeping browser host '%s'.",
                bind_host,
                browser_host,
            )
            bind_host = "0.0.0.0"
    else:
        if not bind_host:
            bind_host = "0.0.0.0"
        if not browser_host:
            if bind_host in ("0.0.0.0", "::"):
                browser_host = _detect_local_ip()
            else:
                browser_host = bind_host

    if fixed_hosts:
        existing = _split_hosts(os.environ.get("MAHILMARTPOS_ALLOWED_HOSTS"))
        merged = existing + [host for host in fixed_hosts if host not in existing]
        os.environ["MAHILMARTPOS_ALLOWED_HOSTS"] = ",".join(merged)

    logging.info(
        "Launcher network config: bind_host=%s, browser_host=%s, port=%s",
        bind_host,
        browser_host,
        port,
    )
    return bind_host, browser_host, port


def _set_runtime_allowed_hosts(bind_host, browser_host):
    def _clean_host(value):
        return _normalize_host_value(value).lower()

    host_candidates = {
        "127.0.0.1",
        "localhost",
        bind_host,
        browser_host,
        _detect_local_ip(),
    }
    host_candidates.update(_split_hosts(os.environ.get("MAHILMARTPOS_HOST")))
    host_candidates.update(_split_hosts(os.environ.get("MAHILMARTPOS_BIND_HOST")))
    host_candidates.update(_split_hosts(os.environ.get("MAHILMARTPOS_BROWSER_HOST")))
    existing_hosts = (os.environ.get("MAHILMARTPOS_ALLOWED_HOSTS") or "").strip()
    if existing_hosts:
        host_candidates.update(existing_hosts.split(","))

    normalized_hosts = sorted(
        host
        for host in {_clean_host(item) for item in host_candidates}
        if host and host not in ("0.0.0.0", "::")
    )

    if normalized_hosts:
        os.environ["MAHILMARTPOS_ALLOWED_HOSTS"] = ",".join(normalized_hosts)
    os.environ["MAHILMARTPOS_ALLOW_ALL_HOSTS"] = "1"
    logging.info("Launcher allowed hosts: %s", os.environ.get("MAHILMARTPOS_ALLOWED_HOSTS", ""))


def _open_browser(browser_host, port):
    time.sleep(1.5)
    browser_candidates = _split_hosts(browser_host)
    target_host = browser_candidates[0] if browser_candidates else (_normalize_host_value(browser_host) or "127.0.0.1")
    webbrowser.open(f"http://{target_host}:{port}/")


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


def _generate_modern_license_key(seed):
    uppercase_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lowercase_chars = "abcdefghijkmnopqrstuvwxyz"
    number_chars = "23456789"
    special_chars = "@#$%&*!?"
    modulus = 16777215
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


def _generate_license_key(email, machine_id):
    seed = f"{email.strip().upper()}|{machine_id.strip().upper()}"
    return _generate_modern_license_key(seed)


def _get_license_window_minutes():
    raw_value = os.environ.get("MAHILMARTPOS_LICENSE_KEY_VALIDITY_MINUTES", str(_DEFAULT_LICENSE_WINDOW_MINUTES)).strip()
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = _DEFAULT_LICENSE_WINDOW_MINUTES
    return max(1, value)


def _normalize_generation_time(generated_at=None):
    value = generated_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _license_key_window_start(generated_at=None):
    window_minutes = _get_license_window_minutes()
    window_seconds = window_minutes * 60
    generated_at_utc = _normalize_generation_time(generated_at)
    bucket_index = int(generated_at_utc.timestamp()) // window_seconds
    return datetime.fromtimestamp(bucket_index * window_seconds, tz=timezone.utc)


def _generate_windowed_license_key(email, machine_id, generated_at=None):
    window_start = _license_key_window_start(generated_at)
    seed = f"{email.strip().upper()}|{machine_id.strip().upper()}|{window_start.strftime('%Y%m%d%H%M')}"
    return _generate_modern_license_key(seed)


def _parse_license_issued_at(issued_at):
    value = (issued_at or "").strip()
    if not value:
        return None

    parse_targets = [value]
    if value.endswith("Z"):
        parse_targets.append(f"{value[:-1]}+00:00")

    for candidate in parse_targets:
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


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
    windowed_keys = set()
    issued_at_dt = _parse_license_issued_at(issued_at)
    if issued_at_dt is not None:
        windowed_keys.add(_generate_windowed_license_key(email, machine_id, issued_at_dt))

    legacy_short_key = _generate_legacy_short_license_key(email, machine_id)
    staged_key = _generate_staged_license_key(email, machine_id, issued_at) if issued_at else ""
    transition_key = _generate_transition_license_key(email, machine_id, issued_at) if issued_at else ""
    legacy_expected_key = _generate_legacy_license_key(email, machine_id, issued_at) if issued_at else ""

    valid_keys_sensitive = {expected_key}
    valid_keys_sensitive.update(windowed_keys)
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
    if not email or not machine_id or not issued_at:
        logging.error("Activation notice file missing required fields: %s", notice_path)
        return

    from django.core.mail import get_connection, send_mail

    default_alert_email = "mahiltechlab.ops@gmail.com"
    configured_alert_email = (os.environ.get("MAHILMARTPOS_LICENSE_ALERT_EMAIL") or "").strip()
    license_app_password = (
        os.environ.get("MAHILMARTPOS_LICENSE_ALERT_APP_PASSWORD") or "kylfneblqxccaimx"
    ).strip()
    if not default_alert_email or not license_app_password:
        logging.warning("Activation email skipped because dedicated license email credentials are missing.")
        return

    recipients = [default_alert_email]
    if configured_alert_email and configured_alert_email.lower() != default_alert_email.lower():
        recipients.append(configured_alert_email)

    from_email = default_alert_email
    smtp_timeout_raw = os.environ.get("MAHILMARTPOS_LICENSE_EMAIL_TIMEOUT", "8").strip()
    try:
        smtp_timeout = float(smtp_timeout_raw)
    except ValueError:
        smtp_timeout = 8.0

    subject = "MahilMart POS Machine ID (Setup)"
    body = (
        "A new MahilMart POS setup has been completed.\n\n"
        f"License Email: {email}\n"
        f"Machine ID: {machine_id}\n"
        f"Setup Time: {issued_at}\n\n"
        "License code is intentionally not included."
    )

    try:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host="smtp.gmail.com",
            port=587,
            username=default_alert_email,
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

    _apply_server_config_overrides()
    _ensure_license()

    bind_host, browser_host, port = _get_server_host_port()
    _set_runtime_allowed_hosts(bind_host, browser_host)

    should_migrate = os.environ.get("MAHILMARTPOS_SKIP_MIGRATE") != "1"
    if should_migrate:
        _ensure_database_exists()

    from django import setup as django_setup
    django_setup()
    _send_pending_activation_email()

    if should_migrate:
        try:
            if _has_pending_migrations():
                _run_migrations()
            else:
                logging.info("No pending migrations. Skipping migrate step.")
        except Exception:
            logging.exception("Pending migration check failed; running migrate for safety.")
            _run_migrations()

    threading.Thread(target=_open_browser, args=(browser_host, port), daemon=True).start()
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", f"{bind_host}:{port}", "--noreload"])


if __name__ == "__main__":
    main()
