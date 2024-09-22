from django.db import models
from django.utils import timezone
from nluaba import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.models import CloudinaryField

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

class Image(models.Model):
    name = models.CharField(max_length=100)
    image = CloudinaryField('image')

    def __str__(self):
        return self.name

class Question(models.Model):
    objectives = models.ManyToManyField(Objective)
    text = models.TextField()
    correct_answer = models.TextField(blank=True)
    incorrect_answer_1 = models.TextField(blank=True)
    incorrect_answer_2 = models.TextField(blank=True)
    incorrect_answer_3 = models.TextField(blank=True)
    image = models.ForeignKey(Image, on_delete="SET_NULL", null=True, blank=True, related_name="q_image")
    correct_answer_image = models.ForeignKey(Image, on_delete="SET_NULL", null=True, blank=True, related_name="correct_image")
    incorrect_answer_1_image = models.ForeignKey(Image, on_delete="SET_NULL", null=True, blank=True, related_name="incorrect_image_1")
    incorrect_answer_2_image = models.ForeignKey(Image, on_delete="SET_NULL", null=True, blank=True, related_name="incorrect_image_2")
    incorrect_answer_3_image = models.ForeignKey(Image, on_delete="SET_NULL", null=True, blank=True, related_name="incorrect_image_3")
    feedback = models.TextField(default="", blank=True)
    points = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.text

    def short_answer(self):
        return self.correct_answer == ""

class Test(models.Model):
    name = models.CharField(max_length=100)
    time_limit = models.DurationField(blank=True, null=True, verbose_name="Time Limit. Note if you just put a number, it defaults to seconds. Can accept XX:XX")
    active = models.BooleanField(default=True)
    instructions = models.TextField(blank=True)
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    questions = models.ManyToManyField(Question, blank=True)
    auto_release_feedback = models.BooleanField(default=False)
    multiple_sittings = models.BooleanField(default=False, verbose_name="Can be done over multiple sittings")
    retake = models.BooleanField(default=True, verbose_name="Can be retaken once completed")

    def __str__(self):
        return self.name

    def total_questions(self):
        return self.questions.count()

    def total_score(self):
        total = 0
        for question in self.questions.all():
            total += question.points
        for question in self.testquestionordering_set.all():
            total += question.question.points
        return total

class TestQuestionOrdering(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    ordering = models.SmallIntegerField()

class TestInstance(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='realinstance')
    created = models.DateTimeField(editable=False, auto_now_add=True)
    finished = models.DateTimeField(editable=False, null=True, blank=True, default=None)
    feedback_released = models.BooleanField(default=False)

    def score(self):
        score = 0
        for response in self.testresponse_set.all():
            score += response.earned_points
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
    manual_correct = models.BooleanField(default=False)
    feedback = models.TextField(default="")
    earned_points = models.DecimalField(max_digits=4, decimal_places=2, default=1)

    def correct(self):
        return (self.answer == self.question.correct_answer and self.answer != "") or self.manual_correct

    def get_feedback(self):
        if self.feedback != "":
            return self.feedback
        return self.question.feedback

class File(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)