from django.contrib import admin
from django.urls import path, include
from ica import views
import django_rq

app_name = 'ica'
urlpatterns = [
	path('', views.index, name='index'),
	path('begin', views.begin_assessment, name='begin_assessment'),
	path('submit', views.submit_response, name='submit_response'),
	path('view', views.view_data, name='view_data'),
	path('view/<int:instance_pk>', views.view_instance, name='view_instance'),
	path('delete/<int:instance_pk>', views.delete_instance, name='delete_instance'),
	path('score/update', views.score, name='score'),
	path('logout', views.logout, name="logout"),
	path('insitu/create', views.create_in_situ, name="create_in_situ"),
	path('insitu/create/report', views.create_in_situ_report, name="create_in_situ_report"),
	path('insitu/begin', views.begin_in_situ, name="begin_in_situ"),
	path('insitu/begin/<int:instance_pk>', views.begin_in_situ, name="begin_in_situ"),
	path('insitu/assessment', views.in_situ_assessment, name="in_situ_assessment"),
	path('insitu/assessment/<int:question_pk>', views.in_situ_assessment, name="in_situ_assessment"),
	path('insitu/assessment/submit', views.submit_in_situ_response, name="submit_in_situ_response"),
	path('insitu/assessment/submit/<int:question_pk>', views.submit_in_situ_response, name="submit_in_situ_response"),
	path('insitu/view', views.view_in_situ_data, name='view_in_situ_data'),
	path('insitu/mark/<int:instance_pk>', views.mark_in_situ_complete, name='mark_in_situ_complete'),
	path('insitu/begin/first/<int:instance_pk>', views.in_situ_first_time, name="in_situ_first_time"),
	]