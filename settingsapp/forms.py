from django import forms
from .models import SavingsProduct, ChargePolicy


class SavingsProductForm(forms.ModelForm):
    class Meta:
        model = SavingsProduct
        fields = ["name", "description", "minimum_monthly_contribution", "allow_withdrawals", "interest_rate_percent", "is_active"]


# forms.py example
class ChargePolicyForm(forms.ModelForm):
    class Meta:
        model = ChargePolicy
        fields = '__all__'
        widgets = {
            'charge_amount': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '0.00'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }