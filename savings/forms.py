from decimal import Decimal
from django import forms
from members.models import Member


class StaffDepositForm(forms.Form):
    member = forms.ModelChoiceField(queryset=Member.objects.all())
    amount = forms.DecimalField(min_value=Decimal("1.00"), max_digits=12, decimal_places=2)
    narration = forms.CharField(max_length=255, required=False)


class StaffWithdrawalForm(forms.Form):
    member = forms.ModelChoiceField(queryset=Member.objects.all())
    amount = forms.DecimalField(min_value=Decimal("1.00"), max_digits=12, decimal_places=2)
    narration = forms.CharField(max_length=255, required=False)


class MemberDepositForm(forms.Form):
    amount = forms.DecimalField(min_value=Decimal("1.00"), max_digits=12, decimal_places=2)
    narration = forms.CharField(max_length=255, required=False)


class MemberWithdrawalForm(forms.Form):
    amount = forms.DecimalField(min_value=Decimal("1.00"), max_digits=12, decimal_places=2)
    narration = forms.CharField(max_length=255, required=False)