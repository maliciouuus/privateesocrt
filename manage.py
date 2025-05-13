#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import pathlib
from dotenv import load_dotenv

# Charger le .env AVANT tout import de Django
BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Debug: Afficher les variables de connexion
print("MANAGE.PY: Variables de connexion chargées depuis .env")
print(f"USER: {os.getenv('user')}")
print(f"HOST: {os.getenv('host')}")
print(f"DBNAME: {os.getenv('dbname')}")


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
