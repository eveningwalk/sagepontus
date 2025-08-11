from django.urls import path
from . import views
#from .views import test_summary_view

app_name = "questionnaire"

urlpatterns = [
    path('', views.start, name='start'),  # 설문 시작
    path('<slug:category_slug>/questions/<int:step>/', views.question_flow, name='question_flow'),  # 질문 흐름
    #path('<slug:category_slug>/summary/', views.summary_view, name='summary'),  # 요약
    path("final_prompt/", views.final_prompt_view, name="final_prompt"),  # 최종 Prompt
    #path('summary/', views.summary_page, name='summary'),
    path('<slug:category_slug>/summary/', views.summary_page, name='summary'),


]
