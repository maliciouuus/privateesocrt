from django.contrib import admin
from .models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Transaction,
    Payout,
    WhiteLabel,
    Banner,
    MarketingMaterial,
    PaymentMethod,
    AffiliateLevel,
    Badge,
    AffiliateProfile,
)
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count


@admin.register(ReferralClick)
class ReferralClickAdmin(admin.ModelAdmin):
    list_display = ("user", "referral_code", "ip_address", "clicked_at")
    list_filter = ("clicked_at", "user")
    search_fields = ("user__username", "referral_code", "ip_address")
    date_hierarchy = "clicked_at"


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred", "referral_code", "created_at")
    list_filter = ("created_at", "referrer")
    search_fields = ("referrer__username", "referred__username", "referral_code")
    date_hierarchy = "created_at"


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "created_at", "paid_at")
    list_filter = ("status", "created_at", "paid_at", "user")
    search_fields = ("user__username", "amount", "status")
    date_hierarchy = "created_at"
    actions = ["mark_as_paid", "mark_as_rejected"]

    def mark_as_paid(self, request, queryset):
        queryset.update(status="paid", paid_at=timezone.now())

    mark_as_paid.short_description = "Marquer comme payé"

    def mark_as_rejected(self, request, queryset):
        queryset.update(status="rejected")

    mark_as_rejected.short_description = "Marquer comme rejeté"


@admin.register(CommissionRate)
class CommissionRateAdmin(admin.ModelAdmin):
    list_display = ("ambassador", "target_type", "rate", "created_at", "updated_at")
    list_filter = ("target_type", "created_at")
    search_fields = ("ambassador__username", "rate")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("escort", "amount", "status", "payment_method", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("escort__username", "amount", "payment_id")
    date_hierarchy = "created_at"


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "ambassador",
        "amount",
        "payment_method",
        "status",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "payment_method", "created_at", "completed_at")
    search_fields = ("ambassador__username", "amount", "transaction_id")
    date_hierarchy = "created_at"
    actions = ["mark_as_completed", "mark_as_failed"]

    def mark_as_completed(self, request, queryset):
        queryset.update(status="completed", completed_at=timezone.now())

    mark_as_completed.short_description = "Marquer comme complété"

    def mark_as_failed(self, request, queryset):
        queryset.update(status="failed")

    mark_as_failed.short_description = "Marquer comme échoué"


@admin.register(WhiteLabel)
class WhiteLabelAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "ambassador", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "domain", "ambassador__username")
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            total_clicks=Count("referralclicks"),
            total_conversions=Count("referrals"),
            total_earnings=Sum("commissions__amount"),
        )

    def total_clicks(self, obj):
        return obj.total_clicks

    total_clicks.short_description = "Clics totaux"

    def total_conversions(self, obj):
        return obj.total_conversions

    total_conversions.short_description = "Conversions totales"

    def total_earnings(self, obj):
        return obj.total_earnings or 0

    total_earnings.short_description = "Gains totaux"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "white_label", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "white_label__name")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)

    def white_label_link(self, obj):
        url = reverse("admin:affiliate_whitelabel_change", args=[obj.white_label.id])
        return format_html('<a href="{}">{}</a>', url, obj.white_label.name)

    white_label_link.short_description = "Site White Label"


@admin.register(MarketingMaterial)
class MarketingMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "file_type", "is_active", "download_count", "created_at")
    list_filter = ("file_type", "is_active", "created_at")
    search_fields = ("title", "description")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "payment_type", "account_name", "is_default", "is_active")
    list_filter = ("payment_type", "is_default", "is_active")
    search_fields = ("user__username", "account_name")


@admin.register(AffiliateLevel)
class AffiliateLevelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "min_earnings",
        "min_referrals",
        "min_conversion_rate",
        "commission_bonus",
    )
    list_filter = ("name",)
    search_fields = ("name", "description")


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "points_value", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("name", "description")


@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "level",
        "points",
        "total_earnings",
        "total_referrals",
        "conversion_rate",
    )
    list_filter = ("level",)
    search_fields = ("user__username",)


# Personnalisation de l'interface d'administration
admin.site.site_header = "Administration EscortDollars"
admin.site.site_title = "EscortDollars Admin"
admin.site.index_title = "Tableau de bord"
