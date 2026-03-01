from django import forms
from .models import ChargePolicy


class ChargePolicyForm(forms.ModelForm):
    class Meta:
        model = ChargePolicy
        fields = [
            "withdrawal_fee_flat",
            "withdrawal_fee_percent",
            "membership_fee",
            "loan_processing_fee_percent",
            "is_active",
        ]
        widgets = {
            "withdrawal_fee_flat": forms.NumberInput(attrs={"step": "0.01"}),
            "withdrawal_fee_percent": forms.NumberInput(attrs={"step": "0.01"}),
            "membership_fee": forms.NumberInput(attrs={"step": "0.01"}),
            "loan_processing_fee_percent": forms.NumberInput(attrs={"step": "0.01"}),
        }