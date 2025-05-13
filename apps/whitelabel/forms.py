from django import forms
from .models import WhiteLabel


class WhiteLabelForm(forms.ModelForm):
    class Meta:
        model = WhiteLabel
        fields = [
            "name",
            "domain",
            "logo",
            "primary_color",
            "secondary_color",
            "meta_title",
            "meta_description",
            "meta_keywords",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Site Name"}),
            "domain": forms.TextInput(attrs={"class": "form-control", "placeholder": "Domain"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
            "primary_color": forms.TextInput(attrs={"type": "color", "class": "form-control"}),
            "secondary_color": forms.TextInput(attrs={"type": "color", "class": "form-control"}),
            "meta_title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Meta Title"}
            ),
            "meta_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Meta Description",
                }
            ),
            "meta_keywords": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Meta Keywords"}
            ),
        }

    def clean_domain(self):
        domain = self.cleaned_data["domain"]
        return domain.replace("http://", "").replace("https://", "").rstrip("/")

    def clean_commission_rate(self):
        rate = self.cleaned_data.get("commission_rate")
        if rate is not None:
            if rate < 0 or rate > 100:
                raise forms.ValidationError("Commission rate must be between 0 and 100")
        return rate

    def clean_minimum_payout(self):
        amount = self.cleaned_data.get("minimum_payout")
        if amount is not None and amount < 0:
            raise forms.ValidationError("Minimum payout amount cannot be negative")
        return amount
