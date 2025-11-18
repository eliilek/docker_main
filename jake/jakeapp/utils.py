from jakeapp.models import *
from django.contrib.auth import get_user_model
import unicodecsv as csv
from django.core.files.storage import default_storage
from django.core.mail import send_mail
import datetime
from django.utils import timezone
from redis import Redis
from rq import Queue
from django_rq import get_queue
from rq_scheduler import Scheduler

def daily_check():
	two_weeks_ago = timezone.now() - timezone.timedelta(weeks=2)
	candidates = UserData.objects.filter(follow_up_email_sent=False)
	for candidate in candidates:
		unfinished_module_instances = ModuleInstance.objects.filter(user=candidate.user, completed__isnull=True)
		if unfinished_module_instances.count() != 0:
			continue
		last_completed_module_instance = ModuleInstance.objects.filter(user=candidate.user, completed__isnull=False).order_by("module__ordering_number").last()
		upcoming_modules = Module.objects.filter(ordering_number__gt=last_completed_module_instance.module.ordering_number)
		if upcoming_modules.count() != 0:
			continue
		last_module_assessment_instance_set = AssessmentInstanceSet.objects.filter(user=candidate.user, followed_module=last_completed_module_instance.model)
		if last_module_assessment_instance_set.count() == 1:
			last_assessment_instance_set = last_module_assessment_instance_set.first()
			if last_assessment_instance_set.completed() and last_assessment_instance_set.completed_time() < two_weeks_ago:
				sent_mails = send_mail(
					"Prosocial Research Follow-Up",
					"Thank you for your participation in my research on Prosocial. You are receiving this email as a reminder to log back in and complete the self-report measures one last time. Please answer them just as you did before. If you have any questions, please contact me at jab3477@ego.thechicagoschool.edu. Thank you.",
					"jab3477@ego.thechicagoschool.edu",
					[candidate.user.email,],
				)
				if sent_mails == 1:
					candidate.follow_up_email_sent = True
					candidate.save()

def start_daily_check():
	queue = get_queue('jake')
	scheduler = Scheduler(queue=queue, connection=queue.connection)

	scheduler.cron(
		"0 13 * * *",
		func=daily_check,
		use_local_timezone=True
	)

	sent_mails = send_mail(
		"Prosocial Research Follow-Up",
		"Thank you for your participation in my research on Prosocial. You are receiving this email as a reminder to log back in and complete the self-report measures one last time. Please answer them just as you did before. If you have any questions, please contact me at jab3477@ego.thechicagoschool.edu. Thank you.",
		"jab3477@ego.thechicagoschool.edu",
		["eliilek@gmail.com",],
	)

def write_assessment_set(assessment_instance_set, writer):
	for assessment_instance in assessment_instance_set.assessmentinstance_set.all():
		writer.writerow([assessment_instance.assessment.name, "Started:", (assessment_instance.started.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if assessment_instance.started else "None"), "Completed:", (assessment_instance.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if assessment_instance.completed else "None")])
		writer.writerow(["Question Text", "Given Response(s)"])
		for section in assessment_instance.assessment.assessment_sections.all():
			writer.writerow(["Section:", section.name])
			for assessment_question_response in AssessmentQuestionResponse.objects.filter(assessment_section=section, assessment_instance=assessment_instance):
				writer.writerow([assessment_question_response.assessment_question.text, assessment_question_response.given_response])
		writer.writerow([])
	for football_instance in assessment_instance_set.footballassessmentinstance_set.all():
		writer.writerow(["Social Discounting Assessment", "Ascending:", football_instance.ascending, "Started:", (football_instance.started.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if football_instance.started else "None"), "Completed:", (football_instance.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if football_instance.completed else "None")])
		writer.writerow(["Selfish Amount", "Selfish Choice Made"])
		for section in football_instance.footballassessmentsection_set.all():
			writer.writerow(["Name Info:", section.football_name.name, section.football_name.color, section.football_name.yards])
			writer.writerow(["Created:", section.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), (section.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if section.completed else "None")])
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
	initial_assessment_set = assessment_instance_sets.filter(followed_module=None).first()
	write_assessment_set(initial_assessment_set, writer)

	#Modules
	for module_instance in ModuleInstance.objects.filter(user=user).order_by("module__ordering_number"):
		writer.writerow(["Module:" + module_instance.module.name, "Started:", module_instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), "Completed:", (module_instance.completed.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if module_instance.completed else "Incomplete")])
		for section in module_instance.module.modulesection_set.all().order_by("ordering_number"):
			writer.writerow(["Section " + str(section.ordering_number)])
			for duration in SectionDuration.objects.filter(module_instance=module_instance, section=section):
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
	
	if assessment_instance_sets.filter(followed_module=None).count() > 1:
		write_assessment_set(assessment_instance_sets.filter(followed_module=None).last(), writer)

	#Rewatches
	writer.writerow([])
	writer.writerow(["Section Rewatch Log"])
	writer.writerow(["Section", "Duration", "Start Time"])
	for rewatch in ModuleSectionRewatch.objects.filter(user=user):
		writer.writerow([str(rewatch.module_section), str(rewatch.duration), rewatch.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")])
	new_file.close()	