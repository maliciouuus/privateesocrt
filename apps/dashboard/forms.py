from django import forms
from django.utils.translation import gettext_lazy as _


class TelegramSettingsForm(forms.Form):
    """
    Formulaire pour configurer les préférences Telegram
    """

    telegram_chat_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 123456789"}),
    )

    enable_telegram = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    telegram_language = forms.ChoiceField(
        choices=[
            ("fr", _("Français")),
            ("en", _("English")),
            ("es", _("Español")),
            ("de", _("Deutsch")),
            ("it", _("Italiano")),
            ("ru", _("Русский")),
            ("ar", _("العربية")),
            ("zh", _("中文")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, user=None, *args, **kwargs):
        super(TelegramSettingsForm, self).__init__(*args, **kwargs)

        if user:
            self.initial["telegram_chat_id"] = user.telegram_chat_id or ""
            self.initial["enable_telegram"] = bool(user.telegram_chat_id)
            self.initial["telegram_language"] = user.telegram_language or "fr"

    def clean(self):
        cleaned_data = super().clean()
        telegram_chat_id = cleaned_data.get("telegram_chat_id", "")
        enable_telegram = cleaned_data.get("enable_telegram", False)

        if enable_telegram and not telegram_chat_id:
            raise forms.ValidationError(
                _("Vous devez fournir un ID de chat Telegram pour activer les notifications.")
            )

        return cleaned_data
