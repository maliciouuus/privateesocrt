from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import MarketingMaterial


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return [
            "affiliate:home",
            "affiliate:links",
            "affiliate:marketing_materials",
            "affiliate:banners",
        ]

    def location(self, item):
        return reverse(item)


class MarketingMaterialSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return MarketingMaterial.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": StaticViewSitemap,
    "marketing_materials": MarketingMaterialSitemap,
}
