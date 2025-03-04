from jakeapp.models import *
from django.contrib.auth import get_user_model
import unicodecsv as csv
from django.core.files.storage import default_storage
import datetime
from django.utils import timezone

def write_assessment_set(assessment_instance_set, writer):
	for assessment_instance in assessment_instance_set.assessmentinstance_set.all():
		writer.writerow([assessment_instance.assessment.name, "Started:", assessment_instance.started.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), "Completed:", assessment_instance.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")])
		writer.writerow(["Question Text", "Given Response(s)"])
		for section in assessment_instance.assessment.assessment_sections.all():
			writer.writerow(["Section:", section.name])
			for assessment_question_response in AssessmentQuestionResponse.objects.filter(assessment_section=section, assessment_instance=assessment_instance):
				writer.writerow([assessment_question_response.assessment_question.text, assessment_question_response.given_response])
		writer.writerow([])
	for football_instance in assessment_instance_set.footballassessmentinstance_set.all():
		writer.writerow(["Social Discounting Assessment", "Ascending:", football_instance.ascending, "Started:", assessment_instance.started.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), "Completed:", assessment_instance.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")])
		writer.writerow(["Selfish Amount", "Selfish Choice Made"])
		for section in football_instance.footballassessmentsection_set.all():
			writer.writerow(["Name Info:", section.football_name.name, section.football_name.color, section.football_name.yards])
			for response in section.footballresponse_set.all():
				writer.writerow([response.selfish_amount, response.selfish_choice])
		writer.writerow([])

def create_csv(args):
	new_file = default_storage.open(args['filename'], 'wb')
	writer = csv.writer(new_file, dialect='excel')

	#User Info
	user = get_user_model().objects.get(pk=args['user_pk'])
	writer.writerow(['User Email', user.email])
	writer.writerow([])

	assessment_instance_sets = AssessmentInstanceSet.objects.filter(user=user)

	#Initial Assessments
	initial_assessment_set = assessment_instance_sets.get(followed_module=None)
	write_assessment_set(initial_assessment_set, writer)

	#Modules
	for module_instance in ModuleInstance.objects.filter(user=user).order_by("module__ordering_number"):
		writer.writerow(["Module:" + module_instance.module.name, "Started:", module_instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), "Completed:", module_instance.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")])
		for section in module_instance.module.modulesection_set.all().order_by("ordering_number"):
			writer.writerow(["Section " + str(section.ordering_number)])
			for duration in SectionDuration.objects.filter(module_instance=module_instance, module_section=section):
				writer.writerow(["Watch Duration", str(duration.duration), "Created", (duration.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if duration.created else None)])
			if section.quiz:
				if section.quiz.activity:
					for activity_instance in ActivityInstance.objects.filter(user=user, activity=section.quiz.activity):
						writer.writerow(["Activity", activity_instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), "Duration", str(activity_instance.duration)])
				else:
					for quiz_instance in QuizInstance.objects.filter(user=user, quiz=section.quiz):
						writer.writerow(["Quiz", quiz_instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), "Duration", str(quiz_instance.duration)])
						writer.writerow(["Question Text", "Given Response(s)", "Correct"])
						for response in quiz_instance.questionresponse_set.all():
							writer.writerow([response.question.text, response.string_responses(), response.correct()])
		#Post-module Assessments
		writer.writerow([])
		assessment_sets = assessment_instance_sets.filter(followed_module=module_instance.module)
		for assessment_set in assessment_sets:
			write_assessment_set(assessment_set, writer)

	#Rewatches
	writer.writerow([])
	writer.writerow(["Section Rewatch Log"])
	writer.writerow(["Section", "Duration", "Start Time"])
	for rewatch in ModuleSectionRewatch.objects.filter(user=user):
		writer.writerow([str(rewatch.module_section), str(rewatch.duration), rewatch.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")])
	new_file.close()	