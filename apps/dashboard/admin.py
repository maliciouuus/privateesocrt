from django.contrib import admin

from .models import Notification, UserStatistics


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "is_read", "created_at"]
    list_filter = ["is_read"]
    search_fields = ["title", "user__username"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]


@admin.register(UserStatistics)
class UserStatisticsAdmin(admin.ModelAdmin):
    list_display = ["user", "total_earnings", "total_referrals", "total_transactions"]
    list_filter = ["user"]
    search_fields = ["user__username"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
