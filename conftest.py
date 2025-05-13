import os
import django
import pytest

# Définir les paramètres de la base de données de test
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings.test'


def pytest_configure():
    """
    Configuration pour les tests : utiliser la base de données Supabase existante
    """
    # Utiliser les paramètres définis dans settings/test.py
    django.setup()


@pytest.fixture(scope='function')
def db_access():
    """
    Fixture pour indiquer qu'un test a besoin d'accéder à la base de données.
    À utiliser avec @pytest.mark.usefixtures('db_access')
    """
    pass 