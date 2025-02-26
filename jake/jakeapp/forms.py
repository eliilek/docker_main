from django import forms
from django.forms import formset_factory
from jakeapp.models import *
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *

#Plain Text First
#For normal assessments, we need a formset of forms with 1 label and N radio buttons
#Assume same number of response choices
from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ['email', 'password1', 'password2']

#Problem - if we're using forms database objects are created when they are saved
#Use javascript, capture duration on submit
def create_quiz_form(quiz_pk):
	try:
		quiz = Quiz.objects.get(pk=quiz_pk)
	except:
		return None
	fields = {}
	for question in quiz.questions.all():
		options = []
		for response in question.responses.all():
			options.append((response.pk, response.text))
		if question.correct_responses.count() > 1:
			fields['question_' + str(question.pk)] = forms.CharField(widget=forms.CheckboxSelectMultiple(choices=options), label=question.text)
		else:
			fields['question_' + str(question.pk)] = forms.CharField(widget=forms.RadioSelect(choices=options), label=question.text)
	return type('QuizForm', (forms.Form,), fields)

#Fieldsets is a dict of dicts of dicts
class CustomAssessmentForm(forms.Form):
	def __init__(self, *args, **kwargs):
		#fieldsets = kwargs.pop('fieldsets', {})
		#extra_fields = kwargs.pop('extra_fields', {})
		super().__init__(*args, **kwargs)
		for name, field in self.extra_fields.items():
			self.fields[name] = field
		self.helper = FormHelper()
		self.helper.form_tag = False
		dynamic_layout = Layout()
		for legend, field_list in self.fieldsets.items():
			#Should be {'legend':['field1', 'field2', 'field3', 'response_labels']
			response_labels = [HTML("<span class='w-auto flex-fill'>" + label + "</span>") for label in field_list.pop()]
			row_list = []
			for field in field_list:
				row_list.append(InlineCheckboxes(field, template="jakeapp/custom_inline_radio_layout.html"))
			#dynamic_fieldset = Fieldset(legend, *row_list)
			dynamic_object = Div(
				HTML("<p>" + legend + "</p>"),
				Row(HTML("<span style='width:auto;'>In the last two weeks...</span>"), Row(*response_labels, style="width:50%;", css_class="justify-content-evenly"
					),
					css_class="justify-content-between mb-3"
				),
				css_class="d-flex flex-column mb-5")
			dynamic_object.extend(row_list)
			dynamic_layout.append(dynamic_object)
		self.helper.layout = dynamic_layout
		self.helper.render_unmentioned_fields = True

#Non-Football assessments
def create_assessment_form(assessment_instance):
	try:
		assessment = assessment_instance.assessment
	except:
		return None
	extra_fields = {}
	fieldsets = {}
	for section in assessment.assessment_sections.all():
		#Create a fieldset
		fieldsets[section.header] = []
		response_labels = []
		responses_labeled = False
		for assessment_question_response in AssessmentQuestionResponse.objects.filter(assessment_section=section, assessment_instance=assessment_instance):
			question = assessment_question_response.assessment_question
			options = []
			for response in question.responses.all():
				if not responses_labeled:
					response_labels.append(response.text)
				options.append((response.pk, ""))
			responses_labeled = True
			extra_fields['question_response_' + str(assessment_question_response.pk)] = forms.CharField(widget=forms.RadioSelect(choices=options), label=question.text)
			fieldsets[section.header].append('question_response_' + str(assessment_question_response.pk))
		fieldsets[section.header].append(response_labels)
	return type('AssessmentForm', (CustomAssessmentForm,), {'extra_fields':extra_fields, 'fieldsets':fieldsets})
	#return CustomAssessmentForm(fieldsets=fieldsets, extra_fields=fields)
	#return type('AssessmentForm', (forms.Form,), fields)