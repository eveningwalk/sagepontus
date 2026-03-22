from django.urls import path
from . import views
from .views import landing_page, signup, login, logout


app_name = "accounts"

urlpatterns = [
    #path('', views.landing_page, name='landing_page'),  # 루트 접근
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
]