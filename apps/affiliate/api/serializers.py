from rest_framework import serializers
from ..models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Payout,
    WhiteLabel,
)


class ReferralClickSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralClick
        fields = ["id", "referral_code", "ip_address", "user_agent", "clicked_at"]
        read_only_fields = ["clicked_at"]


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = ["id", "referrer", "referred", "referral_code", "created_at"]
        read_only_fields = ["created_at"]


class CommissionSerializer(serializers.ModelSerializer):
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
        read_only_fields = ["created_at", "paid_at"]


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id",
            "ambassador",
            "amount",
            "payment_method",
            "wallet_address",
            "status",
            "transaction_id",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = ["created_at", "updated_at", "completed_at"]


class CommissionRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionRate
        fields = ["id", "ambassador", "target_type", "rate", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class WhiteLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhiteLabel
        fields = [
            "id",
            "name",
            "domain",
            "primary_color",
            "secondary_color",
            "logo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# Cette classe est obsolète car le modèle Banner a été supprimé
# class BannerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Banner
#         fields = [
#             "id",
#             "title",
#             "white_label",
#             "image",
#             "link",
#             "is_active",
#             "created_at",
#         ]
#         read_only_fields = ["created_at"]
