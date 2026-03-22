from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from animamus_common.models import Response, ResponseSet

class ResponseCreateAPITest(APITestCase):
    def test_create_response(self):
        #url = reverse('response-create')
        url = reverse('questionnaire:response-create')  # 네임스페이스 포함
        data = {
            'question_id': 'goal_problem',
            'answer': '이것은 테스트 답변입니다.'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], '답변이 저장되었습니다.')

        # DB에 저장되었는지 확인
        session_key = self.client.session.session_key
        response_set = ResponseSet.objects.filter(session_key=session_key).first()
        self.assertIsNotNone(response_set)

        saved_response = Response.objects.filter(response_set=response_set, question_id='goal_problem').first()
        self.assertIsNotNone(saved_response)
        self.assertEqual(saved_response.answer, '이것은 테스트 답변입니다.')
