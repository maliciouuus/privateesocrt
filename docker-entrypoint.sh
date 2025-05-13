#!/bin/bash

# Création des répertoires nécessaires
mkdir -p /app/logs
touch /app/logs/affiliate.log
chmod -R 777 /app/logs

# Assurer que les répertoires media et staticfiles existent et ont les bonnes permissions
mkdir -p /app/media /app/staticfiles
chmod -R 755 /app/media /app/staticfiles

# Collecter les fichiers statiques
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Exécuter les migrations (commenter si non nécessaire en production)
# echo "Applying migrations..."
# python manage.py migrate --noinput

# Démarrage de l'application
echo "Starting application..."
exec "$@" 