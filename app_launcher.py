import os
import shutil
import threading
import time
import webbrowser
import sys


def _open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/")


def _is_frozen():
    return bool(getattr(sys, "frozen", False))


def _get_user_db_path():
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or os.path.expanduser("~")
    data_dir = os.path.join(base, "MahilMartPOS", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "db.sqlite3")


def _get_bundled_db_path():
    base = getattr(sys, "_MEIPASS", os.getcwd())
    return os.path.join(base, "db.sqlite3")


def _ensure_sqlite_db():
    user_db = _get_user_db_path()
    os.environ["MAHILMARTPOS_SQLITE"] = "1"
    os.environ["MAHILMARTPOS_SQLITE_PATH"] = user_db

    needs_migrate = False
    if not os.path.exists(user_db):
        bundled_db = _get_bundled_db_path()
        if os.path.exists(bundled_db):
            shutil.copy2(bundled_db, user_db)
        else:
            open(user_db, "a").close()
        needs_migrate = True

    if needs_migrate:
        import django
        django.setup()
        from django.core.management import call_command
        call_command("migrate", interactive=False)


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MahilMartPOS.settings")

    if _is_frozen():
        _ensure_sqlite_db()

    threading.Thread(target=_open_browser, daemon=True).start()
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8000"])


if __name__ == "__main__":
    main()
