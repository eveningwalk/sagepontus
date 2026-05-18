from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import PTProfile


class PTSignupForm(forms.Form):
    first_name     = forms.CharField(max_length=50, label="First Name")
    last_name      = forms.CharField(max_length=50, label="Last Name")
    email          = forms.EmailField(label="Email")
    password       = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    role           = forms.ChoiceField(choices=PTProfile.ROLE_CHOICES, label="Role")
    clinic_name    = forms.CharField(max_length=120, required=False, label="Clinic / Practice Name")
    license_number = forms.CharField(max_length=50, required=False, label="License Number (optional)")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cd = super().clean()
        pw  = cd.get("password", "")
        pw2 = cd.get("password_confirm", "")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "Passwords do not match.")
        if pw:
            try:
                validate_password(pw)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return cd

    def save(self) -> User:
        cd = self.cleaned_data
        username = cd["email"].lower().split("@")[0]
        # 중복 username 방지
        base = username
        n = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{n}"
            n += 1

        user = User.objects.create_user(
            username=username,
            email=cd["email"].lower(),
            password=cd["password"],
            first_name=cd["first_name"],
            last_name=cd["last_name"],
        )
        PTProfile.objects.create(
            user=user,
            role=cd["role"],
            clinic_name=cd.get("clinic_name", ""),
            license_number=cd.get("license_number", ""),
        )
        return user
