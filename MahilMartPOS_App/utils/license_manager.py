import os
import re
from datetime import datetime, timezone


DEFAULT_LICENSE_EMAIL = "mahiltechlab.ops@gmail.com"
DEFAULT_MONGO_URI = (
    "mongodb+srv://praveenv_db_user:ytf8RxoQPEn3tUSD@cluster0.ezhfgp1.mongodb.net/?appName=Cluster0"
)
DEFAULT_MONGO_DB = "mahilmart_pos"
DEFAULT_MONGO_COLLECTION = "license_keys"


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
    mongo_uri = (os.environ.get("MAHILMARTPOS_LICENSE_MONGO_URI") or DEFAULT_MONGO_URI).strip()
    if not mongo_uri:
        return None, "Mongo URI is not configured."
    try:
        from pymongo import MongoClient

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client, None
    except Exception as exc:
        return None, str(exc)


def store_generated_license(machine_id, license_key, generated_by, customer_name="", contact_email="", note=""):
    client, error_message = _open_mongo_client()
    if client is None:
        return False, f"MongoDB save failed: {error_message}"

    db_name = (os.environ.get("MAHILMARTPOS_LICENSE_MONGO_DB") or DEFAULT_MONGO_DB).strip()
    collection_name = (
        os.environ.get("MAHILMARTPOS_LICENSE_MONGO_COLLECTION") or DEFAULT_MONGO_COLLECTION
    ).strip()
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
        "source": "license_manager_page",
    }

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
        return False, f"MongoDB save failed: {exc}"
    finally:
        client.close()


def fetch_recent_generated_licenses(limit=20):
    client, error_message = _open_mongo_client()
    if client is None:
        return [], f"MongoDB unavailable: {error_message}"

    db_name = (os.environ.get("MAHILMARTPOS_LICENSE_MONGO_DB") or DEFAULT_MONGO_DB).strip()
    collection_name = (
        os.environ.get("MAHILMARTPOS_LICENSE_MONGO_COLLECTION") or DEFAULT_MONGO_COLLECTION
    ).strip()

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
        return [], f"MongoDB load failed: {exc}"
    finally:
        client.close()
