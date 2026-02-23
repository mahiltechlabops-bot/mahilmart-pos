import configparser
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import URLError


DEFAULT_LICENSE_EMAIL = "mahiltechlab.ops@gmail.com"
DEFAULT_MONGO_URI = (
    "mongodb+srv://praveenv_db_user:ytf8RxoQPEn3tUSD@cluster0.ezhfgp1.mongodb.net/?appName=Cluster0"
)
DEFAULT_MONGO_DB = "mahilmart_pos"
DEFAULT_MONGO_COLLECTION = "license_keys"
LOCAL_CACHE_DIR = Path.home() / "MahilMartPOS"
LOCAL_CACHE_FILE = LOCAL_CACHE_DIR / "license_keys_cache.json"
_PUBLIC_IP_CACHE = None


def _shared_mongo_config_path():
    custom_path = (os.environ.get("MAHILMARTPOS_SHARED_MONGO_CONFIG_PATH") or "").strip()
    if custom_path:
        return Path(custom_path)
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "MahilMartPOS" / "license_mongo_config.ini"


def _read_shared_mongo_config():
    config_path = _shared_mongo_config_path()
    if not config_path.exists():
        return {}

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(config_path, encoding="utf-8")
    except Exception:
        return {}

    if "mongo" not in parser:
        return {}

    section = parser["mongo"]
    return {
        "mongo_uri": (section.get("mongo_uri") or "").strip(),
        "mongo_db": (section.get("mongo_db") or "").strip(),
        "mongo_collection": (section.get("mongo_collection") or "").strip(),
    }


def _get_mongo_runtime_config():
    shared_config = _read_shared_mongo_config()
    mongo_uri = (
        os.environ.get("MAHILMARTPOS_LICENSE_MONGO_URI")
        or shared_config.get("mongo_uri")
        or DEFAULT_MONGO_URI
    ).strip()
    mongo_db = (
        os.environ.get("MAHILMARTPOS_LICENSE_MONGO_DB")
        or shared_config.get("mongo_db")
        or DEFAULT_MONGO_DB
    ).strip()
    mongo_collection = (
        os.environ.get("MAHILMARTPOS_LICENSE_MONGO_COLLECTION")
        or shared_config.get("mongo_collection")
        or DEFAULT_MONGO_COLLECTION
    ).strip()
    return {
        "mongo_uri": mongo_uri,
        "mongo_db": mongo_db,
        "mongo_collection": mongo_collection,
    }


def _build_checksum_value(seed, multiplier, offset):
    total = 0
    modulus = 16777215
    for index, char in enumerate(seed, start=1):
        total = (total + (ord(char) + offset) * (index + multiplier)) % modulus
    return total


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


def normalize_machine_id(machine_id):
    value = (machine_id or "").strip().upper()
    value = re.sub(r"\s+", "", value)
    return value


def is_machine_id_valid(machine_id):
    value = normalize_machine_id(machine_id)
    if not value:
        return False
    return re.fullmatch(r"[A-Z0-9._-]{3,64}", value) is not None


def is_browser_style_machine_id(machine_id):
    value = normalize_machine_id(machine_id)
    return (
        re.fullmatch(
            r"POS-[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}",
            value,
        )
        is not None
    )


def get_license_email():
    email = (os.environ.get("MAHILMARTPOS_LICENSE_EMAIL") or DEFAULT_LICENSE_EMAIL).strip().lower()
    return email or DEFAULT_LICENSE_EMAIL


def generate_machine_license_key(machine_id):
    machine = normalize_machine_id(machine_id)
    seed = f"{get_license_email().upper()}|{machine}"
    return _generate_modern_license_key(seed)


def _open_mongo_client():
    mongo_uri = _get_mongo_runtime_config()["mongo_uri"]
    if not mongo_uri:
        return None, "Mongo URI is not configured."
    try:
        from pymongo import MongoClient

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client, None
    except Exception as exc:
        return None, _sanitize_mongo_error_message(str(exc))


def _sanitize_mongo_error_message(error_text):
    lowered = (error_text or "").lower()
    if "ssl handshake failed" in lowered or "tlsv1_alert_internal_error" in lowered:
        return (
            "MongoDB TLS connection failed. Check internet/firewall, Atlas IP Access List, and "
            "whether your network blocks Atlas TLS."
        )
    if "authentication failed" in lowered:
        return "MongoDB authentication failed. Check Mongo URI in License Manager settings."
    if "timed out" in lowered or "timeout" in lowered:
        return "MongoDB connection timed out. Check internet and Atlas cluster status."
    if "dns" in lowered:
        return "MongoDB DNS lookup failed. Check network DNS and SRV record access."
    compact = (error_text or "").strip().replace("\r", " ").replace("\n", " ")
    if len(compact) > 220:
        compact = compact[:220].rstrip() + "..."
    return compact or "Unknown MongoDB connection error."


def _fetch_public_ip_hint():
    global _PUBLIC_IP_CACHE
    if _PUBLIC_IP_CACHE is not None:
        return _PUBLIC_IP_CACHE

    env_hint = (os.environ.get("MAHILMARTPOS_PUBLIC_IP_HINT") or "").strip()
    if env_hint:
        _PUBLIC_IP_CACHE = env_hint
        return _PUBLIC_IP_CACHE

    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            with urllib_request.urlopen(url, timeout=3) as response:
                value = response.read().decode("utf-8", errors="ignore").strip()
                if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value):
                    _PUBLIC_IP_CACHE = value
                    return _PUBLIC_IP_CACHE
        except (URLError, OSError, TimeoutError):
            continue

    _PUBLIC_IP_CACHE = ""
    return _PUBLIC_IP_CACHE


def _offline_warning(showing_cache=False, reason=""):
    reason_text = (reason or "").strip()
    public_ip = _fetch_public_ip_hint()

    if reason_text:
        message = f"Cloud sync offline. {reason_text}"
    elif showing_cache:
        message = "Cloud sync offline. Using local cache."
    else:
        message = "Cloud sync offline. No local cache yet."

    if public_ip:
        message = f"{message} Atlas Network Access: whitelist public IP {public_ip}."

    return message


def _offline_save_message(reason):
    reason_text = (reason or "").strip()
    if not reason_text:
        return "Saved locally (cloud sync offline)."
    return f"Saved locally (cloud sync offline: {reason_text})."


def _offline_save_failed_message(cache_message, reason):
    reason_text = (reason or "").strip()
    if reason_text:
        return f"Cloud sync offline ({reason_text}). {cache_message}"
    return f"Cloud sync offline. {cache_message}"


def _to_jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _read_local_cache():
    if not LOCAL_CACHE_FILE.exists():
        return []
    try:
        with LOCAL_CACHE_FILE.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _write_local_cache(items):
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCAL_CACHE_FILE.open("w", encoding="utf-8") as file_obj:
        json.dump(items, file_obj, ensure_ascii=True, indent=2)


def _parse_cached_datetime(value):
    if isinstance(value, datetime):
        return value
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _save_local_generated_license(document):
    items = _read_local_cache()
    key = (document.get("license_key") or "").strip()
    if not key:
        return False, "Local cache save failed: missing license key."

    normalized_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if (item.get("license_key") or "").strip() == key:
            continue
        normalized_items.append(item)

    cache_record = {
        "license_key": key,
        "machine_id": (document.get("machine_id") or "").strip(),
        "customer_name": (document.get("customer_name") or "").strip(),
        "contact_email": (document.get("contact_email") or "").strip(),
        "generated_by": (document.get("generated_by") or "").strip(),
        "generated_at": _to_jsonable(document.get("generated_at")),
        "status": (document.get("status") or "generated").strip(),
        "source": (document.get("source") or "license_manager_page").strip(),
    }
    normalized_items.insert(0, cache_record)
    try:
        _write_local_cache(normalized_items[:200])
        return True, "License saved to local cache."
    except OSError as exc:
        return False, f"Local cache save failed: {exc}"


def _fetch_recent_local_licenses(limit):
    items = _read_local_cache()
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result_item = {
            "license_key": (item.get("license_key") or "").strip(),
            "machine_id": (item.get("machine_id") or "").strip(),
            "customer_name": (item.get("customer_name") or "").strip(),
            "contact_email": (item.get("contact_email") or "").strip(),
            "generated_by": (item.get("generated_by") or "").strip(),
            "generated_at": _parse_cached_datetime(item.get("generated_at")),
            "status": (item.get("status") or "generated").strip(),
        }
        results.append(result_item)
        if len(results) >= max(1, int(limit)):
            break
    return results


def store_generated_license(
    machine_id,
    license_key,
    generated_by,
    customer_name="",
    contact_email="",
    note="",
    source="license_manager_page",
):
    client, error_message = _open_mongo_client()
    now_utc = datetime.now(timezone.utc)

    document = {
        "license_key": (license_key or "").strip(),
        "machine_id": normalize_machine_id(machine_id),
        "license_email": get_license_email(),
        "customer_name": (customer_name or "").strip(),
        "contact_email": (contact_email or "").strip().lower(),
        "note": (note or "").strip(),
        "generated_by": (generated_by or "").strip(),
        "generated_at": now_utc,
        "status": "generated",
        "source": (source or "license_manager_page").strip(),
    }

    if client is None:
        is_cached, cache_message = _save_local_generated_license(document)
        if is_cached:
            return True, _offline_save_message(error_message)
        return False, _offline_save_failed_message(cache_message, error_message)

    mongo_runtime = _get_mongo_runtime_config()
    db_name = mongo_runtime["mongo_db"]
    collection_name = mongo_runtime["mongo_collection"]

    try:
        collection = client[db_name][collection_name]
        collection.update_one(
            {"license_key": document["license_key"]},
            {
                "$set": document,
                "$setOnInsert": {
                    "created_at": now_utc,
                },
            },
            upsert=True,
        )
        return True, "License saved to MongoDB."
    except Exception as exc:
        fallback_reason = _sanitize_mongo_error_message(str(exc))
        is_cached, cache_message = _save_local_generated_license(document)
        if is_cached:
            return True, _offline_save_message(fallback_reason)
        return False, _offline_save_failed_message(cache_message, fallback_reason)
    finally:
        client.close()


def fetch_recent_generated_licenses(limit=20):
    client, error_message = _open_mongo_client()
    if client is None:
        local_records = _fetch_recent_local_licenses(limit)
        if local_records:
            return local_records, _offline_warning(showing_cache=True, reason=error_message)
        return [], _offline_warning(showing_cache=False, reason=error_message)

    mongo_runtime = _get_mongo_runtime_config()
    db_name = mongo_runtime["mongo_db"]
    collection_name = mongo_runtime["mongo_collection"]

    try:
        collection = client[db_name][collection_name]
        cursor = (
            collection.find(
                {},
                {
                    "_id": 0,
                    "license_key": 1,
                    "machine_id": 1,
                    "customer_name": 1,
                    "contact_email": 1,
                    "generated_by": 1,
                    "generated_at": 1,
                    "status": 1,
                },
            )
            .sort("generated_at", -1)
            .limit(max(1, int(limit)))
        )
        return list(cursor), ""
    except Exception as exc:
        fallback_reason = _sanitize_mongo_error_message(str(exc))
        local_records = _fetch_recent_local_licenses(limit)
        if local_records:
            return local_records, _offline_warning(showing_cache=True, reason=fallback_reason)
        return [], _offline_warning(showing_cache=False, reason=fallback_reason)
    finally:
        client.close()
