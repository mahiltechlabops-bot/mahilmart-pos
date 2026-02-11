import configparser
import os
from pathlib import Path


_DEFAULTS = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "mmpos2",
    "USER": "postgres",
    "PASSWORD": "",
    "HOST": "localhost",
    "PORT": "5432",
}


def _candidate_paths():
    env_path = os.environ.get("MAHILMARTPOS_DB_CONFIG")
    if env_path:
        yield Path(env_path)

    project_root = Path(__file__).resolve().parent.parent
    yield project_root / "db_config.ini"
    yield project_root / "db_config.local.ini"

    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        yield Path(programdata) / "MahilMartPOS" / "db_config.ini"

    yield Path.home() / "MahilMartPOS" / "db_config.ini"


def _load_ini(path: Path) -> dict:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(path)
    except (OSError, configparser.Error):
        return {}

    if not parser.has_section("database"):
        return {}

    section = parser["database"]
    return {
        "ENGINE": section.get("engine", "").strip(),
        "NAME": section.get("name", "").strip(),
        "USER": section.get("user", "").strip(),
        "PASSWORD": section.get("password", "").strip(),
        "HOST": section.get("host", "").strip(),
        "PORT": section.get("port", "").strip(),
    }


def _pick(*values, default=""):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip() == "":
                continue
            return value.strip()
        return value
    return default


def load_db_config():
    for path in _candidate_paths():
        if path and path.is_file():
            data = _load_ini(path)
            if any(data.values()):
                data["__path__"] = str(path)
                return data
    return {}


def get_database_settings():
    file_cfg = load_db_config()
    return {
        "ENGINE": _pick(
            os.environ.get("MAHILMARTPOS_DB_ENGINE"),
            file_cfg.get("ENGINE"),
            _DEFAULTS["ENGINE"],
        ),
        "NAME": _pick(
            os.environ.get("MAHILMARTPOS_DB_NAME"),
            file_cfg.get("NAME"),
            _DEFAULTS["NAME"],
        ),
        "USER": _pick(
            os.environ.get("MAHILMARTPOS_DB_USER"),
            file_cfg.get("USER"),
            _DEFAULTS["USER"],
        ),
        "PASSWORD": _pick(
            os.environ.get("MAHILMARTPOS_DB_PASSWORD"),
            file_cfg.get("PASSWORD"),
            _DEFAULTS["PASSWORD"],
        ),
        "HOST": _pick(
            os.environ.get("MAHILMARTPOS_DB_HOST"),
            file_cfg.get("HOST"),
            _DEFAULTS["HOST"],
        ),
        "PORT": _pick(
            os.environ.get("MAHILMARTPOS_DB_PORT"),
            file_cfg.get("PORT"),
            _DEFAULTS["PORT"],
        ),
    }


def get_postgres_connect_kwargs():
    db = get_database_settings()
    return {
        "host": db.get("HOST"),
        "port": db.get("PORT"),
        "database": db.get("NAME"),
        "user": db.get("USER"),
        "password": db.get("PASSWORD"),
    }
