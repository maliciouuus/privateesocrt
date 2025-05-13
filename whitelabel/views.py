from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from whitelabel.models import WhiteLabelSite


class SiteView(LoginRequiredMixin, View):
    def get(self, request, site_id):
        site = get_object_or_404(WhiteLabelSite, id=site_id, user=request.user)
        return redirect(f"http://{site.domain}")


class SiteEditView(LoginRequiredMixin, View):
    def get(self, request, site_id):
        site = get_object_or_404(WhiteLabelSite, id=site_id, user=request.user)
        return render(request, "whitelabel/sites/edit.html", {"site": site})

    def post(self, request, site_id):
        site = get_object_or_404(WhiteLabelSite, id=site_id, user=request.user)
        # Récupérer les données du formulaire
        site.name = request.POST.get("name")
        site.domain = request.POST.get("domain")
        site.logo = request.FILES.get("logo", site.logo)
        site.favicon = request.FILES.get("favicon", site.favicon)
        site.primary_color = request.POST.get("primary_color")
        site.secondary_color = request.POST.get("secondary_color")
        site.save()
        return redirect("/whitelabel/sites/")
