from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from .models import UserProfile


class UserRegistrationForm(UserCreationForm):
    """
    Formulaire d'inscription personnalisé pour les utilisateurs
    """

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Votre email"}),
    )
    first_name = forms.CharField(
        label=_("Prénom"),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Votre prénom"}),
    )
    last_name = forms.CharField(
        label=_("Nom"),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Votre nom"}),
    )
    date_of_birth = forms.DateField(
        label=_("Date de naissance"),
        required=True,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    account_type = forms.ChoiceField(
        label=_("Type de compte"),
        choices=[
            ("escort", _("Escorte")),
            ("member", _("Membre")),
        ],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "date_of_birth",
            "account_type",
            "password1",
            "password2",
        )
        widgets = {
            "password1": forms.PasswordInput(
                attrs={"class": "form-control", "placeholder": "Votre mot de passe"}
            ),
            "password2": forms.PasswordInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Confirmez votre mot de passe",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Cet email est déjà utilisé."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.birth_date = self.cleaned_data["date_of_birth"]
        user.user_type = self.cleaned_data["account_type"]

        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """
    Formulaire de connexion personnalisé
    """

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Votre email"}),
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Votre mot de passe"}
        ),
    )


class ProfileForm(forms.ModelForm):
    """
    Formulaire pour modifier le profil utilisateur
    """

    class Meta:
        model = UserProfile
        fields = [
            "company_name",
            "vat_id",
            "website",
            "address",
            "zip_code",
            "city",
            "country",
            "usdt_trc20_wallet",
            "btc_wallet",
            "eth_erc20_wallet",
            "dark_mode",
            "newsletter_subscribed",
            "preferred_language",
            "theme_color",
            "display_mode",
            "email_notifications",
            "sms_notifications",
            "two_factor_enabled",
            "escort_commission_rate",
            "ambassador_commission_rate",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "vat_id": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "zip_code": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "usdt_trc20_wallet": forms.TextInput(attrs={"class": "form-control"}),
            "btc_wallet": forms.TextInput(attrs={"class": "form-control"}),
            "eth_erc20_wallet": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_language": forms.Select(attrs={"class": "form-control"}),
            "theme_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
            "display_mode": forms.Select(attrs={"class": "form-control"}),
        }


class ProfileEditForm(forms.ModelForm):
    """
    Formulaire pour modifier les informations de base du profil
    """

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ProfileEditForm, self).__init__(*args, **kwargs)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class EmailVerificationForm(forms.Form):
    """
    Formulaire pour la vérification d'email
    """

    code = forms.CharField(
        label=_("Code de vérification"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Entrez le code reçu par email",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            self.fields["email"].initial = self.user.email
            self.fields["bio"].initial = self.user.bio
            self.fields["phone_number"].initial = self.user.phone_number
            self.fields["birth_date"].initial = self.user.birth_date
            self.fields["telegram_username"].initial = self.user.telegram_username

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data["first_name"]
            self.user.last_name = self.cleaned_data["last_name"]
            self.user.email = self.cleaned_data["email"]
            self.user.bio = self.cleaned_data["bio"]
            self.user.phone_number = self.cleaned_data["phone_number"]
            self.user.birth_date = self.cleaned_data["birth_date"]
            self.user.telegram_username = self.cleaned_data["telegram_username"]
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile

    def clean_telegram_username(self):
        username = self.cleaned_data.get("telegram_username", "")
        if username and not username.startswith("@"):
            return "@" + username
        return username
