#!/bin/bash

# Création des répertoires nécessaires
mkdir -p /app/logs
touch /app/logs/affiliate.log
chmod -R 777 /app/logs

# Démarrage de l'application
exec "$@" 