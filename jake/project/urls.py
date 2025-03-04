"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.urls import path, re_path, include
from jakeapp import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('django-rq/', include('django_rq.urls')),
    re_path(r'accounts/', include('django.contrib.auth.urls')),
    path('', views.initial, name="initial"),
    path('consent', views.consent, name="consent"),
    path('quiz/<int:quiz_pk>', views.quiz, name="quiz"),
    path('resume/<int:instance_pk>', views.resume, name="resume"),
    path('begin/<int:module_pk>', views.begin, name="begin"),
    path('review/<int:module_pk>', views.review, name="review"),
    path('beacon', views.beacon, name="beacon"),
    path('rewatch/<int:module_section_pk>', views.rewatch_section, name="rewatch_section"),
    path('assessment/<int:assessment_instance_pk>', views.assessment, name="assessment"),
    path('football/<int:assessment_instance_pk>', views.football_assessment, name="football_assessment"),
    path('football/name/<int:assessment_instance_pk>', views.football_name, name="football_name"),
    path('football/response/<int:response_pk>', views.football_response, name="football_response"),
    path('signup/', views.signup, name="signup"),
    path('activity/<int:activity_pk>', views.activity, name="activity"),
    path('activity/<int:activity_pk>/submit', views.activity_submit, name="activity_submit"),
    path('queued', views.queued, name='queued'),
    path('retrieve/<str:filename>', views.retrieve, name='retrieve'),
    path('delete/<str:filename>', views.delete, name='delete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)