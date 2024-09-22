from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from exams import views

app_name = 'exams'
urlpatterns = [
	path('', views.index, name='index'),
	path('multiupload', views.multi_upload, name='multi_upload'),
	path('test/<int:test>/data', views.view_test_data, name='view_test_data'),
	path('student/<int:student>/data', views.view_student_data, name='view_student_data'),
	path('test/<int:test>', views.test_action, name='test_action'),
	path('test/<int:test>/take', views.take_test, name='take_test'),
	path('test/<int:test>/take/<int:question>', views.take_test, name='take_test'),
	path('test/<int:test>/submit', views.submit_response, name='submit_response'),
	path('test/<int:test>/timeout', views.test_timeout, name='test_timeout'),
	path('instance/<int:instance>', views.view_instance_data, name='view_instance_data'),
	path('maintenance/view', views.view_maintenance_data, name='view_maintenance_data'),
	path('maintenance/student/select', views.select_maintenance_student, name='select_maintenance_student'),
	path('maintenance/view/student/<int:student_pk>', views.view_maintenance_data, name='view_maintenance_data'),
	path('maintenance/view/<int:instance>', views.view_maintenance_instance_data, name='view_maintenance_instance_data'),
	path('multiupload/report', views.multi_upload_report, name='multi_upload_report'),
	path('download', views.download, name='download'),
	path('download/<int:test>', views.download_test, name='download_test'),
	path('download/student', views.download_student_select, name='download_student_select'),
	path('download/student/<int:student>', views.download_student, name='download_student'),
	path('download/student/<int:student>/<int:test>', views.download_student_test, name='download_student_test'),
	path('download/maintenance/student', views.download_maintenance_student_select, name='download_maintenance_student_select'),
	path('download/maintenance/student/<int:student>', views.download_maintenance_student, name='download_maintenance_student'),
	path('download/maintenance/course', views.download_maintenance_course_select, name='download_maintenance_course_select'),
	path('download/maintenance/course/download', views.download_maintenance_course, name='download_maintenance_course'),
	path('instance/<int:instance>/delete/<slug:return_address>', views.delete_test_instance, name='delete_test_instance'),
	path('maintenance/<int:instance>/delete', views.delete_maintenance_instance, name='delete_maintenance_instance'),
	path('queued', views.queued, name='queued'),
	path('retrieve/<str:filename>', views.retrieve, name='retrieve'),
	path('delete/<str:filename>', views.delete, name='delete'),
	path('maintenance', views.maintenance_probe_select, name='maintenance_probe_select'),
	path('maintenance/courses', views.maintenance_probe, name='maintenance_probe'),
	path('maintenance/submit', views.maintenance_create, name='maintenance_create'),
	path('maintenance/take/<int:instance_pk>', views.maintenance_take, name='maintenance_take'),
	path('maintenance/take/<int:instance_pk>/<int:question_index>', views.maintenance_take, name='maintenance_take'),
	path('maintenance/submit/<int:instance_pk>', views.submit_maintenance_response, name='submit_maintenance_response'),
]
