from django.db import models
from django.utils import timezone
from nluaba import settings

# Create your models here.
class Card(models.Model):
    term = models.CharField(max_length=200)
    definition = models.TextField()

    def __str__(self):
        return self.term

class Deck(models.Model):
    name = models.CharField(max_length=50)
    cards = models.ManyToManyField(Card, editable=False)
    students = models.ManyToManyField(settings.AUTH_USER_MODEL)
    test_out = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Practice(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    practice_type = models.CharField(max_length=10)
    deck = models.ForeignKey(Deck, on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(editable=False)
    duration = models.DurationField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        return super(Practice, self).save(*args, **kwargs)

    def correct(self):
        correct = [1 for item in self.practiceresponse_set.all() if item.correct()]
        return len(correct)

    def incorrect(self):
        incorrect = [1 for item in self.practiceresponse_set.all() if not item.correct()]
        return len(incorrect)

    def correctPerMinute(self):
        return self.correct()/(self.duration.total_seconds()/60.0)

    def incorrectPerMinute(self):
        return self.incorrect()/(self.duration.total_seconds()/60.0)

    def templateDuration(self):
        return str((self.duration.seconds//60)%60) + " min " + str(self.duration.seconds%60) + " sec"

class PracticeResponse(models.Model):
    practice = models.ForeignKey(Practice, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    response = models.CharField(max_length=200)
    manual_correct = models.BooleanField(default=False)
    latency = models.DurationField(null=True, default=None)

    def correct(self):
        if (self.response.lower().replace("`", "'").replace("  ", " ").strip() == self.card.term.lower().replace("`", "'").replace("  ", " ")) or self.manual_correct:
            return True
        return False

    def templateLatency(self):
        if self.latency:
            return str(self.latency.total_seconds()) + " sec"
        return "Unrecorded"

class File(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)