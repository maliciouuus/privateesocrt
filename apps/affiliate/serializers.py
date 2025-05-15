from rest_framework import serializers
from .models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Payout,
    WhiteLabel,
)
from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "user_type", "is_ambassador", "is_escort"]


class ReferralClickSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ReferralClick
        fields = [
            "id",
            "user",
            "referral_code",
            "ip_address",
            "user_agent",
            "clicked_at",
        ]


class ReferralSerializer(serializers.ModelSerializer):
    referrer = UserSerializer(read_only=True)
    referred = UserSerializer(read_only=True)

    class Meta:
        model = Referral
        fields = ["id", "referrer", "referred", "referral_code", "created_at"]


class CommissionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    referral = ReferralSerializer(read_only=True)

    class Meta:
        model = Commission
        fields = [
            "id",
            "user",
            "referral",
            "amount",
            "status",
            "transaction_id",
            "created_at",
            "paid_at",
        ]


class CommissionRateSerializer(serializers.ModelSerializer):
    ambassador = UserSerializer(read_only=True)

    class Meta:
        model = CommissionRate
        fields = ["id", "ambassador", "target_type", "rate", "created_at", "updated_at"]


class PayoutSerializer(serializers.ModelSerializer):
    ambassador = UserSerializer(read_only=True)
    commissions = CommissionSerializer(many=True, read_only=True)

    class Meta:
        model = Payout
        fields = [
            "id",
            "ambassador",
            "amount",
            "status",
            "payment_method",
            "payment_reference",
            "created_at",
            "completed_at",
            "commissions",
        ]


class WhiteLabelSerializer(serializers.ModelSerializer):
    ambassador = UserSerializer(read_only=True)

    class Meta:
        model = WhiteLabel
        fields = [
            "id",
            "ambassador",
            "name",
            "domain",
            "logo",
            "primary_color",
            "secondary_color",
            "is_active",
            "created_at",
            "updated_at",
        ]


# Le sérialiseur Banner est temporairement désactivé car le modèle Banner a été supprimé
# class BannerSerializer(serializers.ModelSerializer):
#     white_label = WhiteLabelSerializer(read_only=True)
# 
#     class Meta:
#         model = Banner
#         fields = [
#             "id",
#             "white_label",
#             "title",
#             "image",
#             "link",
#             "is_active",
#             "created_at",
#             "updated_at",
#         ]


# Sérialiseurs pour les statistiques
class AmbassadorStatsSerializer(serializers.Serializer):
    total_referrals = serializers.IntegerField()
    total_commissions = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_commissions = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_payouts = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.FloatField()


class WhiteLabelStatsSerializer(serializers.Serializer):
    total_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    total_commissions = serializers.DecimalField(max_digits=10, decimal_places=2)
