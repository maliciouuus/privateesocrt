from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.accounts.models import User
from apps.whitelabel.models import WhiteLabel


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return [
            "home",
            "about",
            "pricing",
            "contact",
            "terms",
            "privacy",
            "faq",
            "blog",
        ]

    def location(self, item):
        return reverse(item)


class EscortSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return User.objects.filter(is_active=True, user_type="escort")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("escort_profile", args=[obj.username])


class WhiteLabelSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return WhiteLabel.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("whitelabel_home", args=[obj.domain])
