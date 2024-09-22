from django.shortcuts import render, redirect, HttpResponse
from django.http import StreamingHttpResponse
import random
from django.forms.models import model_to_dict
import json
import datetime
from safmeds.models import *
from safmeds.forms import *
from django.contrib.auth import get_user_model, login
from django.core import serializers
import csv
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from safmeds.utils import create_csv
import django_rq
from ica.models import InSituAssessmentInstance

# Create your views here.

def test(request):
	return HttpResponse("Test Successful!")

def splash(request):
	return render(request, 'safmeds/splash.html', {'title':"Bergmark Consulting", 'in_situ_assessment':(InSituAssessmentInstance.objects.filter(users=request.user).count() != 0)})

def first_login(request):
	if request.method == 'POST':
		form = SignUpForm(request.POST)
		form.errors['email'] = ''
		email = form.data['email']
		name = form.data['name']
		try:
			user = get_user_model().objects.get(email=email, name__iexact=name)
			if user.has_usable_password():
				return render(request, 'registration/signup.html', {'form':form, 'errormsg':"You have already created a password. Please login using the link at the top of the screen."})
		except Exception as e:
			print(e)
			return render(request, 'registration/signup.html', {'form':form, 'errormsg':"Your name/email combo wasn't found"})
		raw_password = form.data['password1']
		if form.data['password2'] != raw_password:
			return render(request, 'registration/signup.html', {'form':form, 'errormsg':"Your passwords didn't match"})
		user.set_password(raw_password)
		user.save()
		login(request, user)
		return splash(request)
	else:
		form = SignUpForm()
	return render(request, 'registration/signup.html', {'form': form})

def decks(request):
	if request.user.is_superuser:
		decks = Deck.objects.all()
	else:
		decks = request.user.deck_set.all()
	return render(request, 'safmeds/select.html', {'participants':decks})

def practice_selection(request, deck):
	try:
		print(deck)
		deck = Deck.objects.get(pk=deck)
	except e:
		print(e)
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for. Use the above link to return to the menu."})
	if request.user.is_superuser:
		return progress(request, deck.pk)
	if deck.test_out:
		return render(request, "safmeds/practice_selection_test_out.html", {'deck':deck})
	return render(request, "safmeds/practice_selection.html", {'deck':deck})

def practice_full(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for. Use the above link to return to the menu."})
	practice_cards = [model_to_dict(card) for card in deck.cards.all()]
	random.shuffle(practice_cards)
	return render(request, "safmeds/practice.html", {'cards':practice_cards, 'practice_type':'full', 'deck':deck.id})

def practice_minute(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for. Use the above link to return to the menu."})
	practice_cards = [model_to_dict(card) for card in deck.cards.all()]
	random.shuffle(practice_cards)
	return render(request, "safmeds/practice.html", {'cards':practice_cards, 'practice_type':'minute', 'deck':deck.id})

def practice_errors(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	try:
		last_practice = Practice.objects.filter(student=request.user, deck=deck).latest("created")
	except:
		return render(request, "safmeds/plain.html", {"msg":"You don't have any practices with the selected deck.\nUse the above link to return to the menu."})
	practice_cards = []
	for response in last_practice.practiceresponse_set.all():
		if not response.correct():
			practice_cards.append(model_to_dict(response.card))
	if len(practice_cards) == 0:
		return render(request, "safmeds/plain.html", {"msg":"You didn't get any cards incorrect on your last timing!\nUse the above link to return to the menu."})
	random.shuffle(practice_cards)
	return render(request, "safmeds/practice.html", {'cards':practice_cards, 'practice_type':'errors', 'deck':deck.id})

def practice_test_out(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	if not deck.test_out:
		return render(request, "safmeds/plain.html", {"msg":"This deck does not offer the requested function.\nPlease don't try to navigate the site by editing the URL, use the provided links.\nUse the above link to return to the menu."})
	practice_cards = [model_to_dict(card) for card in deck.cards.all()]
	random.shuffle(practice_cards)
	return render(request, "safmeds/test_out.html", {'cards':practice_cards, 'deck':deck.id})

def report(request):
	if request.method != "POST":
		return redirect("safmeds:decks")
	print(request.POST)
	responses = json.loads(request.POST['responses'])
	practice = Practice(student=request.user, deck=Deck.objects.get(pk=request.POST['deck']), practice_type=request.POST['practice_type'])
	if not 'duration' in request.POST.keys():
		practice.duration = datetime.timedelta(milliseconds=60000)
	else:
		practice.duration = datetime.timedelta(milliseconds=int(request.POST['duration']))
	practice.save()
	for response in responses:
		new_response = PracticeResponse(practice=practice, card=Card.objects.get(pk=int(response['card_id'])), response=response['response'], latency=datetime.timedelta(milliseconds=int(response['latency'])))
		new_response.save()
		print(new_response.response)
	return HttpResponse("Responses Recieved")

def view_deck(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	payload = []
	for card in deck.cards.all():
		payload.append({'definition':card.definition, 'term':card.term})
	return render(request, "safmeds/view_deck.html", {"cards":payload, "deck_name":deck.name})

def progress(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	if request.user.is_superuser:
		students = get_user_model().objects.filter(deck=deck)
		return render(request, "safmeds/select.html", {"participants":students, "next":'safmeds:super_progress', "actual_deck_id":deck.id})
	else:
		practices_list = Practice.objects.filter(student=request.user, deck=deck).order_by("-created")
		paginator = Paginator(practices_list, 20)
		practices = paginator.get_page(request.GET.get('page', 1))
	return render(request, "safmeds/progress.html", {"practices":practices, "name":request.user.name})

def super_progress(request, deck, student):
	if not request.user.is_superuser:
		return progress(request, deck)
	try:
		deck = Deck.objects.get(pk=deck)
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck or student you're looking for.\nUse the above link to return to the menu."})
	practices_list = Practice.objects.filter(student=student, deck=deck).order_by("-created")
	paginator = Paginator(practices_list, 20)
	practices = paginator.get_page(request.GET.get('page', 1))
	return render(request, "safmeds/progress.html", {"practices":practices, "name":student.name})

def specific_result(request, practice):
	try:
		practice = Practice.objects.get(pk=practice)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	return render(request, "safmeds/view_practice.html", {"practice":practice.practiceresponse_set.all()})

def multi_upload(request):
	if request.user.is_superuser:
		return render(request, "safmeds/multi_upload.html")
	return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})

def multi_upload_report(request):
	if request.method != "POST":
		return redirect("safmeds:multi_upload")
	long_string = request.POST['cards']
	cards = long_string.split("\r\n")
	new_cards = []
	deletable_cards = []
	for card in cards:
		split_str = card.split("  ")
		if len(split_str) != 2:
			split_str = card.split("\t")
		if len(split_str) != 2:
			for card in deletable_cards:
				card.delete()
			return render(request, "safmeds/plain.html", {"msg":"The line \"" + card + "\" didn't parse. Please re-do this deck."})
		existing = Card.objects.filter(term=split_str[0], definition=split_str[1])
		if existing.count() == 0:
			new_card = Card(term=split_str[0], definition=split_str[1])
			new_card.save()
			new_cards.append(new_card)
			deletable_cards.append(new_card)
		else:
			new_cards.append(existing[0])
	new_deck = Deck(name=request.POST['name'])
	if "testout" in request.POST:
		new_deck.test_out = True
	new_deck.save()
	new_deck.cards.add(*new_cards)
	return redirect("safmeds:decks")

def reset_select(request):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	participants = [user for user in get_user_model().objects.all() if not user.is_superuser and user.has_usable_password()]
	return render(request, 'safmeds/download_select.html', {'participants':participants, 'password_reset':True})

def reset_password(request, student):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		user = get_user_model().objects.get(pk=student)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	user.set_unusable_password()
	user.save()
	return redirect("/")

def download_select(request):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	participants = [user for user in get_user_model().objects.all() if not user.is_superuser]
	return render(request, 'safmeds/download_select.html', {'participants':participants})

def download_deck_select(request):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	participants = [deck for deck in Deck.objects.all()]
	return render(request, 'safmeds/download_select.html', {'participants':participants, 'deck_download':True})

def download_type_select(request, student):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		user = get_user_model().objects.get(pk=student)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	return render(request, 'safmeds/download_type_select.html', {'student':student})

def download_deck_type_select(request, deck):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	return render(request, 'safmeds/download_type_select.html', {'student':deck.pk, 'deck_type':True})

def download_timings(request, student):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		user = get_user_model().objects.get(pk=student)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})

	args_dict = {'user_pk':student, 'filename':str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__user_' + user.name + "_timings.csv"}
	args_dict['csv_type'] = 'timings'

	try:
		args_dict['start_year'] = int(request.GET['startyear'])
		args_dict['start_month'] = int(request.GET['startmonth']) + 1
		args_dict['start_day'] = int(request.GET['startday']) + 1
		args_dict['end_year'] = int(request.GET['endyear'])
		args_dict['end_month'] = int(request.GET['endmonth']) + 1
		args_dict['end_day'] = int(request.GET['endday']) + 1
		args_dict['dates'] = True
	except:
		args_dict['dates'] = False

	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()

	return redirect("safmeds:queued")

	#response = HttpResponse(content_type='text/csv')
	#response['Content-Disposition'] = 'attachment; filename="user_' + user.name + '_timings.csv"'

	#writer = csv.writer(response)
	#writer.writerow(["Created On", "Deck", "Correct Per Minute", "Incorrect Per Minute", "Duration", "Total Correct", "Total Incorrect"])

	#try:
	#	start_year = int(request.GET['startyear'])
	#	start_month = int(request.GET['startmonth']) + 1
#		start_day = int(request.GET['startday']) + 1
#		end_year = int(request.GET['endyear'])
#		end_month = int(request.GET['endmonth']) + 1
#		end_day = int(request.GET['endday']) + 1
#		practices = Practice.objects.select_related('deck').filter(student=user).filter(created__gte=datetime.date(start_year, start_month, start_day)).filter(created__lte=datetime.date(end_year, end_month, end_day)).order_by("deck__name", "created")
#	except Exception as e:
#		print(e)
#		practices = Practice.objects.select_related('deck').filter(student=user).order_by("deck__name", "created")
#	for practice in practices:
#		writer.writerow([practice.created.strftime("%H:%M:%S %b %d, %Y"), practice.deck.name,  practice.correctPerMinute(), practice.incorrectPerMinute(), practice.templateDuration(), practice.correct(), practice.incorrect()])
		
#	return response

def download_timings_deck(request, deck):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	
	args_dict = {'deck_pk':deck.pk, 'filename':str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__deck' + deck.name + "_timings.csv"}
	args_dict['csv_type'] = 'timings'

	try:
		args_dict['start_year'] = int(request.GET['startyear'])
		args_dict['start_month'] = int(request.GET['startmonth']) + 1
		args_dict['start_day'] = int(request.GET['startday']) + 1
		args_dict['end_year'] = int(request.GET['endyear'])
		args_dict['end_month'] = int(request.GET['endmonth']) + 1
		args_dict['end_day'] = int(request.GET['endday']) + 1
		args_dict['dates'] = True
	except:
		args_dict['dates'] = False

	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()

	return redirect("safmeds:queued")

#	response = HttpResponse(content_type='text/csv')
#	response['Content-Disposition'] = 'attachment; filename="deck_' + deck.name + '_timings.csv"'
#
#	writer = csv.writer(response)
#	writer.writerow(["Created On", "Student", "Correct Per Minute", "Incorrect Per Minute", "Duration", "Total Correct", "Total Incorrect"])

#	try:
#		start_year = int(request.GET['startyear'])
#		start_month = int(request.GET['startmonth']) + 1
#		start_day = int(request.GET['startday']) + 1
#		end_year = int(request.GET['endyear'])
#		end_month = int(request.GET['endmonth']) + 1
#		end_day = int(request.GET['endday']) + 1
#		practices = Practice.objects.select_related('student').filter(deck=deck).filter(created__gte=datetime.date(start_year, start_month, start_day)).filter(created__lte=datetime.date(end_year, end_month, end_day)).order_by("student__name", "created")
#	except Exception as e:
#		print(e)
#		practices = Practice.objects.select_related('student').filter(deck=deck).order_by("student__name", "created")
#	for practice in practices:
#		writer.writerow([practice.created.strftime("%H:%M:%S %b %d, %Y"), practice.student.name,  practice.correctPerMinute(), practice.incorrectPerMinute(), practice.templateDuration(), practice.correct(), practice.incorrect()])
#	return response

def download_responses(request, student):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		user = get_user_model().objects.get(pk=student)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	
	args_dict = {'user_pk':student, 'filename':str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__user_' + user.name + "_responses.csv"}
	args_dict['csv_type'] = 'responses'

	try:
		args_dict['start_year'] = int(request.GET['startyear'])
		args_dict['start_month'] = int(request.GET['startmonth']) + 1
		args_dict['start_day'] = int(request.GET['startday']) + 1
		args_dict['end_year'] = int(request.GET['endyear'])
		args_dict['end_month'] = int(request.GET['endmonth']) + 1
		args_dict['end_day'] = int(request.GET['endday']) + 1
		args_dict['dates'] = True
	except:
		args_dict['dates'] = False

	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()

	return redirect("safmeds:queued")

#	response = HttpResponse(content_type='text/csv')
#	response['Content-Disposition'] = 'attachment; filename="user_' + user.name + '_responses.csv"'
#
#	writer = csv.writer(response)
#	writer.writerow(["Timing Created On", "Term", "Definition", "Response Given", "Correct"])
#
#	try:
#		start_year = int(request.GET['startyear'])
#		start_month = int(request.GET['startmonth']) + 1
#		start_day = int(request.GET['startday']) + 1
#		end_year = int(request.GET['endyear'])
#		end_month = int(request.GET['endmonth']) + 1
#		end_day = int(request.GET['endday']) + 1
#		practices = Practice.objects.filter(student=user).filter(created__gte=datetime.date(start_year, start_month, start_day)).filter(created__lte=datetime.date(end_year, end_month, end_day)).order_by("deck__name", "created")
#	except Exception as e:
#		print(e)
#		practices = Practice.objects.filter(student=user).order_by("deck__name", "created")
#	for practice in practices:
#		for practice_response in practice.practiceresponse_set.select_related('card').all():
#			writer.writerow([practice.created.strftime("%H:%M:%S %b %d, %Y"), practice_response.card.term, practice_response.card.definition, practice_response.response, practice_response.correct()])
#		writer.writerow(['',])
#	return response

def download_responses_deck(request, deck):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})

	args_dict = {'deck_pk':deck.pk, 'filename':str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__deck_' + deck.name + "_responses.csv"}
	args_dict['csv_type'] = 'responses'

	try:
		args_dict['start_year'] = int(request.GET['startyear'])
		args_dict['start_month'] = int(request.GET['startmonth']) + 1
		args_dict['start_day'] = int(request.GET['startday']) + 1
		args_dict['end_year'] = int(request.GET['endyear'])
		args_dict['end_month'] = int(request.GET['endmonth']) + 1
		args_dict['end_day'] = int(request.GET['endday']) + 1
		args_dict['dates'] = True
	except:
		args_dict['dates'] = False

	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()

	return redirect("safmeds:queued")

#	response = HttpResponse(content_type='text/csv')
#	response['Content-Disposition'] = 'attachment; filename="deck_' + deck.name + '_responses.csv"'
#
#	writer = csv.writer(response)
#	writer.writerow(["Student", "Timing Created On", "Term", "Definition", "Response Given", "Correct"])
#
#	try:
#		start_year = int(request.GET['startyear'])
#		start_month = int(request.GET['startmonth']) + 1
#		start_day = int(request.GET['startday']) + 1
#		end_year = int(request.GET['endyear'])
#		end_month = int(request.GET['endmonth']) + 1
#		end_day = int(request.GET['endday']) + 1
#		practices = Practice.objects.filter(deck=deck).filter(created__gte=datetime.date(start_year, start_month, start_day)).filter(created__lte=datetime.date(end_year, end_month, end_day)).order_by("student__name", "created")
#	except Exception as e:
#		print(e)
#		practices = Practice.objects.filter(deck=deck).order_by("student__name", "created")
#	for practice in practices:
#		for practice_response in practice.practiceresponse_set.select_related('card').all():
#			writer.writerow([practice.student.name, practice.created.strftime("%H:%M:%S %b %d, %Y"), practice_response.card.term, practice_response.card.definition, practice_response.response, practice_response.correct()])
#		writer.writerow(['',])
#	return response

def queued(request):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	files = File.objects.all()
	args = []
	for file in files:
		#Check if the file exists and is finished
		args.append({'name':file.name, 'created':file.created, 'ready':default_storage.exists(file.name)})
	return render(request, "safmeds/queued.html", {"files":args})

def retrieve(request, filename):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	if not default_storage.exists(filename):
		return redirect("safmeds:queued")

	retrieved_file = default_storage.open(filename, 'r')

	response = HttpResponse(retrieved_file, content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=' + filename.replace(" ", "_")

	return response

def delete(request, filename):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	default_storage.delete(filename)
	file.delete()
	return redirect("safmeds:queued")

def mark(request):
	if not request.POST:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		practice_response = PracticeResponse.objects.get(pk=request.POST['response'])
		if not request.user.is_superuser and not practice_response.practice.student == request.user:
			return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
		practice_response.manual_correct = not practice_response.manual_correct
		practice_response.save()
		return HttpResponse("Success!")
	except Exception as e:
		return HttpResponse("Failure: " + str(e))

def index(request):
	return redirect("safmeds:decks")

def view_set(request, deck):
	try:
		deck = Deck.objects.get(pk=deck)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the deck you're looking for.\nUse the above link to return to the menu."})
	to_send = []
	for card in deck.cards.all():
		to_send.append({'see':card.definition, 'type':card.term})
	return render(request, "safmeds/view_full_set.html", {"cards":to_send})

def delete_timing(request, timing):
	if not request.user.is_superuser:
		return render(request, "safmeds/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the main menu."})
	try:
		practice = Practice.objects.get(pk=timing)
	except:
		return render(request, "safmeds/plain.html", {"msg":"I couldn't find the timing you're looking for.\nUse the above link to return to the menu."})
	student = practice.student
	deck = practice.deck
	practice.delete()
	return super_progress(request, deck.pk, student.pk)