from thesis_readiness.models import *
from django.contrib.auth import get_user_model
import unicodecsv as csv
from django.core.files.storage import default_storage
import datetime
from django.utils import timezone
import cloudinary

def create_csv(args):
	new_file = default_storage.open(args['filename'], 'wb')
	writer = csv.writer(new_file, dialect='excel')
	assessment = Assessment.objects.get(pk=args['assessment_pk'])
	if assessment.part_1:
		if 'student_pk' in args:
			instances = AssessmentInstance.objects.filter(user__pk=args['student_pk'], assessment=assessment)
		else:
			instances = AssessmentInstance.objects.filter(assessment=assessment)
		writer.writerow(['Test Name', 'Student Name', 'Date Started', 'Date Submitted', 'Objective', 'Question', 'Given Answer', 'Points Earned', 'Points Possible'])
		for instance in instances:
			for response in instance.assessmentresponse_set.all():
				if response.question.objectives.count() == 0:
					objective = 'None'
				else:
					objective = response.question.objectives.first().name
				line = [instance.assessment.name, instance.user.name, instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), (instance.finished.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if instance.finished else "Unrecorded"), objective, response.question.text, response.answer, response.earned_points, response.question.points]
				writer.writerow(line)
	else:
		writer.writerow(['Test Name', 'Student Name', 'Date Started', 'Date Submitted', 'Objective 1', 'Objective 2', 'Objective 3', 'Objective 4', 'Question', 'Given Answer', 'Correct Answer', 'Points Earned', 'Points Possible'])
		if 'student_pk' in args:
			instances = AssessmentInstance.objects.filter(user__pk=args['student_pk'], assessment=assessment)
		else:
			instances = AssessmentInstance.objects.filter(assessment=assessment)
		for instance in instances:
			for response in instance.assessmentresponse_set.all():
				line = [instance.assessment.name, instance.user.name, instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), (instance.finished.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if instance.finished else "Unrecorded")]
				if response.question.objectives.count() > 4:
					objectives = response.question.objectives.all()[:4]
				else:
					objectives = response.question.objectives.all()
				for objective in objectives:
					line.append(objective.name)
				line.append(response.question.text)
				line.append(response.answer)
				line.append(response.question.correct_string())
				line.append(response.earned_points)
				line.append(response.question.points)
				writer.writerow(line)

	new_file.close()