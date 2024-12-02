from django.contrib import admin
from ica.models import *
from django import forms

class QuestionAssessmentOrderingInline(admin.TabularInline):
	model = QuestionAssessmentOrdering
	fields = ['question_number', 'question']
	autocomplete_fields = ['question']

class AssessmentAdmin(admin.ModelAdmin):
	inlines = [QuestionAssessmentOrderingInline]
	autocomplete_fields = ['users']

class MultipleChoiceAdditionInline(admin.TabularInline):
	model = MultipleChoiceAddition
	formfield_overrides = {
		models.TextField: {'widget': forms.TextInput},
	}

class ShortAnswerAdditionInline(admin.TabularInline):
	model = ShortAnswerAddition
	formfield_overrides = {
		models.TextField: {'widget': forms.TextInput},
	}

class ColumnShortAnswerAdditionInline(admin.TabularInline):
	model = ColumnShortAnswerAddition

class DragDropAdditionInline(admin.TabularInline):
	model = DragDropAddition

class InSituAdditionInline(admin.TabularInline):
	model = InSituAddition

class QuestionAdmin(admin.ModelAdmin):
	inlines = [MultipleChoiceAdditionInline, 
				ShortAnswerAdditionInline, 
				ColumnShortAnswerAdditionInline, 
				DragDropAdditionInline,
				InSituAdditionInline]
	search_fields = ['name']
	#formfield_overrides = {
	#	models.TextField: {'widget': forms.TextInput},
	#}

class InSituAssessmentInstanceAdmin(admin.ModelAdmin):
	fields = ('technician','users')

# Register your models here.
admin.site.register(Task)
admin.site.register(Image)
admin.site.register(Question, QuestionAdmin)
admin.site.register(DragDropAddition)
admin.site.register(ColumnShortAnswerAddition)
admin.site.register(ShortAnswerAddition)
admin.site.register(MultipleChoiceAddition)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(InSituAssessmentInstance, InSituAssessmentInstanceAdmin)