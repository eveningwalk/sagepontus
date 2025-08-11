from django import forms

'''
class QuestionForm(forms.Form):
    answer = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

class QuestionForm(forms.Form):
    answer = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 150,# 6,  # 세로 높이
            'cols': 80, # 가로 폭
            'placeholder': '답변을 입력하세요...'
        })
    )
'''
from django import forms

class QuestionForm(forms.Form):
    answer = forms.CharField(label='답변', required=True)
