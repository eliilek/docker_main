from django.db import models
from django.utils import timezone
from nluaba import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.models import CloudinaryField
import random
from collections import Counter

class Objective(models.Model):
	name = models.CharField(max_length=150) 

	def __str__(self):
		return self.name

class TreatmentDesign(models.Model):
	name = models.CharField(max_length=150)

	def __str__(self):
		return self.name

class TreatmentDesignQuantity(models.Model):
	treatment_design = models.ForeignKey(TreatmentDesign, on_delete=models.CASCADE)
	quantity = models.PositiveSmallIntegerField()

class Image(models.Model):
	name = models.CharField(max_length=100)
	image = CloudinaryField('image')

	def __str__(self):
		return self.name

class Answer(models.Model):
	text = models.TextField()
	image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True)

class Question(models.Model):
	objectives = models.ManyToManyField(Objective, blank=True)
	text = models.TextField()
	image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True)
	correct_answers = models.ManyToManyField(Answer, related_name="correct_answer", blank=True)
	incorrect_answers = models.ManyToManyField(Answer, related_name="incorrect_answer", blank=True)
	points = models.DecimalField(max_digits=4, decimal_places=2, default=1)
	active = models.BooleanField(default=True)
	key = models.TextField(blank=True)
	select_all = models.BooleanField(default=False)

	def correct_string(self):
		correct_answer_string = ""
		for answer in self.correct_answers.all():
			if correct_answer_string != "":
				correct_answer_string += ","
			correct_answer_string += answer.text
		return correct_answer_string

	def incorrect_string(self):
		incorrect_answer_string = ""
		for answer in self.incorrect_answers.all():
			if incorrect_answer_string != "":
				incorrect_answer_string += ","
			incorrect_answer_string += answer.text
			if answer.image:
				incorrect_answer_string += " <a href='" + cloudinary.CloudinaryImage(answer.image.image.public_id).build_url() + "'>Image</a>"
		return incorrect_answer_string

	def question_type(self):
		if self.correct_answers.count() == 0 and self.incorrect_answers.count() == 0:
			return "Short Answer"
		elif self.select_all:
			return "Checkbox"
		else:
			return "Radio"

	def assessment_string(self):
		assessment_str = ""
		for assessment in self.assessment_set.all():
			if assessment_str != "":
				assessment_str += ", "
			assessment_str += assessment.name
		return assessment_str

class GraphManager(models.Manager):
	def random(self, n=1, treatment_design=None, section_1=True, exclude=None):
		if treatment_design:
			my_filter = self.filter(treatment_design=treatment_design, section_1=section_1)
		else:
			my_filter = self.all()
		if exclude:
			my_filter = my_filter.exclude(id__in=exclude)
		count = my_filter.count()
		random_indices = random.sample(range(0, count), n)
		graphs = [my_filter[index] for index in random_indices]
		return graphs

class Graph(models.Model):
	objects = GraphManager()
	name = models.CharField(max_length=150, unique=True)
	image = CloudinaryField('image')
	treatment_design = models.ManyToManyField(TreatmentDesign)
	questions = models.ManyToManyField(Question, blank=True)
	section_1 = models.BooleanField(verbose_name="Section 1 Graph")

	def __str__(self):
		return self.name

class Assessment(models.Model):
	name = models.CharField(max_length=100)
	active = models.BooleanField(default=True)
	instructions = models.TextField(blank=True)
	part_instructions = models.TextField(blank=True)
	students = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
	questions = models.ManyToManyField(Question, blank=True)
	section_1_treatment_designs = models.ManyToManyField(TreatmentDesignQuantity, related_name='assessment_qty_1', blank=True)
	section_2_treatment_designs = models.ManyToManyField(TreatmentDesignQuantity, related_name='assessment_qty_2', blank=True)
	part_1 = models.BooleanField(default=True)

	def __str__(self):
		return self.name

	def total_questions(self):
		return self.questions.count()

	def total_score(self):
		total = 0
		for question in self.questions.all():
			total += question.points
		return total

class AssessmentInstance(models.Model):
	assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assessmentinstance')
	created = models.DateTimeField(editable=False, auto_now_add=True)
	finished = models.DateTimeField(editable=False, null=True, blank=True, default=None)

	def score(self):
		score = 0
		for response in self.assessmentresponse_set.all():
			score += response.earned_points
		return score

	def total_score(self):
		total = 0
		for response in self.assessmentresponse_set.all():
			total += response.question.points
		return total

	def complete(self):
		if self.finished:
			return True
		return False

	def total_questions(self):
		return self.assessmentresponse_set.all().count()

	def __str__(self):
		return self.user.name + " - " + self.assessment.name

class AssessmentResponse(models.Model):
	assessment_instance = models.ForeignKey(AssessmentInstance, on_delete=models.CASCADE)
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	answer = models.TextField(blank=True)
	manual_correct = models.BooleanField(default=False)
	earned_points = models.DecimalField(max_digits=4, decimal_places=2, default=1)
	graph = models.ForeignKey(Graph, on_delete=models.SET_NULL, null=True, blank=True)

	def correct(self):
		if self.manual_correct:
			return True
		elif self.question.correct_answers.count() == 0:
			return self.earned_points == self.question.points
		elif self.question.correct_answers.count() == 1:
			return self.answer == self.question.correct_answers.all()[0].text
		else:
			correct_answer_string = ""
			for answer in self.question.correct_answers.all():
				if correct_answer_string != "":
					correct_answer_string += ","
				correct_answer_string += answer.text
			return Counter(self.answer.split(",")) == Counter(correct_answer_string.split(","))

class File(models.Model):
	created = models.DateTimeField(auto_now_add=True)
	name = models.CharField(max_length=200)