import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nluaba.settings")
django.setup()

from safmeds.models import *
for practice in Practice.objects.all():
	correct = 0
	incorrect = 0
	for item in practice.practiceresponse_set.all():
		if item.correct():
			correct += 1
		else:
			incorrect += 1
	practice.correct = correct
	practice.incorrect = incorrect
	practice.save()