from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from django.http import HttpResponse
import csv

from ..models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Transaction,
    Payout,
    WhiteLabel,
    Banner,
)
from ..serializers import (
    ReferralClickSerializer,
    ReferralSerializer,
    CommissionSerializer,
    CommissionRateSerializer,
    TransactionSerializer,
    PayoutSerializer,
    WhiteLabelSerializer,
    BannerSerializer,
    AmbassadorStatsSerializer,
    WhiteLabelStatsSerializer,
)
from ..services import SupabaseService


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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(escort=self.request.user)


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


class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    permission_classes = [IsAmbassador]

    def get_queryset(self):
        return Banner.objects.filter(white_label__ambassador=self.request.user)


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
