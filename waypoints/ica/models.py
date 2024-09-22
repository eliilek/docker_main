from django.db import models
from django.utils import timezone
from nluaba import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.models import CloudinaryField
import random

# Create your models here.
class Task(models.Model):
	name = models.CharField(max_length=200)

	def __str__(self):
		return self.name

class Image(models.Model):
	name = models.CharField(max_length=100)
	image = CloudinaryField('image')

	def __str__(self):
		return self.name

#Question is just a container, can have appropriate additions
#Question stores type/template to inform what additions to look for, a little fragile
#Question types are: multiple choice, short answer, multiple short answer (horiz or vert), random label, column,
	#drag & drop, 
class Question(models.Model):
	question_types = [
					("MC", "Multiple Choice"),
					("SA", "Short Answer"),
					("CSA", "Column Short Answer"),
					("DD", "Drag and Drop"),
					("IS", "In Situ"),
				]
	task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
	#This label is only used if there's an overheader, individual question labels are in addition
	#Use || if randomly selecting from multiple
	label = models.TextField(blank=True)
	#Use || if randomly selecting from multiple
	video_names = models.TextField(blank=True)
	horizontal = models.BooleanField(default=False)
	question_type = models.CharField(max_length=5, choices=question_types)
	name = models.CharField(max_length=100, default="", blank=True)

	def __str__(self):
		if self.name != "":
			return self.name
		if self.label != "":
			return self.label
		try:
			return str(self.task) + " - question " + str(self.link_to_assessment.first().question_number)
		except Exception as e:
			return "Broken"

	def get_label(self):
		if "||" in self.label:
			return random.choice(self.label.split("||"))
		return self.label

	def get_video_name(self):
		if "||" in self.video_names:
			return random.choice(self.video_names.split("||"))
		return self.video_names

class DragDropAddition(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	image_1 = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="image_1")
	image_2 = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="image_2")
	image_3 = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="image_3")
	image_4 = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="image_4")
	number_of_pairs = models.PositiveSmallIntegerField(default=6)

class ColumnShortAnswerAddition(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	column_1_label = models.CharField(max_length=50)
	column_2_label = models.CharField(max_length=50)
	row_count = models.PositiveSmallIntegerField()

#Question can have multiple
class ShortAnswerAddition(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	label = models.TextField()

#Question can have multiple
class MultipleChoiceAddition(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	label =  models.TextField()
	correct_answer = models.TextField()
	incorrect_answer_1 = models.TextField()
	incorrect_answer_2 = models.TextField()
	incorrect_answer_3 = models.TextField()

	def answer_string(self):
		return self.correct_answer + "||" + self.incorrect_answer_1 + "||" + self.incorrect_answer_2 + "||" + self.incorrect_answer_3

class InSituAddition(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	label = models.TextField()

class Assessment(models.Model):
	questions = models.ManyToManyField(Question, through="QuestionAssessmentOrdering")
	users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="ica_assessment")
	active = models.BooleanField(default=True)
	in_situ_assessment = models.BooleanField(default=False)

	def __str__(self):
		if self.in_situ_assessment:
			return "In-Situ Assessment"
		return "Technician Assessment"

	def get_questions(self):
		return self.questions.order_by('link_to_assessment')

class QuestionAssessmentOrdering(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='link_to_assessment')
	assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
	question_number = models.PositiveSmallIntegerField(default=1)

	class Meta:
		ordering = ('question_number',)

class AssessmentInstance(models.Model):
	assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='icainstance', null=True)
	created = models.DateTimeField(editable=False, auto_now_add=True)
	finished = models.DateTimeField(editable=False, null=True, blank=True, default=None)

	def duration(self):
		if not self.finished:
			return None
		total_duration = timezone.timedelta(days=0)
		for aqr in self.assessmentquestionresponse_set.all():
			try:
				total_duration += aqr.duration()
			except Exception as e:
				pass
		if total_duration:
			return str(total_duration.seconds//3600) + " hours " + str((total_duration.seconds//60)%60) + " min " + str(total_duration.seconds%60) + " sec"
		return None

class AssessmentQuestionResponse(models.Model):
	assessment_instance = models.ForeignKey(AssessmentInstance, on_delete=models.CASCADE)
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	#This label is only used if there's an overheader, individual question labels are in addition
	label = models.TextField()
	video_name = models.TextField()
	created = models.DateTimeField(editable=False, auto_now_add=True)
	points = models.DecimalField(max_digits=4, decimal_places=2, default=0)
	begun = models.DateTimeField(editable=False, null=True, blank=True, default=None)

	def duration(self):
		if not self.begun:
			return 0
		end_time = self.responseanswer_set.order_by("-answered_timestamp").first().answered_timestamp
		return end_time-self.begun

	def answered(self):
		for response_answer in self.responseanswer_set.all():
			if not response_answer.answered():
				return False
		return True

	def generate_response_answers(self):
		self.label = self.question.get_label()
		self.video_name = self.question.get_video_name()
		self.save()
		if self.question.question_type == "MC":
			for addition in self.question.multiplechoiceaddition_set.all():
				new_response_answer = ResponseAnswer(assessment_question_response=self, response_label=addition.label, multiple_choice_response_string=addition.answer_string())
				new_response_answer.save()
		elif self.question.question_type == "SA":
			for addition in self.question.shortansweraddition_set.all():
				new_response_answer = ResponseAnswer(assessment_question_response=self, response_label=addition.label)
				new_response_answer.save()
		elif self.question.question_type == "CSA":
			for addition in self.question.columnshortansweraddition_set.all():
				for i in range(addition.row_count):
					new_col_1_answer = ResponseAnswer(assessment_question_response=self, response_label="(row " + str(i+1) + ") || " + addition.column_1_label)
					new_col_1_answer.save()
					new_col_2_answer = ResponseAnswer(assessment_question_response=self, response_label="(row " + str(i+1) + ") || " + addition.column_2_label)
					new_col_2_answer.save()
		elif self.question.question_type == "DD":
			for addition in self.question.dragdropaddition_set.all():
				for i in range(addition.number_of_pairs):
					new_col_1_answer = ResponseAnswer(assessment_question_response=self, response_label="row " + str(i+1) + " left")
					new_col_1_answer.save()
					new_col_2_answer = ResponseAnswer(assessment_question_response=self, response_label="row " + str(i+1) + " right")
					new_col_2_answer.save()
		elif self.question.question_type == "IS":
			for addition in self.question.insituaddition_set.all():
				new_response_answer = ResponseAnswer(assessment_question_response=self, response_label=addition.label)
				new_response_answer.save()
			notes_response_answer = ResponseAnswer(assessment_question_response=self, response_label="Notes")
			notes_response_answer.save()
		else:
			raise RuntimeError("A question has no known question type, please fix.")

class InSituAssessmentQuestionResponse(AssessmentQuestionResponse):
	required = models.BooleanField(default=False)
	respondent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="insituaqr", null=True)

#AssessmentQuestionResponse can have multiple
class ResponseAnswer(models.Model):
	assessment_question_response = models.ForeignKey(AssessmentQuestionResponse, on_delete=models.CASCADE)
	#For questions with multiple answers, track which label it's associated with
	response_label = models.TextField()
	given_response = models.TextField()
	#Only used for MC questions, Correct then 3 incorrect separated by ||
	multiple_choice_response_string = models.TextField()
	created = models.DateTimeField(editable=False, auto_now_add=True)
	answered_timestamp = models.DateTimeField(editable=False, null=True)

	def answered(self):
		if not self.given_response and not self.response_label == "Notes":
			return False
		return True

class InSituAssessmentInstance(AssessmentInstance):
	user = None
	technician = models.TextField()
	users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='in_situ_assessment')
	confirmed_supervisors = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='in_situ_assessment_confirmed')

	def supervisor_names(self):
		return ", ".join([supervisor.name for supervisor in self.users.all()])

class File(models.Model):
	created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200)
