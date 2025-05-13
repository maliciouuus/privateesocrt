from dataclasses import dataclass


@dataclass
class Notification:
    """
    Classe utilitaire pour créer des notifications sans avoir besoin
    de créer un objet en base de données.
    Utilisée principalement pour l'envoi de notifications via Telegram.
    """

    title: str
    message: str
    notification_type: str = "info"
    url: str = None

    def __str__(self):
        return f"{self.title}: {self.message}"
