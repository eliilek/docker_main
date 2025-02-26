from django.db import models
from project import settings
import random
from django.utils import timezone

#def random_color():
#	r = lambda: random.randint(0,255)
#	return '#%02X%02X%02X' % (r(),r(),r())

# Create your models here.

class Response(models.Model):
	text = models.TextField()

	def __str__(self):
		return self.text

class Question(models.Model):
	text = models.TextField()
	responses = models.ManyToManyField(Response)
	correct_responses = models.ManyToManyField(Response, related_name="correct_questions")

	def __str__(self):
		if len(self.text) <= 40:
			return self.text
		return "("+str(self.pk)+") "+self.text[:40]

class ActivityPair(models.Model):
	left_text = models.CharField(max_length=100)
	right_text = models.CharField(max_length=100)

class Activity(models.Model):
	left_column_header = models.CharField(max_length=100)
	right_column_header = models.CharField(max_length=100)
	activity_pairs = models.ManyToManyField(ActivityPair)

	class Meta:
		verbose_name_plural = "Activities"

class ActivityInstance(models.Model):
	activity = models.ForeignKey(Activity, on_delete=models.CASCADE, blank=True, null=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	duration = models.DurationField(null=True)

class Quiz(models.Model):
	questions = models.ManyToManyField(Question, blank=True)
	activity = models.ForeignKey(Activity, on_delete=models.SET_NULL, null=True, default=None, blank=True)
	passing_threshold = models.PositiveSmallIntegerField(default=80)

class QuizInstance(models.Model):
	quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	duration = models.DurationField()

	def passed(self):
		correct = 0
		total = 0
		for question_response in self.questionresponse_set.all():
			total += 1
			if question_response.correct():
				correct += 1
		if correct / total >= self.quiz.passing_threshold / 100:
			return True
		return False

class QuestionResponse(models.Model):
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	quiz_instance = models.ForeignKey(QuizInstance, on_delete=models.CASCADE)
	given_responses = models.ManyToManyField(Response)

	def correct(self):
		if self.given_responses.count() == self.question.correct_responses.count():
			for response in self.given_responses.all():
				if not response in self.question.correct_responses.all():
					return False
			return True
		return False

class Module(models.Model):
	name = models.CharField(max_length=100)
	ordering_number = models.PositiveSmallIntegerField(verbose_name="Ordering Number - Module 1 would be first, then ascending")

	def next_section(self, ordering_number=None):
		if ordering_number:
			try:
				return self.modulesection_set.filter(ordering_number__gt=ordering_number).order_by("ordering_number").first()
			except:
				return None
		else:
			return self.modulesection_set.order_by("ordering_number").first()

	def __str__(self):
		return self.name

class AssessmentQuestion(models.Model):
	text = models.TextField()
	responses = models.ManyToManyField(Response)

	def __str__(self):
		if len(self.text) <= 40:
			return self.text
		return "("+str(self.pk)+") "+self.text[:40]

class AssessmentSection(models.Model):
	name = models.CharField(max_length=100)
	header = models.TextField()
	assessment_questions = models.ManyToManyField(AssessmentQuestion)

	def __str__(self):
		if self.name:
			return self.name
		return "("+str(self.pk)+") "+self.header[:40]

class Assessment(models.Model):
	#assessment_questions = models.ManyToManyField(AssessmentQuestion)
	assessment_sections = models.ManyToManyField(AssessmentSection)
	name = models.CharField(max_length=100)

	def __str__(self):
		return self.name

class AssessmentInstanceSet(models.Model):
	followed_module = models.ForeignKey(Module, null=True, on_delete=models.SET_NULL)
	created = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

	def completed(self):
		for assessment_instance in self.assessmentinstance_set.all():
			if not assessment_instance.complete():
				return False
		for assessment_instance in self.footballassessmentinstance_set.all():
			if not assessment_instance.complete():
				return False
		return True

	def next(self):
		for assessment_instance in self.assessmentinstance_set.all():
			if not assessment_instance.complete():
				return (assessment_instance, "normal")
		for assessment_instance in self.footballassessmentinstance_set.all():
			if not assessment_instance.complete():
				return (assessment_instance, "football")
		return None

class AssessmentInstance(models.Model):
	assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	started = models.DateTimeField(null=True, default=None)
	completed = models.DateTimeField(null=True, default=None)
	instance_set = models.ForeignKey(AssessmentInstanceSet, on_delete=models.CASCADE)

	def initialize(self):
		for section in self.assessment.assessment_sections.all():
			for assessment_question in section.assessment_questions.all():
				new_response = AssessmentQuestionResponse(assessment_question=assessment_question, assessment_section=section, assessment_instance=self)
				new_response.save()

	def complete(self):
		return self.completed != None

class AssessmentQuestionResponse(models.Model):
	assessment_question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)
	assessment_section = models.ForeignKey(AssessmentSection, on_delete=models.CASCADE)
	assessment_instance = models.ForeignKey(AssessmentInstance, on_delete=models.CASCADE)
	given_response = models.ForeignKey(Response, on_delete=models.CASCADE, null=True, default=None)

class FootballAssessment(models.Model):
	question_text = models.TextField(verbose_name="Question Text - use {name} or {yards} to indicate the relevant name or yard line")
	other_text = models.TextField(verbose_name="Text for altrustic option - use {money} to indicate the altruistic value, {name} and {yards} still valid")
	selfish_text = models.TextField(verbose_name="Text for selfish option - use {money} to indicate the current selfish value, {name} and {yards} still valid")
	altruistic_amount = models.SmallIntegerField(verbose_name="Amount both people get for the altruistic option")
	low_selfish_amount = models.SmallIntegerField(verbose_name="Lowest selfish option will get")
	high_selfish_amount = models.SmallIntegerField(verbose_name="Highest selfish option will get")
	step_size = models.PositiveSmallIntegerField(default=10)

class FootballAssessmentInstance(models.Model):
	instance_set = models.ForeignKey(AssessmentInstanceSet, on_delete=models.CASCADE)
	assessment = models.ForeignKey(FootballAssessment, on_delete=models.CASCADE)
	ascending = models.BooleanField(default=False)
	created = models.DateTimeField(auto_now_add=True)
	started = models.DateTimeField(null=True, default=None)
	completed = models.DateTimeField(null=True, default=None)

	def initialize(self):
		yard_list = [(1, "#808080"), (2, "#FF0000"), (5, "#FF8040"), (10, "#FFFF00"), (20, "#0080FF"), (50, "#800080"), (100, "#000000")]
		random.shuffle(yard_list)

		for yard in yard_list:
			new_name = FootballName(instance=self, name="", color=yard[1], yards=yard[0])
			new_name.save()
			new_section = FootballAssessmentSection(instance=self, football_name=new_name)
			new_section.save()
			if self.ascending:
				temp = self.assessment.low_selfish_amount
				while temp <= self.assessment.high_selfish_amount:
					new_response = FootballResponse(section=new_section, selfish_amount=temp)
					new_response.save()
					temp += self.assessment.step_size
			else:
				temp = self.assessment.high_selfish_amount
				while temp >= self.assessment.low_selfish_amount:
					new_response = FootballResponse(section=new_section, selfish_amount=temp)
					new_response.save()
					temp -= self.assessment.step_size

	def has_names(self):
		for name in self.footballname_set.all():
			if name.name == "":
				return False
		return True

	def next_section_question(self):
		for section in self.footballassessmentsection_set.filter(completed__isnull=True).order_by('created'):
			response = section.next_response()
			if response:
				return response
		self.completed = timezone.now()
		self.save()
		return None

	def complete(self):
		if self.completed:
			return True
		if self.footballassessmentsection_set.filter(completed__isnull=True).count() == 0:
			self.completed = timezone.now()
			self.save()
			return True
		return False

class FootballName(models.Model):
	instance = models.ForeignKey(FootballAssessmentInstance, on_delete=models.CASCADE)
	name = models.CharField(max_length=100)
	color = models.CharField(max_length=8)
	yards = models.PositiveSmallIntegerField()

class FootballAssessmentSection(models.Model):
	instance = models.ForeignKey(FootballAssessmentInstance, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	football_name = models.ForeignKey(FootballName, on_delete=models.CASCADE)
	completed = models.DateTimeField(null=True)

	def next_response(self):
		if self.completed:
			return None
		previous_response = None
		for response in self.footballresponse_set.all().order_by('created'):
			if response.selfish_choice == None:
				return {'next':response, 'previous':previous_response}
			previous_response = response
		self.completed = timezone.now()
		self.save()
		return None

class FootballResponse(models.Model):
	section = models.ForeignKey(FootballAssessmentSection, on_delete=models.CASCADE)
	selfish_amount = models.SmallIntegerField()
	selfish_choice = models.BooleanField(null=True, default=None)
	created = models.DateTimeField(auto_now_add=True)

class AssessmentSet(models.Model):
	assessments = models.ManyToManyField(Assessment)
	football_assessment = models.ForeignKey(FootballAssessment, on_delete=models.CASCADE)
	active = models.BooleanField(default=True)

	def instantiate(self, user, followed_module=None):
		instance_set = AssessmentInstanceSet(followed_module=followed_module, user=user)
		instance_set.save()
		for assessment in self.assessments.all():
			instance = AssessmentInstance(instance_set=instance_set, assessment=assessment)
			instance.save()
			instance.initialize()
		football_instance = FootballAssessmentInstance(assessment=self.football_assessment, instance_set=instance_set, ascending=(random.choice([True,False])))
		football_instance.save()
		football_instance.initialize()
		return instance_set

class ModuleSection(models.Model):
	module = models.ForeignKey(Module, on_delete=models.CASCADE)
	ordering_number = models.PositiveSmallIntegerField(verbose_name="Ordering Number - Section 1 would be first, then ascending, for sections within this module")
	video = models.FileField()
	quiz = models.ForeignKey(Quiz, on_delete=models.SET_NULL, null=True)

	def __str__(self):
		return self.video.name

class ModuleInstance(models.Model):
	module = models.ForeignKey(Module, on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	completed = models.DateTimeField(null=True)
	current_section = models.ForeignKey(ModuleSection, on_delete=models.CASCADE)
	current_section_video_complete = models.BooleanField(default=False)

	def next_section(self):
		return self.module.next_section(ordering_number=self.current_section.ordering_number)

class ModuleSectionRewatch(models.Model):
	module_section = models.ForeignKey(ModuleSection, on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	duration = models.DurationField(null=True)

class UserData(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	consented = models.DateTimeField(null=True, default=None, editable=False)
	current_module_instance = models.ForeignKey(ModuleInstance, null=True, default=None, on_delete=models.SET_NULL)