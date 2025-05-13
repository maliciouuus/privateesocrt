Configuration
============

Configuration de Base
------------------

1. Variables d'Environnement
~~~~~~~~~~~~~~~~~~~~~~~~~

Créer un fichier `.env` à la racine du projet avec les variables suivantes :

.. code-block:: text

   # Configuration Django
   DEBUG=True
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=localhost,127.0.0.1

   # Base de données
   DATABASE_URL=postgres://user:password@localhost:5432/escortdollars

   # Email
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   EMAIL_USE_TLS=True

   # AWS S3 (optionnel)
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_STORAGE_BUCKET_NAME=your-bucket-name

   # Redis (optionnel)
   REDIS_URL=redis://localhost:6379/0

2. Configuration Django
~~~~~~~~~~~~~~~~~~~~

Modifier `settings.py` pour configurer les paramètres principaux :

.. code-block:: python

   # Configuration de base
   DEBUG = os.getenv('DEBUG', 'False') == 'True'
   SECRET_KEY = os.getenv('SECRET_KEY')
   ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

   # Applications installées
   INSTALLED_APPS = [
       'django.contrib.admin',
       'django.contrib.auth',
       'django.contrib.contenttypes',
       'django.contrib.sessions',
       'django.contrib.messages',
       'django.contrib.staticfiles',
       'django.contrib.sites',
       
       # Applications tierces
       'allauth',
       'allauth.account',
       'allauth.socialaccount',
       'rest_framework',
       'corsheaders',
       
       # Applications locales
       'accounts',
       'affiliate',
       'whitelabel',
       'dashboard',
   ]

   # Middleware
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'django.contrib.sessions.middleware.SessionMiddleware',
       'corsheaders.middleware.CorsMiddleware',
       'django.middleware.common.CommonMiddleware',
       'django.middleware.csrf.CsrfViewMiddleware',
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'django.contrib.messages.middleware.MessageMiddleware',
       'django.middleware.clickjacking.XFrameOptionsMiddleware',
   ]

Configuration de la Base de Données
--------------------------------

1. PostgreSQL
~~~~~~~~~~~

.. code-block:: python

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.getenv('DB_NAME', 'escortdollars'),
           'USER': os.getenv('DB_USER', 'postgres'),
           'PASSWORD': os.getenv('DB_PASSWORD', ''),
           'HOST': os.getenv('DB_HOST', 'localhost'),
           'PORT': os.getenv('DB_PORT', '5432'),
       }
   }

2. Redis (Cache)
~~~~~~~~~~~~~

.. code-block:: python

   CACHES = {
       'default': {
           'BACKEND': 'django_redis.cache.RedisCache',
           'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
           'OPTIONS': {
               'CLIENT_CLASS': 'django_redis.client.DefaultClient',
           }
       }
   }

Configuration de l'Email
---------------------

1. SMTP
~~~~~

.. code-block:: python

   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
   EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
   EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
   EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
   EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
   EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
   DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

2. Templates d'Email
~~~~~~~~~~~~~~~~~

.. code-block:: python

   EMAIL_TEMPLATES = {
       'welcome': 'emails/welcome.html',
       'password_reset': 'emails/password_reset.html',
       'verification': 'emails/verification.html',
   }

Configuration de l'Authentification
-------------------------------

1. Django Allauth
~~~~~~~~~~~~~~

.. code-block:: python

   AUTHENTICATION_BACKENDS = [
       'django.contrib.auth.backends.ModelBackend',
       'allauth.account.auth_backends.AuthenticationBackend',
   ]

   SITE_ID = 1

   ACCOUNT_EMAIL_REQUIRED = True
   ACCOUNT_USERNAME_REQUIRED = True
   ACCOUNT_AUTHENTICATION_METHOD = 'email'
   ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
   ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
   ACCOUNT_LOGOUT_ON_GET = True
   ACCOUNT_UNIQUE_EMAIL = True
   ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3

2. JWT (API)
~~~~~~~~~~

.. code-block:: python

   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework_simplejwt.authentication.JWTAuthentication',
       ],
       'DEFAULT_PERMISSION_CLASSES': [
           'rest_framework.permissions.IsAuthenticated',
       ],
   }

   SIMPLE_JWT = {
       'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
       'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
       'ROTATE_REFRESH_TOKENS': False,
       'BLACKLIST_AFTER_ROTATION': True,
   }

Configuration des Fichiers Statiques
--------------------------------

1. Stockage Local
~~~~~~~~~~~~~~

.. code-block:: python

   STATIC_URL = '/static/'
   STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
   STATICFILES_DIRS = [
       os.path.join(BASE_DIR, 'static'),
   ]

   MEDIA_URL = '/media/'
   MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

2. AWS S3
~~~~~~~~

.. code-block:: python

   AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
   AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
   AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
   AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
   AWS_S3_OBJECT_PARAMETERS = {
       'CacheControl': 'max-age=86400',
   }

   STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
   DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

Configuration de la Sécurité
-------------------------

1. Paramètres de Base
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   SECURE_SSL_REDIRECT = not DEBUG
   SESSION_COOKIE_SECURE = not DEBUG
   CSRF_COOKIE_SECURE = not DEBUG
   SECURE_BROWSER_XSS_FILTER = True
   SECURE_CONTENT_TYPE_NOSNIFF = True
   X_FRAME_OPTIONS = 'DENY'
   SECURE_HSTS_SECONDS = 31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True

2. CORS
~~~~~~

.. code-block:: python

   CORS_ALLOWED_ORIGINS = [
       'http://localhost:3000',
       'https://your-domain.com',
   ]
   CORS_ALLOW_CREDENTIALS = True

Configuration du Logging
---------------------

.. code-block:: python

   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'formatters': {
           'verbose': {
               'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
               'style': '{',
           },
       },
       'handlers': {
           'file': {
               'level': 'INFO',
               'class': 'logging.FileHandler',
               'filename': 'debug.log',
               'formatter': 'verbose',
           },
       },
       'loggers': {
           'django': {
               'handlers': ['file'],
               'level': 'INFO',
               'propagate': True,
           },
       },
   }

Configuration des Tests
--------------------

.. code-block:: python

   TEST_RUNNER = 'django.test.runner.DiscoverRunner'
   TEST_DATABASE = {
       'ENGINE': 'django.db.backends.sqlite3',
       'NAME': ':memory:',
   }

Configuration du Déploiement
-------------------------

1. Gunicorn
~~~~~~~~~

.. code-block:: python

   # gunicorn.conf.py
   bind = 'unix:/run/gunicorn.sock'
   workers = 3
   timeout = 120
   accesslog = '-'
   errorlog = '-'
   capture_output = True
   enable_stdio_inheritance = True

2. Nginx
~~~~~~~

.. code-block:: nginx

   # nginx.conf
   upstream escortdollars {
       server unix:/run/gunicorn.sock;
   }

   server {
       listen 80;
       server_name your-domain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       location /static/ {
           root /path/to/escortdollars;
       }

       location / {
           include proxy_params;
           proxy_pass http://escortdollars;
       }
   } 