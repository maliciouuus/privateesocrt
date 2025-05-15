from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum
from django.utils import timezone
from django.http import HttpResponse
from django.conf import settings
import csv
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
import uuid

from ..models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Payout,
    WhiteLabel,
)
from ..serializers import (
    ReferralClickSerializer,
    ReferralSerializer,
    CommissionSerializer,
    CommissionRateSerializer,
    PayoutSerializer,
    WhiteLabelSerializer,
    AmbassadorStatsSerializer,
    WhiteLabelStatsSerializer,
)
from ..services import SupabaseService
from ..services.telegram_service import TelegramService

User = get_user_model()


class IsAmbassador(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_ambassador


class IsEscort(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_escort


class ReferralClickViewSet(viewsets.ModelViewSet):
    queryset = ReferralClick.objects.all()
    serializer_class = ReferralClickSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(referrer=self.request.user)


class CommissionViewSet(viewsets.ModelViewSet):
    queryset = Commission.objects.all()
    serializer_class = CommissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        commission = self.get_object()
        commission.status = "paid"
        commission.paid_at = timezone.now()
        commission.save()
        return Response({"status": "commission marked as paid"})

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        queryset = self.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="commissions.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "User",
                "Referral",
                "Amount",
                "Status",
                "Transaction ID",
                "Created At",
                "Paid At",
            ]
        )
        for commission in queryset:
            writer.writerow(
                [
                    commission.id,
                    commission.user.username,
                    commission.referral.id if commission.referral else "",
                    commission.amount,
                    commission.status,
                    commission.transaction_id,
                    commission.created_at,
                    commission.paid_at,
                ]
            )
        return response


class CommissionRateViewSet(viewsets.ModelViewSet):
    queryset = CommissionRate.objects.all()
    serializer_class = CommissionRateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(ambassador=self.request.user)


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(ambassador=self.request.user)

    @action(detail=True, methods=["post"])
    def request_payout(self, request, pk=None):
        payout = self.get_object()
        if payout.status != "pending":
            return Response(
                {"error": "Ce paiement a déjà été traité."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier le solde disponible
        available_balance = request.user.pending_commission
        if available_balance < payout.amount:
            return Response({"error": "Solde insuffisant."}, status=status.HTTP_400_BAD_REQUEST)

        # Traiter le paiement
        payout.status = "processing"
        payout.save()

        return Response({"status": "Paiement en cours de traitement."})


class WhiteLabelViewSet(viewsets.ModelViewSet):
    queryset = WhiteLabel.objects.all()
    serializer_class = WhiteLabelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(is_active=True)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        white_label = self.get_object()
        supabase = SupabaseService()
        stats = supabase.get_white_label_stats(str(white_label.id))
        serializer = WhiteLabelStatsSerializer(stats)
        return Response(serializer.data)


# La classe BannerViewSet est temporairement désactivée car le modèle Banner a été supprimé
# class BannerViewSet(viewsets.ModelViewSet):
#     queryset = Banner.objects.all()
#     serializer_class = BannerSerializer
#     permission_classes = [IsAmbassador]
# 
#     def get_queryset(self):
#         return Banner.objects.filter(white_label__ambassador=self.request.user)


class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAmbassador]

    @action(detail=False, methods=["get"])
    def ambassador(self, request):
        # Récupérer les statistiques depuis Supabase
        supabase = SupabaseService()
        stats = supabase.get_ambassador_stats(str(request.user.id))

        if not stats:
            # Calculer les statistiques localement si non disponibles dans Supabase
            stats = {
                "total_referrals": Referral.objects.filter(referrer=request.user).count(),
                "total_commissions": Commission.objects.filter(user=request.user).aggregate(
                    total=Sum("amount")
                )["total"]
                or 0,
                "pending_commissions": Commission.objects.filter(
                    user=request.user, status="pending"
                ).aggregate(total=Sum("amount"))["total"]
                or 0,
                "total_payouts": Payout.objects.filter(ambassador=request.user).aggregate(
                    total=Sum("amount")
                )["total"]
                or 0,
                "conversion_rate": self._calculate_conversion_rate(request.user),
            }

        serializer = AmbassadorStatsSerializer(stats)
        return Response(serializer.data)

    def _calculate_conversion_rate(self, user):
        clicks = ReferralClick.objects.filter(referral_code__startswith=user.username).count()
        referrals = Referral.objects.filter(referrer=user).count()
        return (referrals / clicks * 100) if clicks > 0 else 0


class ExternalReferralAPI(APIView):
    """
    API pour enregistrer une inscription externe avec code de parrainage
    """
    permission_classes = [permissions.AllowAny]  # API publique

    def post(self, request, format=None):
        # Vérifier les données requises
        ref_code = request.data.get('ref_code')
        user_id = request.data.get('user_id')
        username = request.data.get('username')
        email = request.data.get('email')
        
        if not ref_code or not user_id:
            return Response(
                {"error": "Le code de parrainage et l'ID utilisateur sont requis."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trouver l'ambassadeur par code de parrainage
        try:
            referrer = User.objects.get(referral_code=ref_code, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "Code de parrainage invalide."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier si c'est un nouvel utilisateur ou une mise à jour
        referred, created = User.objects.get_or_create(
            supabase_id=user_id,
            defaults={
                'username': username or f"user_{user_id[:8]}",
                'email': email or f"user_{user_id[:8]}@example.com",
                'referred_by': referrer
            }
        )
        
        # Si ce n'est pas un nouvel utilisateur, mettre à jour le parrain si non défini
        if not created and not referred.referred_by:
            referred.referred_by = referrer
            referred.save()
        
        # Créer l'objet Referral s'il n'existe pas déjà
        referral, ref_created = Referral.objects.get_or_create(
            referrer=referrer,
            referred=referred,
            defaults={
                'referral_code': ref_code
            }
        )
        
        # Envoyer notification Telegram seulement si nouvelle référence
        if ref_created:
            telegram_service = TelegramService()
            telegram_service.notify_new_referral(referrer, referred)
        
        return Response({
            "success": True,
            "message": "Parrainage enregistré avec succès.",
            "referral_id": str(referral.id),
            "created": ref_created
        }, status=status.HTTP_201_CREATED if ref_created else status.HTTP_200_OK)


class PublicWhiteLabelAPI(APIView):
    """
    API publique pour récupérer la liste des sites white label actifs.
    
    Cette API ne nécessite pas d'authentification et permet à n'importe quelle application 
    externe d'obtenir la liste des sites white label disponibles sur la plateforme.
    
    Les données sensibles comme les informations d'ambassadeur sont exclues de la réponse.
    """
    permission_classes = [permissions.AllowAny]  # API publique
    
    def get(self, request, format=None):
        """
        Récupère la liste de tous les sites white label actifs.
        
        Les données retournées incluent uniquement les informations publiques 
        comme le nom, le domaine, le logo et les couleurs du site.
        
        Une notification Telegram est envoyée si cette fonctionnalité est activée dans les paramètres.
        
        Returns:
            Response: Une liste de dictionnaires contenant les informations des sites white label actifs.
                      Chaque dictionnaire contient les champs suivants:
                      - id: Identifiant unique du site white label
                      - name: Nom du site white label
                      - domain: Domaine principal du site
                      - custom_domain: Domaine personnalisé (si vérifié)
                      - logo_url: URL du logo du site (si disponible)
                      - primary_color: Couleur principale du site (code hexadécimal)
                      - secondary_color: Couleur secondaire du site (code hexadécimal)
        """
        # Récupérer tous les sites white label actifs
        whitelabels = WhiteLabel.objects.filter(is_active=True)
        
        # Sérialiser les données avec moins d'informations pour l'API publique
        data = []
        for wl in whitelabels:
            # Déterminer quel domaine utiliser
            domain = wl.custom_domain if wl.dns_verified and wl.custom_domain else wl.domain
            
            data.append({
                "id": str(wl.id),
                "name": wl.name,
                "domain": domain,
                "custom_domain": wl.custom_domain if wl.dns_verified else None,
                "logo_url": request.build_absolute_uri(wl.logo.url) if wl.logo else None,
                "favicon_url": request.build_absolute_uri(wl.favicon.url) if wl.favicon else None,
                "primary_color": wl.primary_color,
                "secondary_color": wl.secondary_color,
                "created_at": wl.created_at
            })
        
        # Notification Telegram si activé
        if getattr(settings, 'TELEGRAM_NOTIFY_API_CALLS', False):
            telegram_service = TelegramService()
            telegram_service.send_message(
                f"🔍 <b>API Request</b>\n\n"
                f"Liste des White Labels demandée\n"
                f"IP: {request.META.get('REMOTE_ADDR')}\n"
                f"User Agent: {request.META.get('HTTP_USER_AGENT', 'Non spécifié')}\n"
                f"Nombre d'entrées: {len(data)}"
            )
        
        return Response(data)


class ReferralSignupAPI(APIView):
    """
    API publique pour notifier le système qu'un utilisateur s'est inscrit avec un code de parrainage.
    
    Cette API permet à des sites externes d'enregistrer une inscription avec un code de parrainage,
    sans avoir besoin d'implémenter toute la logique d'affiliation. Cela permet une intégration simple
    avec des systèmes tiers.
    
    Le système vérifie le code de parrainage, crée les relations nécessaires et envoie
    une notification Telegram à l'ambassadeur.
    """
    permission_classes = [permissions.AllowAny]  # API publique
    
    def post(self, request, format=None):
        """
        Enregistre un nouvel utilisateur parrainé via un code.
        
        Cette méthode vérifie la validité du code de parrainage, crée un enregistrement
        de parrainage et envoie une notification Telegram à l'ambassadeur.
        
        Args:
            request: La requête HTTP contenant les données du parrainage
            
        Request Body:
            {
                "referral_code": "code_parrainage",  # Obligatoire - Le code de parrainage utilisé
                "user_email": "email@example.com",   # Obligatoire - L'email de l'utilisateur parrainé
                "user_name": "John Doe",             # Optionnel - Le nom de l'utilisateur parrainé
                "source": "external_site"            # Optionnel - La source du parrainage
            }
            
        Returns:
            Response: Un objet JSON contenant le statut de l'opération:
                {
                    "success": true/false,
                    "message": "Message de statut",
                    "referral_id": "ID du parrainage créé" (si success=true)
                }
        """
        # Extraire et valider les données
        referral_code = request.data.get('referral_code')
        user_email = request.data.get('user_email')
        user_name = request.data.get('user_name', '')
        source = request.data.get('source', 'api')
        
        # Valider les champs obligatoires
        if not referral_code or not user_email:
            return Response({
                "success": False, 
                "message": "Le code de parrainage et l'email de l'utilisateur sont obligatoires."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier la validité du code de parrainage
        try:
            ambassador = User.objects.get(referral_code=referral_code, is_active=True)
        except User.DoesNotExist:
            return Response({
                "success": False, 
                "message": "Code de parrainage invalide."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier si l'utilisateur existe déjà par email
        user_exists = User.objects.filter(email=user_email).exists()
        if user_exists:
            return Response({
                "success": False, 
                "message": "Cet utilisateur est déjà inscrit."
            }, status=status.HTTP_409_CONFLICT)
        
        # Créer un nouvel utilisateur "référé" temporaire
        try:
            username = user_email.split('@')[0]
            if User.objects.filter(username=username).exists():
                username = f"{username}_{uuid.uuid4().hex[:6]}"
                
            referred_user = User.objects.create_user(
                username=username,
                email=user_email,
                password=uuid.uuid4().hex,  # Mot de passe aléatoire, l'utilisateur devra le changer
                first_name=user_name.split(' ')[0] if ' ' in user_name else user_name,
                last_name=user_name.split(' ')[1] if ' ' in user_name else '',
                is_active=True,
                referred_by=ambassador
            )
            
            # Créer l'enregistrement de parrainage
            referral = Referral.objects.create(
                referrer=ambassador,
                referred=referred_user,
                referral_code=referral_code
            )
            
            # Envoyer notification Telegram
            telegram_service = TelegramService()
            telegram_service.notify_new_referral(
                ambassador, 
                referred_user, 
                custom_message=f"Source: {source}"
            )
            
            return Response({
                "success": True,
                "message": "Parrainage enregistré avec succès.",
                "referral_id": str(referral.id)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Erreur lors de l'enregistrement du parrainage: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
