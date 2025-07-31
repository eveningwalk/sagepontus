from django import forms

class QuestionForm(forms.Form):
    answer = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)