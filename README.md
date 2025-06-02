# Projet d'Intégration Django et Web3 avec TransactionContract (Modèles Séparés)

Ce projet démontre l'intégration d'un backend Django avec la blockchain Ethereum en utilisant Web3.py et le contrat `TransactionContract.sol`. Il inclut l'appel de fonctions du contrat, la gestion des événements `TransactionSubmitted` et `ContractEvent` stockés dans des modèles Django **séparés** (`Transaction` et `ContractEvent`), des API REST et GraphQL, et un système de polling d'événements avec Celery intégrant une détection de fraude (placeholder).

**NOTE IMPORTANTE :** Cette version utilise le contrat `TransactionContract.sol`, des modèles `Transaction` et `ContractEvent` distincts en base de données, et n'inclut **pas** d'authentification basée sur la signature MetaMask.

## Structure du Projet (Simplifiée)

```
web3_project/
├── api/                 # Application Django principale
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py        # Modèles Django (Transaction ET ContractEvent séparés)
│   ├── serializers.py   # Serializers DRF (pour les 2 modèles et inputs contrat)
│   ├── validators.py    # Validateurs blockchain
│   ├── views.py         # Vues DRF (API REST, interaction TransactionContract)
│   ├── authentication.py # (Fichier vidé)
│   ├── tasks.py         # Tâches Celery (polling, création Tx, lien Event, détection fraude)
│   └── schema.py        # Schéma GraphQL (Graphene pour les 2 modèles)
├── web3_project/        # Configuration du projet Django
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py      # Paramètres Django 
│   ├── urls.py          # URLs du projet
│   ├── wsgi.py
│   └── celery.py        # Configuration Celery
├── manage.py            # Utilitaire Django
├── requirements.txt     # Dépendances Python
├── README.md            # Ce fichier
└── GUIDE.md             # Guide détaillé pas à pas 
```
pour le smart contract j'ai utilisé RemixIde en ligne pour la création,la compilation et le déploiement des smart contract
## Fonctionnalités Implémentées

1.  **Smart Contract** (`contracts/TransactionContract.sol`): Contrat permettant d'émettre des événements `TransactionSubmitted` et `ContractEvent`.
2.  **Modèles Django Séparés** (`api/models.py`): 
    *   `Transaction`: Stocke les informations de base d'une transaction (hash, numéro de bloc).
    *   `ContractEvent`: Stocke les détails d'un événement (`TransactionSubmitted` ou `ContractEvent`), lié à une `Transaction` via une clé étrangère. Inclut des champs spécifiques extraits et un champ `is_fraudulent`.
3.  **Validateurs** (`api/validators.py`): Fonctions pour valider les formats blockchain.
4.  **Serializers DRF** (`api/serializers.py`): Pour les modèles `Transaction` et `ContractEvent` (montrant la relation), et des serializers d'input pour les fonctions du contrat.
5.  **API REST** (`api/views.py`, `web3_project/urls.py`, `api/urls.py`):
    *   Endpoints pour lister/récupérer les `Transaction` et les `ContractEvent` stockés.
    *   Endpoints pour invoquer les fonctions `submitTransaction` et `triggerEvent` du contrat.
6.  **GraphQL API** (`api/schema.py`):
    *   Types pour `Transaction` et `ContractEvent` exposant la relation.
    *   Requêtes pour récupérer les transactions (avec leurs événements) et les événements (avec leur transaction).
    *   Mutations pour appeler `submitTransaction` et `triggerEvent`.
8.  **Tâches Asynchrones (Celery)** (`web3_project/celery.py`, `api/tasks.py`):
    *   Configuration de Celery.
    *   Tâche `poll_contract_events` adaptée pour :
        *   Récupérer les événements `TransactionSubmitted` et `ContractEvent`.
        *   Créer automatiquement l'enregistrement `Transaction` si nécessaire.
        *   Créer l'enregistrement `ContractEvent` en le liant à la `Transaction` correspondante.
    *   **Intégration Détection Fraude (Placeholder)**.
    *   **Note Importante**: Exécution périodique désactivée, déclenchement manuel requis.

## Instructions de Configuration et Lancement

Consultez le fichier `GUIDE.md` (qui sera mis à jour) pour les instructions détaillées étape par étape concernant :

1.  La préparation de l'environnement.
2.  La configuration de Django (`settings.py`), y compris les variables pour `TransactionContract`.
3.  La compilation et le déploiement de `TransactionContract.sol`.
4.  L'exécution des migrations Django pour les modèles `Transaction` et `ContractEvent`.
5.  Le lancement des services.
6.  Le test des fonctionnalités, en tenant compte de la structure à deux modèles.



