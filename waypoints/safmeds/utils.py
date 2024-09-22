from safmeds.models import *
from django.contrib.auth import get_user_model
import unicodecsv as csv
from django.core.files.storage import default_storage
import datetime
from django.utils import timezone

def create_csv(args):
	new_file = default_storage.open(args['filename'], 'wb')
	writer = csv.writer(new_file, dialect='excel', encoding='utf-8')
	if 'user_pk' in args and args['csv_type'] == "timings":
		print("User Timings")
		writer.writerow(["Created On", "Deck", "Correct Per Minute", "Incorrect Per Minute", "Duration", "Total Correct", "Total Incorrect"])
		user = get_user_model().objects.get(pk=args['user_pk'])
		if args['dates']:
			start_date = datetime.date(args['start_year'], args['start_month'], args['start_day'])
			end_date = datetime.date(args['end_year'], args['end_month'], args['end_day'])
			practices = Practice.objects.select_related('deck').filter(student=user).filter(created__gte=start_date).filter(created__lte=end_date).order_by("deck__name", "created")
		else:
			practices = Practice.objects.select_related('deck').filter(student=user).order_by("deck__name", "created")
		for practice in practices:
			writer.writerow([practice.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), practice.deck.name,  practice.correctPerMinute(), practice.incorrectPerMinute(), practice.templateDuration(), practice.correct(), practice.incorrect()])
	elif 'deck_pk' in args and args['csv_type'] == "timings":
		writer.writerow(["Created On", "Student", "Correct Per Minute", "Incorrect Per Minute", "Duration", "Total Correct", "Total Incorrect"])
		deck = Deck.objects.get(pk=args['deck_pk'])
		if args['dates']:
			start_date = datetime.date(args['start_year'], args['start_month'], args['start_day'])
			end_date = datetime.date(args['end_year'], args['end_month'], args['end_day'])
			practices = Practice.objects.select_related('student').filter(deck=deck).filter(created__gte=start_date).filter(created__lte=end_date).order_by("student__name", "created")
		else:
			practices = Practice.objects.select_related('student').filter(deck=deck).order_by("student__name", "created")
		for practice in practices:
			writer.writerow([practice.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), practice.student.name,  practice.correctPerMinute(), practice.incorrectPerMinute(), practice.templateDuration(), practice.correct(), practice.incorrect()])
	elif 'user_pk' in args:
		writer.writerow(["Timing Created On", "Term", "Definition", "Response Given", "Correct", "Latency"])
		user = get_user_model().objects.get(pk=args['user_pk'])
		if args['dates']:
			start_date = datetime.date(args['start_year'], args['start_month'], args['start_day'])
			end_date = datetime.date(args['end_year'], args['end_month'], args['end_day'])
			practices = Practice.objects.filter(student=user).filter(created__gte=start_date).filter(created__lte=end_date).order_by("deck__name", "created")
		else:
			practices = Practice.objects.filter(student=user).order_by("deck__name", "created")
		for practice in practices:
			for practice_response in practice.practiceresponse_set.select_related('card').all():
				writer.writerow([practice.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), practice_response.card.term, practice_response.card.definition, practice_response.response, practice_response.correct(), practice_response.templateLatency()])
			writer.writerow(['',])
	else:
		writer.writerow(["Student", "Timing Created On", "Term", "Definition", "Response Given", "Correct", "Latency"])
		deck = Deck.objects.get(pk=args['deck_pk'])
		if args['dates']:
			start_date = datetime.date(args['start_year'], args['start_month'], args['start_day'])
			end_date = datetime.date(args['end_year'], args['end_month'], args['end_day'])
			practices = Practice.objects.filter(deck=deck).filter(created__gte=start_date).filter(created__lte=end_date).order_by("student__name", "created")
		else:
			practices = Practice.objects.filter(deck=deck).order_by("student__name", "created")
		for practice in practices:
			for practice_response in practice.practiceresponse_set.select_related('card').all():
				writer.writerow([practice.student.name, practice.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), practice_response.card.term, practice_response.card.definition, practice_response.response, practice_response.correct(), practice_response.templateLatency()])
			writer.writerow(['',])
	new_file.close()