from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from jakeapp.models import *
from jakeapp.forms import *
import re
import sys
from project import settings
from random import shuffle
from django.views.decorators.csrf import csrf_exempt, requires_csrf_token
import json
from django.core.files.storage import default_storage
from django_rq import get_queue

app_queue = get_queue('jake')

# Create your views here.
def signup(request):
	if request.method == 'POST':
		form = CustomUserCreationForm(request.POST)
		if form.is_valid():
			form.save()
			email = form.cleaned_data.get('email')
			raw_password = form.cleaned_data.get('password1')
			user = authenticate(email=email, password=raw_password)
			user_data = UserData(user=user)
			user_data.save()
			login(request, user)
			return redirect('initial')
	else:
		form = CustomUserCreationForm()
	return render(request, 'registration/signup.html', {'form': form})

def initial(request):
	if request.user.is_superuser:
		return redirect("admin:index")
	if not request.user.userdata.consented:
		return redirect("consent")
	if AssessmentInstanceSet.objects.filter(user=request.user).count() == 0:
		#Create the first assessment set
		try:
			active_set = AssessmentSet.objects.get(active=True)
		except:
			return render(request, "jakeapp/error.html", {"msg":"There is no active assessment set configured. Please contact your administrator."})
		new_set = active_set.instantiate(request.user)
	last_set = AssessmentInstanceSet.objects.filter(user=request.user).order_by("created").last()
	if not last_set.completed():
		#Determine which assessment should be up next, render it
		#Next returns a tuple with "normal" or "football" in [1]
		next_assessment_instance = last_set.next()
		if next_assessment_instance[1] == "normal":
			return assessment(request, next_assessment_instance[0].pk)
		else:
			return football_assessment(request, next_assessment_instance[0].pk)
	unfinished_module_instances = ModuleInstance.objects.filter(user=request.user, completed__isnull=True)	
	args = {}
	completed_module_instances = ModuleInstance.objects.filter(user=request.user, completed__isnull=False).order_by("module__ordering_number")
	if unfinished_module_instances.count() > 1:
		return render(request, "jakeapp/error.html", {"msg":"Something has gone wrong. Please contact your database administrator."})
	elif unfinished_module_instances.count() == 1:
		args["in_progress"] = unfinished_module_instances[0]
	else:
		last_completed_instance = completed_module_instances.last()
		assessment_instance_set = AssessmentInstanceSet.objects.filter(user=request.user, followed_module=(last_completed_instance.module if last_completed_instance else None))
		if assessment_instance_set.count() == 0:
			try:
				active_set = AssessmentSet.objects.get(active=True)
			except:
				return render(request, "jakeapp/error.html", {"msg":"There is no active assessment set configured. Please contact your administrator."})
			new_set = active_set.instantiate(request.user, (last_completed_instance.module if last_completed_instance else None))
			return assessment(request, new_set.next()[0].pk)
		last_completed_ordering = (last_completed_instance.module.ordering_number if last_completed_instance else -1)
		upcoming_modules = Module.objects.filter(ordering_number__gt=last_completed_ordering).order_by("ordering_number")
		if upcoming_modules.count() != 0:
			args['upcoming'] = upcoming_modules.first()
	if completed_module_instances.count() != 0:
		args['completed'] = completed_module_instances
	return render(request, "jakeapp/menu.html", args)

def assessment(request, assessment_instance_pk):
	try:
		assessment_instance = AssessmentInstance.objects.get(pk=assessment_instance_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the assessment instance you're looking for. If you have reached this page in error, please contact your administrator."})	
	AssessmentForm = create_assessment_form(assessment_instance)
	if AssessmentForm == None:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the assessment you're looking for. If you have reached this page in error, please contact your administrator."})	
	if request.method == 'POST':
		form = AssessmentForm(request.POST)
	else:
		form = AssessmentForm(None)
	#TODO test if blank responses
	if form.is_valid():
		assessment_instance.started = timezone.datetime.fromtimestamp(int(request.POST['startTimeInput'])/1000, tz=timezone.get_default_timezone())
		assessment_instance.completed = timezone.datetime.fromtimestamp(int(request.POST['endTimeInput'])/1000, tz=timezone.get_default_timezone())
		assessment_instance.save()
		q = re.compile(r"question_response_(\d+)")
		for key in request.POST:
			m = q.match(key)
			if m:
				response = AssessmentQuestionResponse.objects.get(pk=int(m.group(1)))
				response.given_response = Response.objects.get(pk=request.POST[key])
				response.save()
		return redirect("initial")
	return render(request, "jakeapp/assessment_form.html", {"form":form, "object_pk":assessment_instance_pk})

def football_name(request, assessment_instance_pk):
	try:
		assessment_instance = FootballAssessmentInstance.objects.get(pk=assessment_instance_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the Football assessment instance you're looking for. If you have reached this page in error, please contact your administrator."})
	if not request.method == "POST":
		return render(request, "jakeapp/football_name_form.html", {"object_pk":assessment_instance_pk})
	try:
		q = re.compile(r"name_(\d+)")
		for key in request.POST:
			m = q.match(key)
			if m:
				name = FootballName.objects.get(instance=assessment_instance, yards=int(m.group(1)))
				name.name = request.POST[key]
				name.save()
		return redirect(reverse("football_assessment", args=(assessment_instance_pk,)))
	except:
		return render(request, "jakeapp/football_name_form.html", {"object_pk":assessment_instance_pk, "error":"Something has gone wrong"})

def football_formatting(text, name, money=None):
	if money:
		text = text.replace("{money}", "$"+money)
	return text.replace("{name}", "<span style='color:"+name.color+";'>"+name.name+"</span>").replace("{yards}", "<span style='color:"+name.color+";'>"+str(name.yards)+"</span>")

def football_assessment(request, assessment_instance_pk):
	try:
		assessment_instance = FootballAssessmentInstance.objects.get(pk=assessment_instance_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the Football assessment instance you're looking for. If you have reached this page in error, please contact your administrator."})
	#Check if we have valid names, if empty render name form
	#Pass it object_pk=assessment_instance_pk
	if not assessment_instance.has_names():
		return render(request, "jakeapp/football_name_form.html", {"object_pk":assessment_instance_pk})
	#Get next unfinished section, render form for that
	next_section_question = assessment_instance.next_section_question()
	if next_section_question == None:
		#Assessment is over, move on
		return redirect("initial")
	#Do text replacements
	football_name = next_section_question['next'].section.football_name
	render_args = {}
	if next_section_question['previous'] and next_section_question['previous'].selfish_choice:
		render_args['previous_text'] = football_formatting(assessment_instance.assessment.selfish_text, football_name, str(next_section_question['previous'].selfish_amount))
	elif next_section_question['previous']:
		render_args['previous_text'] = football_formatting(assessment_instance.assessment.other_text, football_name, str(assessment_instance.assessment.altruistic_amount))
	render_args['question_text'] = football_formatting(assessment_instance.assessment.question_text, football_name)
	render_args['other_text'] = football_formatting(assessment_instance.assessment.other_text, football_name, str(assessment_instance.assessment.altruistic_amount))
	render_args['selfish_text'] = football_formatting(assessment_instance.assessment.selfish_text, football_name, str(next_section_question['next'].selfish_amount))
	render_args['next_pk'] = next_section_question['next'].pk
	return render(request, "jakeapp/football_assessment_form.html", render_args)

def football_response(request, response_pk):
	if not request.method == "POST":
		return redirect('initial')
	try:
		football_response = FootballResponse.objects.get(pk=response_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the Football assessment instance you're looking for. If you have reached this page in error, please contact your administrator."})
	football_response.selfish_choice = (request.POST['response'] == 'selfish')
	football_response.save()
	return redirect(reverse("football_assessment", args=(football_response.section.instance.pk,)))

def consent(request):
	if request.user.userdata.consented:
		return redirect('initial')
	if request.method == 'POST':
		request.user.userdata.consented = timezone.now()
		request.user.userdata.save()
		return redirect('initial')
	return render(request, 'jakeapp/consent.html')

def activity(request, activity_pk):
	try:
		activity = Activity.objects.get(pk=activity_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the activity you're looking for. If you have reached this page in error, please contact your administrator."})	
	left_list = []
	right_list = []
	key = {}
	for pair in activity.activity_pairs.all():
		left_list.append(pair.left_text)
		right_list.append(pair.right_text)
		key[pair.left_text] = pair.right_text
	shuffle(right_list)
	shuffled_list = zip(left_list, right_list)
	return render(request, "jakeapp/activity.html", {"shuffled_list":shuffled_list, "key":key, "left_header":activity.left_column_header, "right_header":activity.right_column_header, "activity_pk":activity_pk})

def activity_submit(request, activity_pk):
	try:
		activity = Activity.objects.get(pk=activity_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the activity you're looking for. If you have reached this page in error, please contact your administrator."})	
	if request.method != "POST":
		return redirect(reverse('activity', args=(activity_pk, )))
	new_activity_instance = ActivityInstance(activity=activity, user=request.user, duration=timezone.timedelta(milliseconds=int(request.POST['durationInput'])))
	new_activity_instance.save()
	module_instance = request.user.userdata.current_module_instance
	if module_instance.next_section():
		module_instance.current_section = module_instance.next_section()
		module_instance.current_section_video_complete = False
		module_instance.save()
		return redirect(reverse("resume", args=(module_instance.pk,)))
	else:
		module_instance.completed = timezone.now()
		module_instance.save()
		request.user.userdata.current_module_instance = None
		request.user.userdata.save()
		return redirect("initial")

def quiz(request, quiz_pk):
	QuizForm = create_quiz_form(quiz_pk)
	if QuizForm == None:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the quiz you're looking for. If you have reached this page in error, please contact your administrator."})	
	if request.method == 'POST':
		form = QuizForm(request.POST)
	else:
		form = QuizForm(None)
	if form.is_valid():
		quiz_instance = QuizInstance(user=request.user, quiz=Quiz.objects.get(pk=quiz_pk), duration=timezone.timedelta(milliseconds=int(request.POST['durationInput'])))
		quiz_instance.save()
		for question in quiz_instance.quiz.questions.all():
			new_response = QuestionResponse(question=question, quiz_instance=quiz_instance)
			new_response.save()
		feedback_errors = {}
		q = re.compile(r"question_(\d+)")
		#TODO Test with multiple correct answers, will be sent as lists I think
		for key in request.POST:
			m = q.match(key)
			if m:
				response = QuestionResponse.objects.get(quiz_instance=quiz_instance, question=Question.objects.get(pk=int(m.group(1))))
				response.given_responses.add(*[int(item) for item in request.POST.getlist(key)])
				response.save()
				if not response.correct():
					feedback_errors['question_' + str(response.question.pk)] = "Incorrect"
		if quiz_instance.passed():
			module_instance = request.user.userdata.current_module_instance
			if module_instance.next_section():
				module_instance.current_section = module_instance.next_section()
				module_instance.current_section_video_complete = False
				module_instance.save()
				return redirect(reverse("resume", args=(module_instance.pk,)))
			else:
				module_instance.completed = timezone.now()
				module_instance.save()
				request.user.userdata.current_module_instance = None
				request.user.userdata.save()
				return redirect("initial")
		else:
			for error in feedback_errors:
				form.add_error(error, feedback_errors[error])
	return render(request, "jakeapp/quiz_form.html", {"form":form, "object_pk":quiz_pk})

def video(request, module_section_pk, object_type=None, object_pk=None):
	try:
		module_section = ModuleSection.objects.get(pk=module_section_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the module section you're looking for. If you have reached this page in error, please contact your administrator."})
	return render(request, "jakeapp/video.html", {"video_file":module_section.video, "object_pk":object_pk, "object_type":object_type, "module_section_pk":module_section_pk})

#def proceed(request):
#	if not request.user.userdata.consented:
#		return redirect("consent")
	#TODO figure out if we should be showing a menu, video, quiz, or assessment set

def resume(request, instance_pk):
	#English - If the current section video isn't complete, run the current section
	#If the video is complete, run the current section quiz if exists
	try:
		module_instance = ModuleInstance.objects.get(pk=instance_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the module instance you're looking for. If you have reached this page in error, please contact your administrator."})
	if module_instance.current_section_video_complete:
		if module_instance.current_section.quiz:
			if module_instance.current_section.quiz.activity:
				return activity(request, module_instance.current_section.quiz.activity.pk)
			return quiz(request, module_instance.current_section.quiz.pk)
		else:
			next_section = module_instance.next_section()
			if next_section:
				#Setup next section
				module_instance.current_section_video_complete = False
				module_instance.current_section = next_section
				module_instance.save()
				return video(request, next_section.pk, object_type="ModuleInstance", object_pk=module_instance.pk)
			else:
				#Module has ended
				module_instance.completed = timezone.now()
				module_instance.save()
				request.user.userdata.current_module_instance = None
				request.user.userdata.save()
				return redirect("initial")
	return video(request, module_instance.current_section.pk, object_type="ModuleInstance", object_pk=module_instance.pk)

def begin(request, module_pk):
	try:
		module = Module.objects.get(pk=module_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the module you're looking for. If you have reached this page in error, please contact your administrator."})
	sanity_check = ModuleInstance.objects.filter(module=module, user=request.user)
	if sanity_check.count() != 0:
		if sanity_check[0].completed:
			return redirect("initial")
		else:
			return redirect(reverse("resume", args=(sanity_check[0].pk,)))
	new_instance = ModuleInstance(module=module, user=request.user, current_section=module.next_section())
	new_instance.save()
	request.user.userdata.current_module_instance = new_instance
	request.user.userdata.save()
	return redirect(reverse("resume", args=(new_instance.pk,)))

def review(request, module_pk):
	try:
		module = Module.objects.get(pk=module_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the module you're looking for. If you have reached this page in error, please contact your administrator."})
	return render(request, "jakeapp/rewatch_section_menu.html", {"module_sections":module.modulesection_set.all()})	

def rewatch_section(request, module_section_pk):
	try:
		module_section = ModuleSection.objects.get(pk=module_section_pk)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the module section you're looking for. If you have reached this page in error, please contact your administrator."})
	new_rewatch = ModuleSectionRewatch(module_section=module_section, user=request.user, duration=timezone.timedelta(milliseconds=0))
	new_rewatch.save()
	return video(request, module_section.pk, object_type="ModuleSectionRewatch", object_pk=new_rewatch.pk)

@csrf_exempt
#@requires_csrf_token
def beacon(request):
	if not request.method == "POST":
		return HttpResponse("Bad")

	if len(request.POST) == 0:
		my_body = json.loads(request.body)
	else:
		my_body = request.POST
	try:
		module_section = ModuleSection.objects.get(pk=my_body['module_section_pk'])
	except Exception as e:
		print(e)
		return HttpResponse("Bad")

	if my_body['object_type'] == "ModuleSectionRewatch":
		try:
			rewatch = ModuleSectionRewatch.objects.get(pk=int(my_body['object_pk']))
		except:
			try:
				rewatch = ModuleSectionRewatch(module_section=module_section, user=request.user, duration=timezone.timedelta(milliseconds=0), pk=int(my_body['object_pk']))
				rewatch.save()
			except:
				rewatch = ModuleSectionRewatch(module_section=module_section, user=request.user, duration=timezone.timedelta(milliseconds=0))
				rewatch.save()
		rewatch.duration = rewatch.duration + timezone.timedelta(milliseconds=int(my_body['duration']))
		rewatch.save()
		
		return JsonResponse({"link":reverse("review", args=(module_section.module.pk,))})
	elif my_body['object_type'] == "ModuleInstance":
		try:
			module_instance = ModuleInstance.objects.get(pk=my_body['object_pk'])
		except Exception as e:
			print(e)
			return HttpResponse("Bad")
		if SectionDuration.objects.filter(module_instance=module_instance, section=module_section).count() == 0:
			duration = SectionDuration(module_instance=module_instance, section=module_section)
			duration.save()
		else:
			duration = SectionDuration.objects.filter(module_instance=module_instance, section=module_section).first()
		duration.duration = duration.duration + timezone.timedelta(milliseconds=int(my_body['duration']))
		duration.save()
		if "finished" in my_body:
			module_instance.current_section_video_complete = True
			module_instance.save()
			return JsonResponse({"link":reverse("resume", args=(module_instance.pk,))})
	return HttpResponse("OK")

def queued(request):
	if not request.user.is_superuser:
		return render(request, "jakeapp/error.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	files = File.objects.all()
	args = []
	for file in files:
		#Check if the file exists and is finished
		args.append({'name':file.name, 'created':file.created, 'ready':default_storage.exists(file.name)})
	return render(request, "jakeapp/queued.html", {"files":args})

def retrieve(request, filename):
	if not request.user.is_superuser:
		return render(request, "jakeapp/error.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	if not default_storage.exists(filename):
		return redirect("queued")

	retrieved_file = default_storage.open(filename, 'r')

	response = HttpResponse(retrieved_file, content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=' + filename.replace(" ", "_").replace(",", "_")

	return response

def delete(request, filename):
	if not request.user.is_superuser:
		return render(request, "jakeapp/error.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "jakeapp/error.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	default_storage.delete(filename)
	file.delete()
	return redirect("queued")