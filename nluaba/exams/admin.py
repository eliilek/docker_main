from django.contrib import admin
from exams.models import *
from django.contrib.auth import get_user_model

class QuestionAdmin(admin.ModelAdmin):
	list_display = ('text', 'test_string')
	search_fields = ['text']

# Register your models here.
admin.site.register(ContentArea)
admin.site.register(Objective)
admin.site.register(Image)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Test)
admin.site.register(TestSection)
admin.site.register(TestInstance)
admin.site.register(Course)
admin.site.register(MaintenanceInstance)