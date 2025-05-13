#!/usr/bin/env python3
"""
Script pour exécuter les tests d'intégration qui utilisent Supabase
sans créer une base de données de test séparée.
"""

import os
import sys
import unittest
import django
from django.test.runner import DiscoverRunner

# Définir les variables d'environnement
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.test")

# Initialiser Django
django.setup()


class NoDbTestRunner(DiscoverRunner):
    """Test runner qui n'essaie pas de créer une base de données de test."""
    
    def setup_databases(self, **kwargs):
        """Ne rien faire lors de la configuration des bases de données."""
        return {}
    
    def teardown_databases(self, old_config, **kwargs):
        """Ne rien faire lors du nettoyage des bases de données."""
        pass


def run_tests():
    """Exécuter les tests spécifiés."""
    test_modules = [
        'apps.accounts.tests.test_validators',
        'apps.accounts.tests.test_phone_validation',
        'apps.dashboard.tests.test_utils',
        'apps.dashboard.tests.test_formatting',
    ]
    
    # Vous pouvez ajouter ici d'autres tests qui ne nécessitent pas de base de données
    # ou des tests d'intégration qui fonctionnent avec la base de données existante
    
    test_suite = unittest.defaultTestLoader.loadTestsFromNames(test_modules)
    test_runner = NoDbTestRunner(verbosity=1, interactive=True)
    result = test_runner.run_suite(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(not success)  # 0 en cas de succès, 1 en cas d'échec 