# Taux de commission par défaut pour les différents types d'utilisateurs
COMMISSION_RATES = {
    "escort": 30.0,  # 30% pour les escortes
    "ambassador": 20.0,  # 20% pour les ambassadeurs
    "premium": 40.0,  # 40% pour les affiliés premium
}

# Montant minimum pour un paiement
MIN_PAYOUT_AMOUNT = 50.0  # 50€ minimum

# Statuts des commissions
COMMISSION_STATUS = {
    "pending": "En attente",
    "approved": "Approuvée",
    "rejected": "Rejetée",
    "paid": "Payée",
}

# Statuts des paiements
PAYOUT_STATUS = {
    "pending": "En attente",
    "processing": "En cours de traitement",
    "completed": "Terminé",
    "failed": "Échoué",
}

# Types de paiement acceptés
PAYMENT_METHODS = {
    "bank_transfer": "Virement bancaire",
    "paypal": "PayPal",
    "crypto": "Cryptomonnaie",
}

# Niveaux d'affiliation
AFFILIATE_LEVELS = {
    "bronze": {
        "name": "Bronze",
        "min_earnings": 0,
        "commission_bonus": 0,
    },
    "silver": {
        "name": "Argent",
        "min_earnings": 1000,
        "commission_bonus": 5,
    },
    "gold": {
        "name": "Or",
        "min_earnings": 5000,
        "commission_bonus": 10,
    },
    "platinum": {
        "name": "Platine",
        "min_earnings": 10000,
        "commission_bonus": 15,
    },
}

# Durée de validité des liens d'affiliation (en jours)
REFERRAL_LINK_VALIDITY = 30

# Nombre minimum de parrainages pour devenir ambassadeur
MIN_REFERRALS_FOR_AMBASSADOR = 5

# Montant minimum des gains pour devenir ambassadeur
MIN_EARNINGS_FOR_AMBASSADOR = 1000.0
