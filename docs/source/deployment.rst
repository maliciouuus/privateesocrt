Déploiement
==========

Prérequis
--------

1. Serveur
~~~~~~~~

- Ubuntu 20.04 LTS ou supérieur
- 2 CPU minimum
- 4GB RAM minimum
- 20GB espace disque minimum

2. Logiciels Requis
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Mise à jour du système
   sudo apt update
   sudo apt upgrade -y

   # Installation des dépendances système
   sudo apt install -y python3-pip python3-dev python3-venv nginx postgresql postgresql-contrib redis-server

   # Installation de Node.js et npm
   curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
   sudo apt install -y nodejs

Préparation de l'Environnement
---------------------------

1. Création de l'Utilisateur
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Création de l'utilisateur
   sudo useradd -m -s /bin/bash escortdollars
   sudo usermod -aG sudo escortdollars

   # Configuration du mot de passe
   sudo passwd escortdollars

2. Configuration de PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Création de la base de données
   sudo -u postgres psql
   CREATE DATABASE escortdollars;
   CREATE USER escortdollars WITH PASSWORD 'your-password';
   GRANT ALL PRIVILEGES ON DATABASE escortdollars TO escortdollars;
   \q

3. Configuration de Redis
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Édition de la configuration Redis
   sudo nano /etc/redis/redis.conf

   # Ajout des paramètres de sécurité
   bind 127.0.0.1
   requirepass your-redis-password

   # Redémarrage de Redis
   sudo systemctl restart redis

Déploiement de l'Application
-------------------------

1. Cloner le Projet
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Connexion en tant qu'utilisateur escortdollars
   sudo su - escortdollars

   # Clonage du projet
   git clone https://github.com/your-username/escortdollars.git
   cd escortdollars

2. Configuration de l'Environnement Virtuel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Création de l'environnement virtuel
   python3 -m venv venv
   source venv/bin/activate

   # Installation des dépendances
   pip install -r requirements.txt

3. Configuration des Variables d'Environnement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Création du fichier .env
   nano .env

   # Ajout des variables d'environnement
   DEBUG=False
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=your-domain.com
   DATABASE_URL=postgres://escortdollars:your-password@localhost:5432/escortdollars
   REDIS_URL=redis://:your-redis-password@localhost:6379/0

4. Migrations et Collecte des Fichiers Statiques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Application des migrations
   python manage.py migrate

   # Création du superutilisateur
   python manage.py createsuperuser

   # Collecte des fichiers statiques
   python manage.py collectstatic

Configuration de Gunicorn
----------------------

1. Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Installation de Gunicorn
   pip install gunicorn

2. Configuration
~~~~~~~~~~~~

.. code-block:: bash

   # Création du fichier de configuration
   nano gunicorn.conf.py

   # Ajout de la configuration
   bind = 'unix:/run/gunicorn.sock'
   workers = 3
   timeout = 120
   accesslog = '-'
   errorlog = '-'
   capture_output = True
   enable_stdio_inheritance = True

3. Service Systemd
~~~~~~~~~~~~~~

.. code-block:: bash

   # Création du service
   sudo nano /etc/systemd/system/escortdollars.service

   # Configuration du service
   [Unit]
   Description=EscortDollars Gunicorn Service
   After=network.target

   [Service]
   User=escortdollars
   Group=www-data
   WorkingDirectory=/home/escortdollars/escortdollars
   Environment="PATH=/home/escortdollars/escortdollars/venv/bin"
   ExecStart=/home/escortdollars/escortdollars/venv/bin/gunicorn --config gunicorn.conf.py escortdollars.wsgi:application

   [Install]
   WantedBy=multi-user.target

   # Activation et démarrage du service
   sudo systemctl enable escortdollars
   sudo systemctl start escortdollars

Configuration de Nginx
-------------------

1. Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Installation de Nginx
   sudo apt install -y nginx

2. Configuration
~~~~~~~~~~~~

.. code-block:: bash

   # Création de la configuration
   sudo nano /etc/nginx/sites-available/escortdollars

   # Ajout de la configuration
   upstream escortdollars {
       server unix:/run/gunicorn.sock;
   }

   server {
       listen 80;
       server_name your-domain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       location /static/ {
           root /home/escortdollars/escortdollars;
       }

       location / {
           include proxy_params;
           proxy_pass http://escortdollars;
       }
   }

   # Activation du site
   sudo ln -s /etc/nginx/sites-available/escortdollars /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx

Configuration SSL
--------------

1. Installation de Certbot
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Installation de Certbot
   sudo apt install -y certbot python3-certbot-nginx

2. Obtention du Certificat
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Obtention du certificat SSL
   sudo certbot --nginx -d your-domain.com

Maintenance
---------

1. Mise à Jour de l'Application
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Connexion en tant qu'utilisateur escortdollars
   sudo su - escortdollars

   # Mise à jour du code
   cd escortdollars
   git pull

   # Activation de l'environnement virtuel
   source venv/bin/activate

   # Mise à jour des dépendances
   pip install -r requirements.txt

   # Application des migrations
   python manage.py migrate

   # Collecte des fichiers statiques
   python manage.py collectstatic

   # Redémarrage du service
   sudo systemctl restart escortdollars

2. Sauvegarde
~~~~~~~~~~

.. code-block:: bash

   # Création du script de sauvegarde
   nano backup.sh

   # Ajout du script
   #!/bin/bash
   BACKUP_DIR="/home/escortdollars/backups"
   DATE=$(date +%Y-%m-%d_%H-%M-%S)
   mkdir -p $BACKUP_DIR

   # Sauvegarde de la base de données
   pg_dump -U escortdollars escortdollars > $BACKUP_DIR/db_$DATE.sql

   # Sauvegarde des fichiers média
   tar -czf $BACKUP_DIR/media_$DATE.tar.gz /home/escortdollars/escortdollars/media

   # Suppression des sauvegardes plus anciennes que 7 jours
   find $BACKUP_DIR -type f -mtime +7 -delete

   # Rendre le script exécutable
   chmod +x backup.sh

   # Ajout d'une tâche cron
   crontab -e
   0 2 * * * /home/escortdollars/backup.sh

3. Surveillance
~~~~~~~~~~~

.. code-block:: bash

   # Installation des outils de surveillance
   sudo apt install -y htop iotop

   # Configuration de la surveillance des logs
   sudo nano /etc/logrotate.d/escortdollars

   /home/escortdollars/escortdollars/logs/*.log {
       daily
       missingok
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 escortdollars www-data
   }

Dépannage
--------

1. Vérification des Logs
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Logs Nginx
   sudo tail -f /var/log/nginx/error.log

   # Logs Gunicorn
   sudo journalctl -u escortdollars

   # Logs de l'application
   tail -f /home/escortdollars/escortdollars/logs/debug.log

2. Problèmes Courants
~~~~~~~~~~~~~~~~~~

- Erreur 502 Bad Gateway
  - Vérifier que Gunicorn est en cours d'exécution
  - Vérifier les permissions du socket
  - Vérifier les logs Nginx et Gunicorn

- Erreur 500 Internal Server Error
  - Vérifier les logs de l'application
  - Vérifier les permissions des fichiers
  - Vérifier la configuration Django

- Problèmes de Base de Données
  - Vérifier la connexion PostgreSQL
  - Vérifier les migrations
  - Vérifier les permissions de la base de données

3. Commandes Utiles
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Vérification du statut des services
   sudo systemctl status nginx
   sudo systemctl status escortdollars
   sudo systemctl status postgresql
   sudo systemctl status redis

   # Redémarrage des services
   sudo systemctl restart nginx
   sudo systemctl restart escortdollars
   sudo systemctl restart postgresql
   sudo systemctl restart redis

   # Vérification des ports
   sudo netstat -tulpn | grep LISTEN

   # Vérification de l'espace disque
   df -h
   du -sh /home/escortdollars/* 