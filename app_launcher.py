import os
import threading
import time
import webbrowser


def _open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MahilMartPOS.settings")

    threading.Thread(target=_open_browser, daemon=True).start()
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8000"])


if __name__ == "__main__":
    main()
