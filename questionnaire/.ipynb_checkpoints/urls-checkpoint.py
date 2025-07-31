from django.urls import path
from . import views

'''
urlpatterns = [
    path('', views.index, name='index'),
    path('next/', views.next_question, name='next_question'),
    path('complete/', views.complete, name='complete'),
]
'''
app_name = "questionnaire"

# urls.py (수정)
urlpatterns = [
    path('', views.start_questionnaire, name='start'),  # 루트 URL을 시작으로 사용
    path('questionnaire/', views.questionnaire_view, name='questionnaire'),  # 질문 진행
    path('summary/', views.summary_view, name='summary'),                   # 요약
    path("final_prompt/", views.final_prompt_view, name="final_prompt"),    # 최종 결과
    
    #path('question/', views.questionnaire_view_v2, name='question_v2')
    path('question/', views.questionnaire_view_v2, name='question')

]
