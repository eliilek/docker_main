from django.contrib import admin
from jakeapp.models import *
from django import forms

#class ResponseInline(admin.TabularInline):
#	model = Response
#	fields = ['text',]

#class QuestionAdmin(admin.ModelAdmin):
#	inlines = [ResponseInline,]

class AssessmentQuestionAdmin(admin.ModelAdmin):
	search_fields = ['text']

class AssessmentSectionAdmin(admin.ModelAdmin):
	search_fields = ['name', 'header']
	autocomplete_fields = ['assessment_questions']

class AssessmentAdmin(admin.ModelAdmin):
	autocomplete_fields = ['assessment_sections']

# Register your models here.
admin.site.register(Response)
admin.site.register(Question)
admin.site.register(ActivityPair)
admin.site.register(Activity)
admin.site.register(Quiz)
admin.site.register(Module)
admin.site.register(ModuleSection)
admin.site.register(AssessmentSection, AssessmentSectionAdmin)
admin.site.register(AssessmentQuestion, AssessmentQuestionAdmin)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(FootballAssessment)
admin.site.register(AssessmentSet)
