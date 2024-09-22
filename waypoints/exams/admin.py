from django.contrib import admin
from exams.models import *
from django.contrib.auth import get_user_model

class QuestionAdmin(admin.ModelAdmin):
	list_display = ('text', 'test_string')
	search_fields = ['text']

	def test_string(self, inst):
		return_str = ""
		for objective in inst.objectives.all():
			if return_str != "":
				return_str += ", "
			return_str += objective.name
		return return_str

	def get_search_results(self, request, queryset, search_term):
		queryset, may_have_duplicates = super().get_search_results(
			request, queryset, search_term,
		)

		queryset |= self.model.objects.filter(objectives__name=search_term)
		return queryset, True

# Register your models here.
admin.site.register(ContentArea)
admin.site.register(Objective)
admin.site.register(Image)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Test)
admin.site.register(TestSection)
admin.site.register(TestInstance)
