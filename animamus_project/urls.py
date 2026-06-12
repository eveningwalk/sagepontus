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
from django.http import HttpResponse
from questionnaire import views
from .auth_views import email_token_auth

def sitemap_xml(request):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url><loc>https://pt.sagepontus.com/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n'
        '  <url><loc>https://pt.sagepontus.com/pt-alarm</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n'
        '</urlset>'
    )
    return HttpResponse(xml, content_type='application/xml')

def robots_txt(request):
    body = 'User-agent: *\nAllow: /\nSitemap: https://pt.sagepontus.com/sitemap.xml'
    return HttpResponse(body, content_type='text/plain')

urlpatterns = [
    path('sitemap.xml', sitemap_xml, name='sitemap'),
    path('robots.txt', robots_txt, name='robots'),
    path('admin/', admin.site.urls),
    path('questionnaire/', include('questionnaire.urls')),
    path('accounts/', include('accounts.urls')),
    path('api/auth/token/', email_token_auth, name='api_token'),
    path('', include('vertical_pt.urls')),
    path('landing/', views.landing, name='landing'),
    path('demo/', views.demo_entry, name='demo'),
    path('', views.root, name='home'),
]