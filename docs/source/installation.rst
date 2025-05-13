Installation et Configuration
===========================

Prérequis
--------

* Python 3.8 ou supérieur
* PostgreSQL 12 ou supérieur
* Node.js 14 ou supérieur (pour les assets frontend)
* Git

Installation
-----------

1. Cloner le dépôt
~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/yourusername/escortdollars.git
   cd escortdollars

2. Créer un environnement virtuel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # Sur Windows: venv\Scripts\activate

3. Installer les dépendances
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install -r requirements.txt

4. Configuration de l'environnement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Créer un fichier `.env` à la racine du projet avec les variables suivantes :

.. code-block:: text

   DEBUG=True
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgres://user:password@localhost:5432/escortdollars
   ALLOWED_HOSTS=localhost,127.0.0.1
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   EMAIL_USE_TLS=True

5. Configuration de la base de données
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python manage.py migrate
   python manage.py createsuperuser

6. Collecter les fichiers statiques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python manage.py collectstatic

7. Lancer le serveur de développement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python manage.py runserver

Configuration Avancée
------------------

Configuration de PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~

1. Créer la base de données :

.. code-block:: sql

   CREATE DATABASE escortdollars;
   CREATE USER escortdollars_user WITH PASSWORD 'your_password';
   ALTER ROLE escortdollars_user SET client_encoding TO 'utf8';
   ALTER ROLE escortdollars_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE escortdollars_user SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE escortdollars TO escortdollars_user;

2. Mettre à jour les paramètres de base de données dans `settings.py` :

.. code-block:: python

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'escortdollars',
           'USER': 'escortdollars_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }

Configuration de l'Email
~~~~~~~~~~~~~~~~~~~~~

1. Pour Gmail, activer l'authentification à deux facteurs
2. Générer un mot de passe d'application
3. Configurer les paramètres SMTP dans `.env`

Configuration de la Sécurité
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Générer une nouvelle clé secrète :

.. code-block:: bash

   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

2. Mettre à jour `SECRET_KEY` dans `.env`
3. Configurer `ALLOWED_HOSTS` pour la production
4. Désactiver `DEBUG` en production

Configuration du Déploiement
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Installer les dépendances système :

.. code-block:: bash

   sudo apt-get update
   sudo apt-get install python3-dev python3-pip python3-venv postgresql postgresql-contrib nginx

2. Configurer Nginx :

.. code-block:: nginx

   server {
       listen 80;
       server_name your-domain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       location /static/ {
           root /path/to/escortdollars;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/run/gunicorn.sock;
       }
   }

3. Configurer Gunicorn :

.. code-block:: bash

   sudo nano /etc/systemd/system/gunicorn.service

.. code-block:: ini

   [Unit]
   Description=gunicorn daemon
   Requires=gunicorn.socket
   After=network.target

   [Service]
   User=your-user
   Group=www-data
   WorkingDirectory=/path/to/escortdollars
   ExecStart=/path/to/venv/bin/gunicorn \
       --access-logfile - \
       --workers 3 \
       --bind unix:/run/gunicorn.sock \
       escortdollars.wsgi:application

   [Install]
   WantedBy=multi-user.target

Dépannage
--------

Problèmes Courants
~~~~~~~~~~~~~~~~

1. Erreur de connexion à la base de données
   * Vérifier les paramètres de connexion
   * S'assurer que PostgreSQL est en cours d'exécution
   * Vérifier les permissions de l'utilisateur

2. Erreurs de migration
   * Supprimer les fichiers de migration problématiques
   * Recréer les migrations : `python manage.py makemigrations`
   * Appliquer les migrations : `python manage.py migrate`

3. Problèmes de fichiers statiques
   * Vérifier les permissions des dossiers
   * Exécuter `python manage.py collectstatic`
   * Vérifier la configuration de Nginx

4. Erreurs d'email
   * Vérifier les paramètres SMTP
   * S'assurer que l'authentification à deux facteurs est activée
   * Vérifier le mot de passe d'application

Support
------

Pour toute question ou problème, veuillez :

1. Consulter la documentation
2. Vérifier les issues sur GitHub
3. Contacter l'équipe de support 