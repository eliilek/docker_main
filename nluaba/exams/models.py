from django.db import models
from django.utils import timezone
from nluaba import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.models import CloudinaryField
import random
import datetime

# Create your models here.
class ContentArea(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Objective(models.Model):
    name = models.CharField(max_length=100)
    content_area = models.ForeignKey(ContentArea, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        ordering=['name']

class Course(models.Model):
    name = models.CharField(max_length=100)
    objectives = models.ManyToManyField(Objective)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Image(models.Model):
    name = models.CharField(max_length=100)
    image = CloudinaryField('image')

    def __str__(self):
        return self.name

class Question(models.Model):
    objectives = models.ManyToManyField(Objective)
    text = models.TextField()
    correct_answer = models.TextField()
    incorrect_answer_1 = models.TextField()
    incorrect_answer_2 = models.TextField()
    incorrect_answer_3 = models.TextField()
    image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True, related_name="q_image")
    correct_answer_image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True, related_name="correct_image")
    incorrect_answer_1_image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True, related_name="incorrect_image_1")
    incorrect_answer_2_image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True, related_name="incorrect_image_2")
    incorrect_answer_3_image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, blank=True, related_name="incorrect_image_3")
    feedback = models.TextField(default="")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.text

    def test_string(self):
        return "Unimplemented for practice exams"

    def objectives_string(self):
        output = ""
        for objective in self.objectives.all():
            if output != "":
                output += ", "
            output += objective.name
        return output

class Maintenance(models.Model):
    courses = models.ManyToManyField(Course)

    def course_string(self):
        output = ""
        for course in self.courses.all():
            if output != "":
                output = output + ", "
            output = output + str(course)
        return output

    def create_instance(self, user):
        new_instance = MaintenanceInstance(maintenance=self, user=user)
        new_instance.save()
        exclude = []
        objectives = []
        for course in self.courses.all():
            for objective in course.objectives.all():
                objectives.append(objective)
        random.shuffle(objectives)
        for objective in objectives:
            questions = Question.objects.filter(objectives=objective).exclude(pk__in=exclude)
            choice = random.choice(questions)
            exclude.append(choice.pk)
            new_response = MaintenanceResponse(maintenance_instance=new_instance, question=choice)
            new_response.save()
        return new_instance

class MaintenanceInstance(models.Model):
    maintenance = models.ForeignKey(Maintenance, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(editable=False, auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return self.user.name + " Probe"

    def score(self):
        score = 0
        for response in self.maintenanceresponse_set.all():
            if response.correct():
                score += 1
        return score

    def complete(self):
        if self.finished:
            return True
        return False

    def total_questions(self):
        return self.maintenanceresponse_set.all().count()

    def unanswered_questions(self):
        return self.maintenanceresponse_set.filter(answer="").count()

class MaintenanceResponse(models.Model):
    maintenance_instance = models.ForeignKey(MaintenanceInstance, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)
    feedback = models.TextField(default="", blank=True)

    def correct(self):
        return self.answer == self.question.correct_answer

    def get_feedback(self):
        if self.feedback != "":
            return self.feedback
        return self.question.feedback
    
class Test(models.Model):
    name = models.CharField(max_length=100)
    time_limit = models.DurationField(blank=True, null=True, verbose_name="Time Limit. Note if you just put a number, it defaults to seconds. Can accept XX:XX")
    active = models.BooleanField(default=True)
    instructions = models.TextField(blank=True)
    multiple_sittings = models.BooleanField(default=False, verbose_name="Can be done over multiple sittings")

    def __str__(self):
        return self.name

    def total_questions(self):
        total = 0
        for section in self.testsection_set.all():
            total += section.questions
        return total

class TestSection(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    objective = models.ForeignKey(Objective, on_delete=models.CASCADE, blank=True, null=True)
    content_area = models.ForeignKey(ContentArea, on_delete=models.CASCADE, blank=True, null=True)
    questions = models.PositiveSmallIntegerField(verbose_name="Number of questions from this section")

class TestInstance(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(editable=False, auto_now_add=True)
    finished = models.DateTimeField(editable=False, null=True, blank=True, default=None)
    elapsed_time = models.DurationField(default=datetime.timedelta(0))

    def score(self):
        score = 0
        for response in self.testresponse_set.all():
            if response.correct():
                score += 1
        return score

    def complete(self):
        if self.finished:
            return True
        return False

        #done = True
        #for response in self.testresponse_set.all():
        #    if response.answer == "":
        #        done = False
        #        break
        #return done

    def total_questions(self):
        return self.testresponse_set.all().count()

    def __str__(self):
        return self.user.name + " - " + self.test.name

class TestResponse(models.Model):
    test_instance = models.ForeignKey(TestInstance, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)
    feedback = models.TextField(default="", blank=True)

    def correct(self):
        return self.answer == self.question.correct_answer

    def get_feedback(self):
        if self.feedback != "":
            return self.feedback
        return self.question.feedback

class File(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)