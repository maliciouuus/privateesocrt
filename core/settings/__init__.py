from dotenv import load_dotenv
import os
import pathlib
from .base import *  # Déplacé en haut du fichier

# Charger les variables d'environnement avant tout
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Chargement explicite des variables pour la base de données
DB_USER = os.getenv("user")
DB_PASSWORD = os.getenv("password")
DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("dbname")

# Chargement explicite des autres variables d'environnement
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Debug: Print les variables DB
print("SETTINGS/__INIT__.PY: Variables de connexion chargées!")
print(f"BD DB_HOST={DB_HOST}, DB_USER={DB_USER}, DB_NAME={DB_NAME}")

# Surcouche pour la base de données
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
}

# Supprimer les apps non utilisées ou redondantes
INSTALLED_APPS = [
    app
    for app in INSTALLED_APPS
    if app
    not in [
        "allauth.socialaccount",  # On garde allauth.account mais pas socialaccount
        "drf_yasg",  # Swagger non nécessaire en production
    ]
]
