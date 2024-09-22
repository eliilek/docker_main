from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models import F
from safmeds.models import PracticeResponse

@receiver(pre_save, sender=PracticeResponse)
def update_aggregates(sender, instance, **kwargs):
	practice = instance.practice
	if instance.id != None:
		previous = PracticeResponse.objects.get(pk=instance.pk)
		if previous.correct() and not instance.correct():
			practice.correct = F('correct') - 1
			practice.incorrect = F('incorrect') + 1
		elif instance.correct() and not previous.correct():
			practice.correct = F('correct') + 1
			practice.incorrect = F('incorrect') - 1
	else:
		if instance.correct():
			practice.correct = F('correct') + 1
		else:
			practice.incorrect = F('incorrect') + 1
	practice.save()
	practice.refresh_from_db()