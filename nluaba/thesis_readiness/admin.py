from django.contrib import admin
from thesis_readiness.models import *
from django.contrib.auth import get_user_model

class QuestionAdmin(admin.ModelAdmin):
	list_display = ('text', 'assessment_string')
	search_fields = ['text', 'objectives__name', 'image__name']

# Register your models here.
admin.site.register(Objective)
admin.site.register(Image)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Assessment)
admin.site.register(AssessmentInstance)
admin.site.register(Graph)
admin.site.register(TreatmentDesign)
admin.site.register(TreatmentDesignQuantity)