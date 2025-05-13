Architecture Technique
====================

Vue d'ensemble
------------

EscortDollars est construit sur une architecture moderne et évolutive, utilisant Django comme framework principal.
L'architecture est conçue pour être modulaire, maintenable et évolutive.

Structure du Projet
----------------

.. code-block:: text

   escortdollars/
   ├── accounts/              # Application de gestion des comptes
   ├── affiliate/            # Application de parrainage
   ├── whitelabel/           # Application White Label
   ├── dashboard/            # Application de tableau de bord
   ├── core/                 # Fonctionnalités centrales
   ├── templates/            # Templates HTML
   ├── static/              # Fichiers statiques
   ├── media/               # Fichiers média
   └── escortdollars/       # Configuration du projet

Composants Principaux
------------------

1. Application Accounts
~~~~~~~~~~~~~~~~~~~~

Gestion des utilisateurs et de l'authentification.

* Modèles
  * User
  * Profile
  * UserSettings

* Vues
  * Inscription
  * Connexion
  * Gestion du profil
  * Récupération de mot de passe

* URLs
  * /accounts/signup/
  * /accounts/login/
  * /accounts/profile/
  * /accounts/password/

2. Application Affiliate
~~~~~~~~~~~~~~~~~~~~~

Système de parrainage et de commissions.

* Modèles
  * AffiliateLink
  * Commission
  * Referral
  * Payout

* Vues
  * Gestion des liens
  * Suivi des conversions
  * Historique des commissions
  * Demandes de paiement

* URLs
  * /affiliate/links/
  * /affiliate/stats/
  * /affiliate/payouts/
  * /affiliate/referrals/

3. Application White Label
~~~~~~~~~~~~~~~~~~~~~~~

Solution de marque blanche.

* Modèles
  * WhiteLabelSite
  * CustomDomain
  * SiteSettings
  * Branding

* Vues
  * Configuration du site
  * Gestion des domaines
  * Personnalisation
  * Statistiques

* URLs
  * /whitelabel/sites/
  * /whitelabel/domains/
  * /whitelabel/settings/
  * /whitelabel/stats/

4. Application Dashboard
~~~~~~~~~~~~~~~~~~~~~

Tableau de bord analytique.

* Modèles
  * Dashboard
  * Widget
  * Report
  * Notification

* Vues
  * Vue d'ensemble
  * Rapports détaillés
  * Configuration des widgets
  * Notifications

* URLs
  * /dashboard/
  * /dashboard/reports/
  * /dashboard/widgets/
  * /dashboard/notifications/

Base de Données
-------------

Schéma Principal
~~~~~~~~~~~~~

.. code-block:: sql

   -- Users et Profils
   CREATE TABLE accounts_user (
       id SERIAL PRIMARY KEY,
       username VARCHAR(150) UNIQUE,
       email VARCHAR(254) UNIQUE,
       password VARCHAR(128),
       is_active BOOLEAN,
       date_joined TIMESTAMP
   );

   CREATE TABLE accounts_profile (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES accounts_user(id),
       bio TEXT,
       avatar VARCHAR(255),
       created_at TIMESTAMP
   );

   -- Parrainage
   CREATE TABLE affiliate_affiliatelink (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES accounts_user(id),
       code VARCHAR(50) UNIQUE,
       created_at TIMESTAMP
   );

   CREATE TABLE affiliate_commission (
       id SERIAL PRIMARY KEY,
       affiliate_id INTEGER REFERENCES accounts_user(id),
       amount DECIMAL(10,2),
       status VARCHAR(20),
       created_at TIMESTAMP
   );

   -- White Label
   CREATE TABLE whitelabel_whitelabelsite (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES accounts_user(id),
       domain VARCHAR(255),
       settings JSONB,
       created_at TIMESTAMP
   );

Sécurité
-------

1. Authentification
~~~~~~~~~~~~~~~~

* Django Allauth pour l'authentification
* Authentification à deux facteurs
* Protection contre les attaques par force brute
* Sessions sécurisées

2. Autorisation
~~~~~~~~~~~~

* Système de permissions basé sur les rôles
* Vérification des accès par niveau
* Protection des routes sensibles
* Validation des tokens

3. Protection des Données
~~~~~~~~~~~~~~~~~~~~~

* Chiffrement des données sensibles
* Protection CSRF
* Validation des entrées
* Sanitization des sorties

API
---

1. Endpoints Principaux
~~~~~~~~~~~~~~~~~~~~

* /api/v1/auth/
  * POST /login/
  * POST /register/
  * POST /logout/
  * GET /user/

* /api/v1/affiliate/
  * GET /links/
  * POST /links/
  * GET /stats/
  * GET /commissions/

* /api/v1/whitelabel/
  * GET /sites/
  * POST /sites/
  * PUT /sites/{id}/
  * DELETE /sites/{id}/

2. Authentification API
~~~~~~~~~~~~~~~~~~~~

* JWT (JSON Web Tokens)
* OAuth2 pour les intégrations tierces
* Rate limiting
* Validation des requêtes

Performance
----------

1. Optimisations
~~~~~~~~~~~~~

* Mise en cache avec Redis
* Optimisation des requêtes DB
* Compression des assets
* CDN pour les fichiers statiques

2. Monitoring
~~~~~~~~~~

* Logging structuré
* Métriques de performance
* Alertes automatiques
* Rapports d'erreurs

Déploiement
----------

1. Infrastructure
~~~~~~~~~~~~~

* Serveurs web: Nginx
* Serveur d'application: Gunicorn
* Base de données: PostgreSQL
* Cache: Redis
* Stockage: AWS S3

2. CI/CD
~~~~~~~

* Tests automatisés
* Déploiement continu
* Vérification de la qualité du code
* Monitoring des performances

3. Scaling
~~~~~~~~

* Load balancing
* Réplication de base de données
* Mise en cache distribuée
* Gestion des sessions 