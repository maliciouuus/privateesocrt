from django.shortcuts import render
from django.http import JsonResponse


def home(request):
    context = {}

    # Vérifier s'il y a un lien d'activation dans la session
    if "activation_url" in request.session:
        context["activation_url"] = request.session["activation_url"]
        context["activation_email"] = request.session["activation_email"]
        # Nettoyer la session
        del request.session["activation_url"]
        del request.session["activation_email"]

    return render(request, "home.html", context)


def home_luxury(request):
    """
    Vue pour la page d'accueil avec le design luxueux inspiré de GTA 6.
    Garde le même contenu que la page d'accueil d'origine mais avec un design amélioré.
    """
    return render(request, "home-luxury.html")


def home_ultra_luxury(request):
    """
    Vue pour la page d'accueil avec le design ultra-luxueux inspiré de GTA 6 et du lifestyle Andrew Tate.
    Version encore plus ambitieuse avec des effets visuels plus impressionnants et une esthétique masculine et luxueuse.
    """
    context = {}

    # Vérifier s'il y a un lien d'activation dans la session, comme dans la vue d'origine
    if "activation_url" in request.session:
        context["activation_url"] = request.session["activation_url"]
        context["activation_email"] = request.session["activation_email"]
        # Nettoyer la session
        del request.session["activation_url"]
        del request.session["activation_email"]

    return render(request, "home-ultra-luxury.html", context)


def health_check(request):
    """
    Simple health check endpoint for Docker and Kubernetes health probes.
    Returns a 200 OK response when the application is running.
    """
    return JsonResponse({"status": "ok"}, status=200)
