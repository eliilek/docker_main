from django.contrib import admin
from realexams.models import *
from django.contrib.auth import get_user_model

class TestQuestionOrderingInline(admin.TabularInline):
    model = TestQuestionOrdering
    fields = ['ordering', 'question']

class QuestionAdmin(admin.ModelAdmin):
	def test_string(self, obj):
		test_str = ""
		for test in obj.test_set.all():
			if test_str != "":
				test_str += ", "
			test_str += test.name
		for ordering in obj.testquestionordering_set.all():
			if test_str != "":
				test_str += ", "
			test_str += ordering.test.name
		return test_str

	test_string.admin_order_field = 'test__name'

	list_display = ('text', 'test_string')
	search_fields = ['text', 'test__name', 'testquestionordering__test__name']

class TestAdmin(admin.ModelAdmin):
	exclude= ('questions',)
	#inlines = [
	#	TestQuestionOrderingInline
	#]

# Register your models here.
admin.site.register(ContentArea)
admin.site.register(Objective)
admin.site.register(Image)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(TestInstance)
