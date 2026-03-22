from django import forms

class QuestionForm(forms.Form):
    answer = forms.CharField(label='답변', required=True)


from .models import Answer
class AnswerForm(forms.Form):
    answer = forms.ModelChoiceField(
        queryset=Answer.objects.none(),  # Question에 맞춰 동적 설정
        widget=forms.RadioSelect,        # 라디오 버튼으로 선택
        empty_label=None,                # 반드시 선택하도록
        label=''
    )

    def __init__(self, question=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if question:
            self.fields['answer'].queryset = question.answer_set.all()

from questionnaire.models.models_braintree import BrainNode

class NodeForm(forms.ModelForm):
    class Meta:
        model = BrainNode
        #fields = ["name", "order"]
        #fields = ["title", "order"]
        fields = ["order"]
        widgets = {
            #"name": forms.TextInput(attrs={"class": "form-control"}),
            #"title": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }
from questionnaire.models.models_braintree import BrainTree
class BrainTreeForm(forms.ModelForm):
    class Meta:
        model = BrainTree
        fields = ["title"]
        labels = {
            "title": "BrainTree 이름",
        }