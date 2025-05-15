from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Adaptateur personnalisé pour Allauth qui gère l'inscription et la connexion
    """

    def is_open_for_signup(self, request):
        return True

    def get_signup_redirect_url(self, request):
        messages.success(
            request,
            "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter.",
        )
        return reverse("accounts:login")

    def get_login_redirect_url(self, request):
        return reverse("dashboard:simple_dashboard")

    def pre_login(self, request, user, **kwargs):
        """
        Active automatiquement le compte lors de l'inscription
        """
        user.is_active = True
        user.save()
        return None

    def save_user(self, request, user, form, commit=True):
        """
        Surcharge de la méthode save_user pour ajouter des fonctionnalités personnalisées
        """
        user = super().save_user(request, user, form, commit=False)
        user.is_active = True
        if commit:
            user.save()
        return user
