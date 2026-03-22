from rest_framework import serializers
from .models import Category, Question
from animamus_common.models import Response, ResponseSet


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class QuestionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Question
        fields = ['question_id', 'order', 'text', 'guidance', 'hint', 'category']

class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ['question_id', 'answer']

    def create(self, validated_data):
        request = self.context.get('request')
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        response_set, _ = ResponseSet.objects.get_or_create(session_key=session_key)
        response = Response.objects.create(response_set=response_set, **validated_data)
        return response

from rest_framework import serializers
from .models import Step, Question, Answer

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, source='answer_set')

    class Meta:
        model = Question
        fields = ['id', 'text', 'answers']