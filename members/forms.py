from django import forms
from django.contrib.auth import get_user_model
from .models import Member

User = get_user_model()


# members/forms.py
class MemberCompleteProfileForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "phone_number", "national_id", "kra_pin", "date_of_birth", "gender",
            "address", "town", "county", "alternative_phone",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class MemberEditProfileForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "phone_number", "address", "town", "county", "alternative_phone",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
        ]


class StaffRegisterMemberForm(forms.Form):
    """Staff creates a User + Member profile."""
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=15, required=False)

    national_id = forms.CharField(max_length=20)
    kra_pin = forms.CharField(max_length=20, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(choices=Member.GENDER_CHOICES, required=False)

    address = forms.CharField(max_length=255, required=False)
    town = forms.CharField(max_length=120, required=False)
    county = forms.CharField(max_length=120, required=False)

    next_of_kin_name = forms.CharField(max_length=120, required=False)
    next_of_kin_phone = forms.CharField(max_length=15, required=False)
    next_of_kin_relationship = forms.CharField(max_length=60, required=False)

    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_national_id(self):
        nid = self.cleaned_data["national_id"]
        if Member.objects.filter(national_id=nid).exists():
            raise forms.ValidationError("A member with this National ID already exists.")
        return nid


class StaffEditMemberForm(forms.ModelForm):
    """Staff can edit member record + status."""
    class Meta:
        model = Member
        fields = [
            "national_id", "kra_pin", "date_of_birth", "gender",
            "address", "town", "county", "alternative_phone",
            "status", "is_active",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
        ]