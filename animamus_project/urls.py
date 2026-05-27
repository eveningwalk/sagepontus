"""
URL configuration for animamus_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from questionnaire import views
from .auth_views import email_token_auth

urlpatterns = [
    path('admin/', admin.site.urls),
    path('questionnaire/', include('questionnaire.urls')),
    path('accounts/', include('accounts.urls')),
    path('api/auth/token/', email_token_auth, name='api_token'),
    path('', include('vertical_pt.urls')),
    path('landing/', views.landing, name='landing'),
    path('demo/', views.demo_entry, name='demo'),
    path('', views.root, name='home'),
]