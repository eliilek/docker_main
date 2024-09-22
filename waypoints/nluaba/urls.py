"""safmeds URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
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

from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from safmeds import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/first', views.first_login, name='first_login'),
    path('', views.splash, name='splash'),
    path('django-rq/', include('django_rq.urls')),
]

urlpatterns += [
    url(r'accounts/', include('django.contrib.auth.urls')),
    url(r'safmeds/', include('safmeds.urls')),
    url(r'realexams/', include('realexams.urls')),
    url(r'exams/', include('exams.urls')),
    url(r'thesis/', include('thesis_readiness.urls')),
    url(r'ica/', include('ica.urls')),
]
