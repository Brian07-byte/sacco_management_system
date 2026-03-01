from decimal import Decimal
from django import forms
from .models import LoanApplication, LoanProduct, LoanRepayment, Loan


class MemberLoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        fields = ["product", "requested_amount", "term_months", "purpose", "notes"]
        widgets = {
            "requested_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "term_months": forms.NumberInput(attrs={"min": 1}),
            "purpose": forms.TextInput(attrs={"placeholder": "e.g. School fees, Business, Emergency"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = LoanProduct.objects.filter(is_active=True).order_by("name")


class RepaymentRequestForm(forms.ModelForm):
    class Meta:
        model = LoanRepayment
        fields = ["amount", "narration"]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
            "narration": forms.TextInput(attrs={"placeholder": "MPESA Ref / Bank Slip / Notes"}),
        }


class StaffRepaymentForm(forms.ModelForm):
    loan = forms.ModelChoiceField(queryset=Loan.objects.filter(status="ACTIVE").order_by("-created_at"))

    class Meta:
        model = LoanRepayment
        fields = ["loan", "amount", "narration"]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
            "narration": forms.TextInput(attrs={"placeholder": "MPESA Ref / Receipt / Notes"}),
        }


class DisbursementForm(forms.Form):
    disbursement_reference = forms.CharField(max_length=100, required=True)