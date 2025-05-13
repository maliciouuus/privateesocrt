from apps.affiliate.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class SupabaseService:
    def __init__(self):
        self.supabase = get_supabase_client()

    def sync_commission(self, commission):
        """
        Synchronise une commission avec Supabase
        """
        try:
            data = {
                "id": str(commission.id),
                "user_id": str(commission.user.id),
                "referral_id": str(commission.referral.id),
                "amount": float(commission.amount),
                "status": commission.status,
                "transaction_id": commission.transaction_id,
                "created_at": commission.created_at.isoformat(),
                "paid_at": (commission.paid_at.isoformat() if commission.paid_at else None),
            }

            # Vérifier si la commission existe déjà
            existing = (
                self.supabase.table("commissions")
                .select("id")
                .eq("id", str(commission.id))
                .execute()
            )

            if existing.data:
                # Mettre à jour la commission existante
                self.supabase.table("commissions").update(data).eq(
                    "id", str(commission.id)
                ).execute()
                logger.info(f"Commission {commission.id} mise à jour dans Supabase")
            else:
                # Créer une nouvelle commission
                self.supabase.table("commissions").insert(data).execute()
                logger.info(f"Commission {commission.id} créée dans Supabase")

            return True
        except Exception as e:
            logger.exception(
                f"Erreur lors de la synchronisation de la commission {commission.id}: {str(e)}"
            )
            return False

    def get_ambassador_stats(self, ambassador_id):
        """
        Récupère les statistiques d'un ambassadeur depuis Supabase
        """
        try:
            result = (
                self.supabase.table("ambassador_stats")
                .select("*")
                .eq("ambassador_id", ambassador_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.exception(
                f"Erreur lors de la récupération des stats de l'ambassadeur {ambassador_id}: {str(e)}"
            )
            return None

    def get_white_label_stats(self, white_label_id):
        """
        Récupère les statistiques d'un site white label depuis Supabase
        """
        try:
            result = (
                self.supabase.table("white_label_stats")
                .select("*")
                .eq("white_label_id", white_label_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.exception(
                f"Erreur lors de la récupération des stats du white label {white_label_id}: {str(e)}"
            )
            return None

    def sync_white_label(self, white_label):
        """
        Synchronise un site white label avec Supabase
        """
        try:
            data = {
                "id": str(white_label.id),
                "name": white_label.name,
                "domain": white_label.domain,
                "primary_color": white_label.primary_color,
                "secondary_color": white_label.secondary_color,
                "is_active": white_label.is_active,
                "created_at": white_label.created_at.isoformat(),
                "updated_at": white_label.updated_at.isoformat(),
            }

            # Vérifier si le white label existe déjà
            existing = (
                self.supabase.table("white_labels")
                .select("id")
                .eq("id", str(white_label.id))
                .execute()
            )

            if existing.data:
                # Mettre à jour le white label existant
                self.supabase.table("white_labels").update(data).eq(
                    "id", str(white_label.id)
                ).execute()
                logger.info(f"White label {white_label.id} mis à jour dans Supabase")
            else:
                # Créer un nouveau white label
                self.supabase.table("white_labels").insert(data).execute()
                logger.info(f"White label {white_label.id} créé dans Supabase")

            return True
        except Exception as e:
            logger.exception(
                f"Erreur lors de la synchronisation du white label {white_label.id}: {str(e)}"
            )
            return False
