from django.urls import re_path
from django.contrib import admin
from django.urls import path, include
from safmeds import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/first', views.first_login, name='first_login'),
    re_path(r'/?$', views.splash, name='splash'),
    path('django-rq/', include('django_rq.urls')),
]

urlpatterns += [
    re_path(r'accounts/', include('django.contrib.auth.urls')),
    re_path(r'safmeds/', include('safmeds.urls')),
    re_path(r'realexams/', include('realexams.urls')),
    re_path(r'exams/', include('exams.urls')),
    re_path(r'thesis/', include('thesis_readiness.urls')),
]