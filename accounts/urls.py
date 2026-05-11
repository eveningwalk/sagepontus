from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('api/signup/', views.api_signup, name='api_signup'),
    path('api/check-email/', views.api_check_email, name='api_check_email'),
]