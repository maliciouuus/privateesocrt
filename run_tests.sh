#!/bin/bash

# Script pour exécuter tous les tests unitaires qui ne dépendent pas de la base de données

# Définir les variables d'environnement
export DJANGO_SETTINGS_MODULE=core.settings.test

# Exécuter les tests unitaires
echo "Exécution des tests unitaires qui ne dépendent pas de la base de données..."
python3 manage.py test \
    apps.dashboard.tests.test_utils \
    apps.dashboard.tests.test_formatting \
    apps.accounts.tests.test_validators \
    apps.accounts.tests.test_phone_validation

echo ""
echo "Tests unitaires terminés." 