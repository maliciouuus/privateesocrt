"""
Configuration pour les tests.
Utilise la base de données Supabase existante pour les tests.
"""

from core.settings import *

# Utiliser la base de données Supabase pour les tests
# Pas besoin de redéfinir DATABASES puisqu'on utilise la même que settings.py

# Utiliser un hasheur de mot de passe rapide pour les tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Désactiver la journalisation pendant les tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['null'],
            'level': 'CRITICAL',
        },
    },
}

# Désactiver le cache pendant les tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Désactiver Celery pour les tests
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True 