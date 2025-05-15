from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Commission,
    Payout,
    CommissionRate,
    WhiteLabel,
    PaymentMethod,
)


class CommissionForm(forms.ModelForm):
    class Meta:
        model = Commission
        fields = ["amount", "status"]
        widgets = {
            "status": forms.Select(
                choices=[
                    ("pending", _("En attente")),
                    ("approved", _("Approuvé")),
                    ("rejected", _("Rejeté")),
                    ("paid", _("Payé")),
                ]
            )
        }


class PayoutForm(forms.ModelForm):
    class Meta:
        model = Payout
        fields = ["amount", "payment_method", "wallet_address"]
        widgets = {
            "payment_method": forms.Select(
                choices=[
                    ("bitcoin", _("Bitcoin")),
                    ("ethereum", _("Ethereum")),
                    ("tether", _("Tether")),
                ]
            ),
            "wallet_address": forms.TextInput(attrs={"placeholder": _("Adresse du portefeuille")}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < 50:
            raise forms.ValidationError(_("Le montant minimum pour un paiement est de 50€."))
        return amount


class CommissionRateForm(forms.ModelForm):
    """
    Formulaire pour la gestion des taux de commission personnalisés
    """

    class Meta:
        model = CommissionRate
        fields = ["target_type", "rate"]
        widgets = {
            "rate": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "5", "max": "50"}
            ),
            "target_type": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        self.ambassador = kwargs.pop("ambassador", None)
        super().__init__(*args, **kwargs)

        # Ajouter des labels et des helptext
        self.fields["target_type"].label = _("Type d'utilisateur")
        self.fields["target_type"].help_text = _(
            "Type d'utilisateur pour lequel ce taux s'applique"
        )

        self.fields["rate"].label = _("Taux (%)")
        self.fields["rate"].help_text = _("Taux de commission en pourcentage (entre 5% et 50%)")

    def clean(self):
        cleaned_data = super().clean()
        rate = cleaned_data.get("rate")

        # Vérifier les limites du taux
        if rate and (rate < 5 or rate > 50):
            raise forms.ValidationError(_("Le taux doit être compris entre 5% et 50%"))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.ambassador:
            instance.ambassador = self.ambassador

        if commit:
            instance.save()

            # Synchroniser avec Supabase
            try:
                from .services import SupabaseService

                supabase = SupabaseService()
                supabase.sync_commission_rate(instance)
            except Exception as e:
                import logging

                logging.error(f"Erreur lors de la synchronisation du taux de commission: {str(e)}")

        return instance


class WhiteLabelForm(forms.ModelForm):
    """
    Formulaire pour la création et l'édition d'un site white label
    """

    class Meta:
        model = WhiteLabel
        fields = [
            "name",
            "domain",
            "custom_domain",
            "primary_color",
            "secondary_color",
            "logo",
            "favicon",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "domain": forms.TextInput(attrs={"class": "form-control"}),
            "custom_domain": forms.TextInput(attrs={"class": "form-control"}),
            "primary_color": forms.TextInput(
                attrs={"class": "form-control color-picker", "type": "color"}
            ),
            "secondary_color": forms.TextInput(
                attrs={"class": "form-control color-picker", "type": "color"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.ambassador = kwargs.pop("ambassador", None)
        super().__init__(*args, **kwargs)

        # Ajouter des labels et des helptext
        self.fields["name"].help_text = _("Nom de votre site white label")
        self.fields["domain"].help_text = _(
            "Sous-domaine de votre site white label (ex: monsite.escortdollars.com)"
        )
        self.fields["custom_domain"].help_text = _(
            "Domaine personnalisé (optionnel, nécessite une vérification DNS)"
        )
        self.fields["primary_color"].help_text = _("Couleur principale du site")
        self.fields["secondary_color"].help_text = _("Couleur secondaire du site")
        self.fields["logo"].help_text = _(
            "Logo de votre site (format recommandé: PNG/SVG, taille max: 2MB)"
        )
        self.fields["favicon"].help_text = _(
            "Favicon (icône de votre site dans les onglets du navigateur)"
        )
        self.fields["is_active"].help_text = _("Activer ou désactiver le site")

    def clean_domain(self):
        domain = self.cleaned_data.get("domain", "").lower()
        domain = domain.replace("http://", "").replace("https://", "").rstrip("/")

        # Vérifier que le domaine est unique
        if (
            WhiteLabel.objects.filter(domain=domain)
            .exclude(pk=self.instance.pk if self.instance.pk else None)
            .exists()
        ):
            raise forms.ValidationError(_("Ce domaine est déjà utilisé"))

        return domain

    def clean_custom_domain(self):
        custom_domain = self.cleaned_data.get("custom_domain", "").lower()
        if not custom_domain:
            return custom_domain

        custom_domain = custom_domain.replace("http://", "").replace("https://", "").rstrip("/")

        # Vérifier que le domaine personnalisé est unique
        if (
            WhiteLabel.objects.filter(custom_domain=custom_domain)
            .exclude(pk=self.instance.pk if self.instance.pk else None)
            .exists()
        ):
            raise forms.ValidationError(_("Ce domaine personnalisé est déjà utilisé"))

        return custom_domain

    def clean(self):
        cleaned_data = super().clean()

        # Vérifier que l'utilisateur a moins de 3 sites white label (sauf si édition)
        if self.ambassador and not self.instance.pk:
            existing_count = WhiteLabel.objects.filter(ambassador=self.ambassador).count()
            if existing_count >= 3:
                raise forms.ValidationError(
                    _("Vous ne pouvez pas avoir plus de 3 sites white label")
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.ambassador:
            instance.ambassador = self.ambassador

        if commit:
            instance.save()

            # Synchroniser avec Supabase
            try:
                from .services import SupabaseService

                supabase = SupabaseService()
                supabase.sync_white_label(instance)
            except Exception as e:
                import logging

                logging.error(f"Erreur lors de la synchronisation du white label: {str(e)}")

        return instance


class CryptoPaymentForm(forms.Form):
    amount = forms.DecimalField(
        min_value=50,
        max_digits=10,
        decimal_places=2,
        label=_("Montant"),
        widget=forms.NumberInput(attrs={"min": 50, "step": 0.01}),
    )
    currency = forms.ChoiceField(
        choices=[
            ("BTC", _("Bitcoin")),
            ("ETH", _("Ethereum")),
            ("USDT", _("Tether")),
        ],
        label=_("Devise"),
    )
    wallet_address = forms.CharField(
        max_length=100,
        label=_("Adresse du portefeuille"),
        widget=forms.TextInput(attrs={"placeholder": _("Entrez votre adresse de portefeuille")}),
    )


class PaymentMethodForm(forms.ModelForm):
    """Formulaire pour les méthodes de paiement."""

    class Meta:
        model = PaymentMethod
        fields = ["payment_type", "account_name", "account_details"]
        widgets = {
            "account_details": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_type"].widget.attrs.update({"class": "form-control"})
        self.fields["account_name"].widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get("payment_type")
        account_details = {}

        if payment_type == "bank":
            account_details = {
                "iban": self.data.get("iban"),
                "bic": self.data.get("bic"),
                "bank_name": self.data.get("bank_name"),
            }
        elif payment_type == "paypal":
            account_details = {
                "email": self.data.get("paypal_email"),
            }
        elif payment_type == "crypto":
            account_details = {
                "wallet_address": self.data.get("wallet_address"),
                "crypto_type": self.data.get("crypto_type"),
            }

        cleaned_data["account_details"] = account_details
        return cleaned_data
