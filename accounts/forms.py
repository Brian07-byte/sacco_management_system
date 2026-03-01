from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from members.models import Member  # make sure app name is "members"

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    national_id = forms.CharField(
        required=True,
        max_length=20,
        label="National ID",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 12345678"})
    )

    class Meta:
        model = User
        fields = ("username", "email", "national_id", "password1", "password2")

    def clean_national_id(self):
        national_id = (self.cleaned_data.get("national_id") or "").strip()

        if Member.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError("This National ID is already registered. Please sign in or use another one.")

        return national_id