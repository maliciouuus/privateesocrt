Modèles de données
===============

Cette section documente les principaux modèles utilisés dans la plateforme EscortDollars.
Les modèles sont organisés par application et représentent la structure de la base de données.

Vue d'ensemble
------------

Le système est conçu autour de plusieurs entités principales :

1. **Utilisateurs et Profils** - Gestion des utilisateurs, ambassadeurs et leurs profils
2. **Système d'affiliation** - Gestion des parrainages et clics de référence
3. **Commissions et Paiements** - Suivi des commissions et paiements aux ambassadeurs
4. **White Label** - Personnalisation des sites d'affiliation

Modèles de l'application Affiliate
--------------------------------

.. automodule:: apps.affiliate.models
    :members:
    :undoc-members:
    :show-inheritance:

Utilisateurs et Profils
---------------------

User
~~~~

Le modèle ``User`` étend le modèle utilisateur Django standard avec des fonctionnalités spécifiques à l'affiliation.

Attributs principaux:
 * ``username`` - Nom d'utilisateur unique
 * ``email`` - Adresse email de l'utilisateur
 * ``is_active`` - Statut d'activation
 * ``is_ambassador`` - Indique si l'utilisateur est un ambassadeur
 * ``referral_code`` - Code de parrainage unique
 * ``referred_by`` - Référence à l'utilisateur parrain (si applicable)

UserProfile
~~~~~~~~~~

Le profil utilisateur contient des informations supplémentaires sur l'utilisateur.

Attributs principaux:
 * ``user`` - Relation one-to-one avec le modèle User
 * ``bio`` - Biographie de l'utilisateur
 * ``phone`` - Numéro de téléphone
 * ``address`` - Adresse postale
 * ``profile_picture`` - Image de profil

AffiliateProfile
~~~~~~~~~~~~~~~

Ce profil spécifique est créé pour les ambassadeurs et contient les informations liées au programme d'affiliation.

Attributs principaux:
 * ``user`` - Relation one-to-one avec le modèle User
 * ``commission_rate`` - Taux de commission personnalisé
 * ``payment_methods`` - Méthodes de paiement préférées
 * ``stats`` - Statistiques de performance

Système d'affiliation
-------------------

Referral
~~~~~~~

Le modèle ``Referral`` représente une relation de parrainage entre deux utilisateurs.

Attributs principaux:
 * ``referrer`` - Ambassadeur qui a parrainé
 * ``referred`` - Utilisateur parrainé
 * ``referral_code`` - Code utilisé pour le parrainage
 * ``created_at`` - Date de création du parrainage
 * ``status`` - Statut du parrainage (actif, suspendu, etc.)

ReferralClick
~~~~~~~~~~~~

Ce modèle enregistre les clics sur les liens de parrainage pour mesurer les conversions.

Attributs principaux:
 * ``referral_code`` - Code de parrainage cliqué
 * ``ip_address`` - Adresse IP du visiteur
 * ``user_agent`` - User-Agent du navigateur
 * ``timestamp`` - Date et heure du clic
 * ``converted`` - Indique si le clic a mené à une conversion

Commissions et Paiements
----------------------

Commission
~~~~~~~~~

Le modèle ``Commission`` représente une commission gagnée par un ambassadeur.

Attributs principaux:
 * ``user`` - Ambassadeur recevant la commission
 * ``referral`` - Parrainage associé (si applicable)
 * ``amount`` - Montant de la commission
 * ``commission_type`` - Type de commission (inscription, achat, etc.)
 * ``status`` - Statut (en attente, payé, annulé)
 * ``created_at`` - Date de création
 * ``paid_at`` - Date de paiement (si payée)

CommissionRate
~~~~~~~~~~~~~

Ce modèle définit les différents taux de commission applicables.

Attributs principaux:
 * ``ambassador`` - Ambassadeur concerné
 * ``rate`` - Taux de commission (pourcentage)
 * ``commission_type`` - Type de commission
 * ``is_active`` - Indique si ce taux est actif

Payout
~~~~~~

Le modèle ``Payout`` représente un paiement effectué à un ambassadeur.

Attributs principaux:
 * ``ambassador`` - Ambassadeur recevant le paiement
 * ``amount`` - Montant du paiement
 * ``payment_method`` - Méthode de paiement utilisée
 * ``status`` - Statut (en attente, traité, complété)
 * ``reference`` - Référence du paiement
 * ``created_at`` - Date de création
 * ``processed_at`` - Date de traitement

PaymentMethod
~~~~~~~~~~~~

Ce modèle stocke les méthodes de paiement disponibles pour les ambassadeurs.

Attributs principaux:
 * ``ambassador`` - Ambassadeur concerné
 * ``method_type`` - Type de méthode (crypto, virement, etc.)
 * ``details`` - Détails du compte de paiement
 * ``is_default`` - Indique si c'est la méthode par défaut

White Label
---------

WhiteLabel
~~~~~~~~~

Le modèle ``WhiteLabel`` permet de créer des sites d'affiliation personnalisés.

Attributs principaux:
 * ``name`` - Nom du site
 * ``domain`` - Domaine du site
 * ``logo`` - Logo personnalisé
 * ``primary_color`` - Couleur principale
 * ``secondary_color`` - Couleur secondaire
 * ``is_active`` - Statut d'activation
 * ``created_at`` - Date de création

Notifications
-----------

Notification
~~~~~~~~~~~

Le modèle ``Notification`` gère les notifications envoyées aux utilisateurs.

Attributs principaux:
 * ``user`` - Destinataire de la notification
 * ``message`` - Contenu de la notification
 * ``notification_type`` - Type de notification
 * ``is_read`` - Indique si la notification a été lue
 * ``created_at`` - Date de création

Intégrations et interactions entre modèles
----------------------------------------

Le schéma ci-dessous illustre les relations entre les principaux modèles :

.. code-block::

    User <-- UserProfile
     |
     +-- AffiliateProfile
     |    |
     |    +-- PaymentMethod
     |    |
     |    +-- CommissionRate
     |
     +-- referred_by --> User
     |
     +-- Referral (referrer)
     |    |
     |    +-- User (referred)
     |
     +-- ReferralClick
     |
     +-- Commission
     |    |
     |    +-- Referral
     |
     +-- Payout
     |
     +-- WhiteLabel
     |
     +-- Notification

Cette structure de données est conçue pour offrir une flexibilité maximale tout en maintenant l'intégrité des relations entre les différentes entités du système. 