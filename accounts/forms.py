from django import forms
from .models import EarlyAccessSignup


class EarlyAccessSignupForm(forms.Form):
    INDUSTRY_CHOICES = [('', '업종을 선택해주세요')] + EarlyAccessSignup.INDUSTRY_CHOICES

    email = forms.EmailField(
        label='이메일',
        widget=forms.EmailInput(attrs={'placeholder': 'your@email.com', 'autocomplete': 'email'}),
    )
    industry = forms.ChoiceField(
        label='업종',
        choices=INDUSTRY_CHOICES,
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if EarlyAccessSignup.objects.filter(email=email).exists():
            raise forms.ValidationError('이미 등록된 이메일입니다.')
        return email

    def clean_industry(self):
        industry = self.cleaned_data['industry']
        if not industry:
            raise forms.ValidationError('업종을 선택해주세요.')
        return industry

    def save(self):
        return EarlyAccessSignup.objects.create(
            email=self.cleaned_data['email'],
            industry=self.cleaned_data['industry'],
        )
