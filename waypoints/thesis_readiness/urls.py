from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from thesis_readiness import views

app_name = 'thesis_readiness'
urlpatterns = [
	path('', views.index, name='index'),
	path('multiupload', views.multi_upload, name='multi_upload'),
	path('multiupload/p2', views.multi_upload_2, name='multi_upload_2'),
	path('multiupload/report', views.multi_upload_report, name='multi_upload_report'),
	path('multiupload/report/p2', views.multi_upload_report_part_2, name='multi_upload_report_part_2'),
	path('download', views.download, name='download'),
	path('download/student', views.download_student_select, name='download_student_select'),
	path('assessment/<int:assessment>/data', views.view_assessment_data, name='view_assessment_data'),
	path('student/<int:student>/data', views.view_student_data, name='view_student_data'),
	path('assessment/<int:assessment>/take', views.take_assessment, name='take_assessment'),
	path('assessment/<int:assessment>/take/<int:question>', views.take_assessment, name='take_assessment'),
	path('test/<int:assessment>/submit', views.submit_response, name='submit_response'),
	path('download/<int:assessment>', views.download_assessment, name='download_assessment'),
	path('assessment/<int:assessment>/take/instructions', views.instructions, name='instructions'),
	path('assessment/<int:assessment>/take/partinstructions', views.part_instructions, name='part_instructions'),
	path('instance/<int:instance>', views.view_instance_data, name='view_instance_data'),
	path('score', views.score, name='score'),
	path('key', views.key, name='key'),
	path('instance/<int:instance>/delete/<slug:return_address>', views.delete_assessment_instance, name='delete_assessment_instance'),	path('queued', views.queued, name='queued'),
	path('retrieve/<str:filename>', views.retrieve, name='retrieve'),
	path('delete/<str:filename>', views.delete, name='delete'),
]
