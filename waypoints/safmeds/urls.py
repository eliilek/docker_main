from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from safmeds import views
import django_rq

app_name = 'safmeds'
urlpatterns = [
	path('decks', views.decks, name='decks'),
	path('decks/<int:deck>', views.practice_selection, name='practice_selection'),
	path('decks/<int:deck>/full', views.practice_full, name='practice_full'),
	path('decks/<int:deck>/minute', views.practice_minute, name='practice_minute'),
	path('decks/<int:deck>/errors', views.practice_errors, name='practice_errors'),
	path('decks/<int:deck>/testout', views.practice_test_out, name='practice_test_out'),
	path('decks/<int:deck>/view', views.view_deck, name='view_deck'),
	path('decks/<int:deck>/progress', views.progress, name='progress'),
	path('results/<int:practice>', views.specific_result, name='specific_result'),
	path('report', views.report, name='report'),
	path('multiupload', views.multi_upload, name='multi_upload'),
	path('multiupload/report', views.multi_upload_report, name='multi_upload_report'),
	path('decks/<int:deck>/progress/<int:student>', views.super_progress, name='super_progress'),
	path('results/mark', views.mark, name='mark'),
	path('download', views.download_select, name='download_select'),
	path('download/<int:student>', views.download_type_select, name='download_type_select'),
	path('download/<int:student>/timings', views.download_timings, name='download_timings'),
	path('download/<int:deck>/decktimings', views.download_timings_deck, name='download_timings_deck'),
	path('download/<int:student>/responses', views.download_responses, name='download_responses'),
	path('download/<int:deck>/deckresponses', views.download_responses_deck, name='download_responses_deck'),
	path('reset', views.reset_select, name='reset_select'),
	path('reset/<int:student>', views.reset_password, name='reset_password'),
	path('', views.index, name='index'),
	path('decks/<int:deck>/set', views.view_set, name='view_set'),
	path('download/deck', views.download_deck_select, name='download_deck_select'),
	path('download/deck/<int:deck>', views.download_deck_type_select, name='download_deck_type_select'),
	path('queued', views.queued, name='queued'),
	path('retrieve/<str:filename>', views.retrieve, name='retrieve'),
	path('delete/<str:filename>', views.delete, name='delete'),
	path('delete/timing/<int:timing>', views.delete_timing, name='delete_timing'),
]
