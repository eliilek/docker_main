from exams.models import *
from django.contrib.auth import get_user_model
import unicodecsv as csv
from django.core.files.storage import default_storage
from django.utils import timezone
import cloudinary

def create_csv(args):
	new_file = default_storage.open(args['filename'], 'wb')
	writer = csv.writer(new_file, dialect='excel', encoding='utf-8')
	test = Test.objects.get(pk=args['test_pk'])
	if "student_pk" in args:
		student = get_user_model().objects.get(pk=args['student_pk'])

		writer.writerow(['Test', 'Test Date', 'Test Finished', 'Objective 1', 'Objective 2', 'Question Text', 'Correct Answer', 'Given Answer', 'Correct T/F', 'Incorrect Answer 1', 'Incorrect Answer 2', 'Incorrect Answer 3'])
		instances = TestInstance.objects.filter(test=test, user=student)
		for instance in instances:
			for response in instance.testresponse_set.all():
				objective_1 = response.question.objectives.first().name
				if response.question.objectives.count() != 1:
					objective_2 = response.question.objectives.last().name
				else:
					objective_2 = ""
				line = [instance.test.name, instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), (instance.finished.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if instance.finished else "Unrecorded"), objective_1, objective_2, response.question.text, response.question.correct_answer, response.answer, response.correct(), response.question.incorrect_answer_1, response.question.incorrect_answer_2, response.question.incorrect_answer_3]
				if response.question.image:
					line[4] += "\n" + cloudinary.CloudinaryImage(response.question.image.image.public_id).build_url()
				if response.question.correct_answer_image:
					line[5] += "\n" + cloudinary.CloudinaryImage(response.question.correct_answer_image.image.public_id).build_url()
				if response.question.incorrect_answer_1_image:
					line[8] += "\n" + cloudinary.CloudinaryImage(response.question.incorrect_answer_1_image.image.public_id).build_url()
				if response.question.incorrect_answer_2_image:
					line[9] += "\n" + cloudinary.CloudinaryImage(response.question.incorrect_answer_2_image.image.public_id).build_url()
				if response.question.incorrect_answer_3_image:
					line[10] += "\n" + cloudinary.CloudinaryImage(response.question.incorrect_answer_3_image.image.public_id).build_url()
				writer.writerow(line)
	else:
		first_row = ["Student Name", "Date/Time Started", "Date/Time Completed"]
		rows = {}
		instances = TestInstance.objects.filter(test=test)
		full_questions = []
		for instance in instances:
			rows[instance.pk] = [instance.user.name, instance.created.astimezone(timezone.get_default_timezone()), (instance.finished.astimezone(timezone.get_default_timezone()) if instance.finished else "Unrecorded")]
		sections = test.testsection_set.all()
		for section in sections:
			if section.objective:
				questions = Question.objects.filter(objectives=section.objective)
				for question in questions:
					first_row.append(question.text)
					if question.image:
						first_row[-1] += "\n" + cloudinary.CloudinaryImage(question.image.image.public_id).build_url()
					first_row.append(section.objective.name)
					full_questions.append(question)
					for row in rows:
						rows[row].append("")
						rows[row].append("")
			elif section.content_area:
				objective_set = Objective.objects.filter(content_area=section.content_area)
				questions = Question.objects.filter(objectives__in=objective_set).distinct()
				for question in questions:
					first_row.append(question.text)
					if question.image:
						first_row[-1] += "\n" + cloudinary.CloudinaryImage(question.image.image.public_id).build_url()
					first_row.append(section.content_area.name)
					full_questions.append(question)
					for row in rows:
						rows[row].append("")
						rows[row].append("")
		for response in TestResponse.objects.filter(test_instance__test=test).distinct():
			rows[response.test_instance.pk][((full_questions.index(response.question) + 1) * 2) + 1] = response.answer
			rows[response.test_instance.pk][((full_questions.index(response.question) + 1) * 2) + 2] = ("Y" if response.correct() else "N")
		writer.writerow(first_row)
		for row in rows:
			writer.writerow(rows[row])

	new_file.close()

def sort_func(question):
	return question.text

def create_maintenance_csv(args):
	new_file = default_storage.open(args['filename'], 'wb')
	writer = csv.writer(new_file, dialect='excel', encoding='utf-8')

	if 'student_pk' in args:
		student = get_user_model().objects.get(pk=args['student_pk'])
		instances = MaintenanceInstance.objects.filter(user=student).order_by('created')
		for instance in instances:
			writer.writerow(["Student", "Started", "Finished", "Correct", "Total"])
			writer.writerow([student.name, instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), (instance.finished.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y") if instance.finished else "Unrecorded"), instance.score(), instance.total_questions()])
			writer.writerow(["Objective", "Question", "Correct", "Incorrect 1", "Incorrect 2", "Incorrect 3", "Correct"])
			for response in instance.maintenanceresponse_set.all():
				response_row = [response.question.objectives_string(), response.question.text, response.question.correct_answer, response.question.incorrect_answer_1, response.question.incorrect_answer_2, response.question.incorrect_answer_3, response.correct()]
				if response.question.image:
					response_row[1] += "\n" + cloudinary.CloudinaryImage(response.question.image.image.public_id).build_url()
				if response.question.correct_answer_image:
					response_row[2] += "\n" + cloudinary.CloudinaryImage(response.question.correct_answer_image.image.public_id).build_url()
				if response.question.incorrect_answer_1_image:
					response_row[3] += "\n" + cloudinary.CloudinaryImage(response.question.incorrect_answer_1_image.image.public_id).build_url()
				if response.question.incorrect_answer_2_image:
					response_row[4] += "\n" + cloudinary.CloudinaryImage(response.question.incorrect_answer_2_image.image.public_id).build_url()
				if response.question.incorrect_answer_3_image:
					response_row[5] += "\n" + cloudinary.CloudinaryImage(response.question.incorrect_answer_3_image.image.public_id).build_url()
				writer.writerow(response_row)
			writer.writerow([""])
	elif 'course_pks' in args:
		instances = None
		questions = []
		for course_pk in args['course_pks']:
			course = Course.objects.get(pk=course_pk)
			if instances:
				instances = instances | MaintenanceInstance.objects.filter(maintenance__courses=course, finished__isnull=False)
			else:
				instances = MaintenanceInstance.objects.filter(maintenance__courses=course, finished__isnull=False)
		for instance in instances:
			for response in instance.maintenanceresponse_set.all():
				if not response.question in questions:
					questions.append(response.question)
		questions.sort(key=sort_func)
		writer.writerow(["",""] + [question.objectives_string() + " - " + question.text for question in questions])
		for instance in instances:
			row = [instance.user.name, instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")]
			for question in questions:
				try:
					response = instance.maintenanceresponse_set.get(question=question)
					row.append(response.correct())
				except:
					row.append("")
			writer.writerow(row)

	new_file.close()