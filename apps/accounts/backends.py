from django.contrib import messages
from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        activation_url = self.get_email_confirmation_url(request, emailconfirmation)

        # Stocker le lien d'activation dans la session
        request.session["activation_url"] = activation_url
        request.session["activation_email"] = emailconfirmation.email_address.email

        # Ajouter un message pour informer l'utilisateur
        messages.info(
            request,
            f"Lien d'activation pour {emailconfirmation.email_address.email}: {activation_url}",
        )

        return None  # Ne pas envoyer d'email réel
