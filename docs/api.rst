API Publique
===========

Le système EscortDollars met à disposition des APIs publiques pour interagir avec la plateforme. 
Ces APIs ne nécessitent pas d'authentification et peuvent être utilisées par n'importe quelle application tierce.

API White Labels
---------------

L'API White Labels permet de récupérer la liste de tous les sites white label actifs sur la plateforme.

Endpoint
~~~~~~~~

.. code-block:: text

    GET /api/affiliate/public/whitelabels/

Paramètres
~~~~~~~~~~

Cette API ne nécessite aucun paramètre.

Réponse
~~~~~~~

La réponse est un tableau JSON contenant la liste des sites white label actifs.

.. code-block:: json

    [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Exemple de White Label",
            "domain": "example.escortdollars.com",
            "custom_domain": "example.com",
            "logo_url": "https://example.escortdollars.com/media/whitelabels/logos/logo.png",
            "favicon_url": "https://example.escortdollars.com/media/whitelabels/favicons/favicon.ico",
            "primary_color": "#7C4DFF",
            "secondary_color": "#FF4D94",
            "created_at": "2023-01-01T00:00:00Z"
        }
    ]

Champs de la réponse
~~~~~~~~~~~~~~~~~~~

- **id** : Identifiant unique du site white label
- **name** : Nom du site white label
- **domain** : Domaine principal du site
- **custom_domain** : Domaine personnalisé (si vérifié, sinon null)
- **logo_url** : URL du logo du site (si disponible, sinon null)
- **favicon_url** : URL du favicon du site (si disponible, sinon null)
- **primary_color** : Couleur principale du site (code hexadécimal)
- **secondary_color** : Couleur secondaire du site (code hexadécimal)
- **created_at** : Date de création du site white label

Exemple d'utilisation
~~~~~~~~~~~~~~~~~~~~~

Avec cURL
^^^^^^^^^

.. code-block:: bash

    curl -X GET "https://api.escortdollars.com/api/affiliate/public/whitelabels/" -H "accept: application/json"

Avec JavaScript
^^^^^^^^^^^^^^

.. code-block:: javascript

    fetch('https://api.escortdollars.com/api/affiliate/public/whitelabels/')
        .then(response => response.json())
        .then(data => console.log(data))
        .catch(error => console.error('Erreur:', error));

Avec Python
^^^^^^^^^^^

.. code-block:: python

    import requests
    
    response = requests.get('https://api.escortdollars.com/api/affiliate/public/whitelabels/')
    white_labels = response.json()
    
    for wl in white_labels:
        print(f"White Label: {wl['name']} - Domain: {wl['domain']}")

Limites d'utilisation
~~~~~~~~~~~~~~~~~~~~

Pour éviter les abus, cette API est limitée à 100 requêtes par adresse IP par heure.
Si vous dépassez cette limite, vous recevrez une réponse avec le code d'état HTTP 429.

API Referral Externe
-------------------

L'API Referral Externe permet à des applications tierces d'enregistrer des parrainages 
depuis des sites externes. Pour plus d'informations, consultez la documentation spécifique
de cette API.

Endpoint
~~~~~~~~

.. code-block:: text

    POST /api/affiliate/external/referral/

API Inscription Parrainage
------------------------

Cette API permet à des sites externes d'enregistrer une inscription avec un code de parrainage,
sans avoir besoin d'implémenter toute la logique d'affiliation.

Endpoint
~~~~~~~~

.. code-block:: text

    POST /api/affiliate/signup/referral/

Paramètres
~~~~~~~~~~

Cette API attend un objet JSON avec les paramètres suivants :

.. code-block:: json

    {
        "referral_code": "code_parrainage",
        "user_email": "email@example.com",
        "user_name": "John Doe",
        "source": "external_site"
    }

Paramètres requis :
    - **referral_code** : Le code de parrainage utilisé
    - **user_email** : L'email de l'utilisateur parrainé

Paramètres optionnels :
    - **user_name** : Le nom de l'utilisateur parrainé
    - **source** : La source du parrainage (nom du site externe, par défaut "api")

Réponse
~~~~~~~

En cas de succès (code HTTP 201) :

.. code-block:: json

    {
        "success": true,
        "message": "Parrainage enregistré avec succès.",
        "referral_id": "550e8400-e29b-41d4-a716-446655440000"
    }

En cas d'erreur :

.. code-block:: json

    {
        "success": false,
        "message": "Message d'erreur spécifique"
    }

Codes d'erreur possibles :
    - **400 Bad Request** : Paramètres manquants ou invalides
    - **404 Not Found** : Code de parrainage invalide
    - **409 Conflict** : Utilisateur déjà inscrit
    - **500 Internal Server Error** : Erreur interne du serveur

Exemple d'utilisation
~~~~~~~~~~~~~~~~~~~~~

Avec cURL
^^^^^^^^^

.. code-block:: bash

    curl -X POST "https://api.escortdollars.com/api/affiliate/signup/referral/" \
        -H "Content-Type: application/json" \
        -d '{
            "referral_code": "AB123456", 
            "user_email": "john@example.com", 
            "user_name": "John Doe", 
            "source": "my-external-site"
        }'

Avec JavaScript
^^^^^^^^^^^^^^

.. code-block:: javascript

    fetch('https://api.escortdollars.com/api/affiliate/signup/referral/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            referral_code: 'AB123456',
            user_email: 'john@example.com',
            user_name: 'John Doe',
            source: 'my-external-site'
        }),
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Erreur:', error));

Avec Python
^^^^^^^^^^^

.. code-block:: python

    import requests
    
    data = {
        "referral_code": "AB123456",
        "user_email": "john@example.com",
        "user_name": "John Doe",
        "source": "my-external-site"
    }
    
    response = requests.post('https://api.escortdollars.com/api/affiliate/signup/referral/', json=data)
    result = response.json()
    
    if response.status_code == 201:
        print(f"Parrainage réussi avec ID: {result['referral_id']}")
    else:
        print(f"Erreur: {result['message']}") 