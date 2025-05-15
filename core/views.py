import json
from django.shortcuts import render
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


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


def health_check(request):
    """
    Health check endpoint pour vérifier que le service est opérationnel.
    Utilisé par les équilibreurs de charge et les systèmes de monitoring.
    """
    # Informations de base sur l'état du service
    data = {
        "status": "online",
        "message": "Service is running normally",
    }

    return JsonResponse(data)
