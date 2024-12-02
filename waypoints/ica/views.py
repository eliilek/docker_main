from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from ica.models import *
from django.utils import timezone
from django.core.files.storage import default_storage
import random
import re
from django.contrib.auth import logout as normal_logout
from django.contrib.auth import get_user_model

# Create your views here.
def index(request):
	if Assessment.objects.filter(users=request.user).count() != 0:
		return render(request, 'ica/instructions.html')
	elif request.user.is_superuser:
		return redirect("ica:view_data")
	else:
		return render(request, 'ica/plain.html', {'msg':"You don't have an ICA assessment assigned to you.\nPlease contact Jess at jessica.gamba@waypoints.life"})

def begin_assessment(request):
	#Determine if they have an assessment in progress, otherwise create a new one
	#Display the next unanswered question. Question will poll additions to determine if it's answered or not.
	try:
		assessment_instance = AssessmentInstance.objects.get(user=request.user, finished__isnull=True)
	except:
		for instance in AssessmentInstance.objects.filter(user=request.user, finished__isnull=True):
			instance.finished = timezone.now()
			instance.save()
		assessment = Assessment.objects.filter(users=request.user, active=True)
		if assessment.count() == 2:
			assessment = assessment.filter(in_situ_assessment=False)[0]
		elif assessment[0].in_situ_assessment:
			assessment[0].users.remove(request.user)
			return redirect("ica:index")
		else:
			assessment = assessment[0]
		assessment_instance = AssessmentInstance(assessment=assessment, user=request.user)
		assessment_instance.save()
		#Generate empty AssessmentQuestionResponses and their associated ResponseAnswers
		for question in assessment.get_questions():
			new_response = AssessmentQuestionResponse(assessment_instance=assessment_instance, question=question)
			new_response.save()
			new_response.generate_response_answers()
	assessment_question_responses = assessment_instance.assessmentquestionresponse_set.order_by('created')
	question_response = None
	current_question_number = 0
	for temp_question_response in assessment_question_responses:
		current_question_number += 1
		if not temp_question_response.answered():
			question_response = temp_question_response
			break
	if not question_response:
		#Test is done
		assessment_instance.finished = timezone.now()
		assessment_instance.save()
		assessment_instance.assessment.users.remove(request.user)
		return render(request, "ica/plain.html", {'msg':"Thank you for your submission."})
	else:
		to_send = {'question_type':question_response.question.question_type, 'question_response_pk':question_response.pk}
		to_send['current_question_number'] = current_question_number
		to_send['total_question_number'] = assessment_question_responses.count()
		if question_response.video_name:
			to_send['video_url'] = default_storage.url(question_response.video_name)
		if question_response.label:
			to_send['over_header'] = question_response.label
		if question_response.question.horizontal:
			to_send['horizontal'] = question_response.question.horizontal
		if question_response.question.question_type == "CSA":
			to_send['col_1_header'] = ""
			to_send['col_2_header'] = ""

		to_send['response_answers'] = []
		for response_answer in question_response.responseanswer_set.all().order_by('created'):
			cleaned = {'response_label':response_answer.response_label, 'pk':response_answer.pk}
			if "||" in response_answer.multiple_choice_response_string:
				answers = response_answer.multiple_choice_response_string.split("||")
				random.shuffle(answers)
				cleaned['answers'] = answers
			if "||" in response_answer.response_label:
				if to_send['col_1_header'] == "":
					to_send['col_1_header'] = response_answer.response_label.split(" || ")[1]
				elif to_send['col_2_header'] == "" and to_send['col_1_header'] != response_answer.response_label.split(" || ")[1]:
					to_send['col_2_header'] = response_answer.response_label.split(" || ")[1]
			to_send['response_answers'].append(cleaned)

		question_response.begun = timezone.now()
		question_response.save()

		if question_response.question.question_type == "DD":
			#Render with Drag Drop template
			to_send['range'] = range(6)
			to_send['images'] = [image for image in Image.objects.all()]
			return render(request, "ica/dd_question.html", to_send)
		else:
			#Render with standard question template
			return render(request, "ica/standard_question.html", to_send)

def submit_in_situ_response(request, question_pk=None):
	if not request.method == "POST":
		return redirect("ica:begin_in_situ")
	print(request.POST)
	for key in request.POST:
		m = re.match(r"answer-(\d+)", key)
		if m:
			response_answer = ResponseAnswer.objects.get(pk=int(m.group(1)))
			if response_answer.given_response != request.POST[key]:
				response_answer.given_response = request.POST[key]
				response_answer.answered_timestamp = timezone.now()
				response_answer.save()
			if not response_answer.assessment_question_response.insituassessmentquestionresponse.respondent:
				response_answer.assessment_question_response.insituassessmentquestionresponse.respondent = get_user_model().objects.get(pk=int(request.POST['user_pk']))
				response_answer.assessment_question_response.insituassessmentquestionresponse.save()
		elif key == "next_question":
			question_pk = int(request.POST[key])
	if question_pk:
		return in_situ_assessment(request, question_pk)
	return HttpResponse("Received")

def submit_response(request):
	if not request.method == "POST":
		return redirect("ica:begin_assessment")
	try:
		question_response = AssessmentQuestionResponse.objects.get(pk=request.POST['question_response_pk'])
	except:
		return HttpResponse("Something has gone wrong. Please contact Eli.")
	#Figure out if DD question or other
	#For DD, response_label stores left/right and position on page
	if question_response.question.question_type == "DD":
		response_answers = question_response.responseanswer_set.all().order_by('created')
		for key in request.POST:
			m = re.match(r"answer-left-(\d+)", key)
			if m:
				response_answer = response_answers[int(m.group(1))*2]
			else:
				m = re.match(r"answer-right-(\d+)", key)
				if m:
					response_answer = response_answers[int(m.group(1))*2 + 1]
				else:
					continue
			response_answer.response_label = m.group(0)
			response_answer.given_response = request.POST[key]
			response_answer.answered_timestamp = timezone.now()
			response_answer.save()
	else:
		#For other, regex match answer-%d, number is id of responseanswer object
		for key in request.POST:
			m = re.match(r"answer-(\d+)", key)
			if m:
				response_answer = question_response.responseanswer_set.get(pk=int(m.group(1)))
				response_answer.given_response = request.POST[key]
				response_answer.answered_timestamp = timezone.now()
				response_answer.save()
	return redirect("ica:begin_assessment")

def view_data(request):
	assessment_instances = AssessmentInstance.objects.filter(assessment__in_situ_assessment=False)
	return render(request, "ica/select.html", {"instances":assessment_instances})

def view_in_situ_data(request):
	assessment_instances = AssessmentInstance.objects.filter(assessment__in_situ_assessment=True)
	return render(request, "ica/in_situ_data_select.html", {"instances":assessment_instances})

def mark_in_situ_complete(request, instance_pk):
	try:
		assessment_instance = AssessmentInstance.objects.get(pk=instance_pk)
	except:
		return render(request, "ica/plain.html", {"msg":"I couldn't find the instance you're looking for."})
	assessment_instance.finished = timezone.now()
	assessment_instance.save()
	return redirect(request.META.get('HTTP_REFERER', ""))

def view_instance(request, instance_pk):
	try:
		assessment_instance = AssessmentInstance.objects.get(pk=instance_pk)
	except:
		return render(request, "ica/plain.html", {"msg":"I couldn't find the instance you're looking for."})
	to_send = {'responses':[]}
	for question_response in assessment_instance.assessmentquestionresponse_set.order_by('created'):
		response_dict = {'question_response_pk':question_response.pk, 'task':question_response.question.task, 'question_type':question_response.question.question_type, 'answers':[]}
		response_dict['question_label'] = str(question_response.question)
		if assessment_instance.assessment.in_situ_assessment:
			response_dict['respondent'] = question_response.insituassessmentquestionresponse.respondent
		if question_response.question.question_type == "CSA":
			response_dict['left_label'] = ""
			response_dict['right_label'] = ""
			temp_left = None
		elif question_response.question.question_type == "DD":
			response_dict['left_label'] = "Left"
			response_dict['right_label'] = "Right"
			temp_left = None
		if question_response.label:
			response_dict['question_label'] = question_response.label
		if question_response.video_name:
			response_dict['video'] = question_response.video_name
		response_dict['points'] = question_response.points
		for response_answer in question_response.responseanswer_set.order_by('created'):
			clean_answer = {'response_label':response_answer.response_label.replace(" || ", " "), 'pk':response_answer.pk}
			if question_response.question.question_type == "MC":
				clean_answer['correct_response'] = response_answer.multiple_choice_response_string.split("||")[0]
				clean_answer['given_response'] = response_answer.given_response
			elif question_response.question.question_type == "SA" or question_response.question.question_type == "IS":
				clean_answer['given_response'] = response_answer.given_response
			else:
				if temp_left:
					clean_answer['left_response'] = temp_left.given_response
					clean_answer['right_response'] = response_answer.given_response
					temp_left = None
					clean_answer['response_label'] = ""
				else:
					temp_left = response_answer
					if response_dict['left_label'] == "":
						response_dict['left_label'] = response_answer.response_label.split(" || ")[1]
					continue
			clean_answer['answered_timestamp'] = response_answer.answered_timestamp
			response_dict['answers'].append(clean_answer)
			if question_response.question.question_type == "CSA":
				if response_dict['left_label'] == "":
					response_dict['left_label'] = response_answer.response_label.split(" || ")[1]
				elif response_dict['right_label'] == "" and response_dict['left_label'] != response_answer.response_label.split(" || ")[1]:
					response_dict['right_label'] = response_answer.response_label.split(" || ")[1]
		to_send['responses'].append(response_dict)
	if assessment_instance.assessment.in_situ_assessment:
		return render(request, "ica/view_in_situ_instance.html", to_send)
	return render(request, "ica/view_instance.html", to_send)

def delete_instance(request, instance_pk):
	try:
		assessment_instance = AssessmentInstance.objects.get(pk=instance_pk)
	except:
		return render(request, "ica/plain.html", {"msg":"I couldn't find the instance you're looking for."})
	temp = assessment_instance.assessment.in_situ_assessment
	assessment_instance.delete()
	if temp:
		return redirect("ica:view_in_situ_data")
	return redirect("ica:view_data")

def score(request):
	print(request.POST)
	if request.method != "POST":
		return redirect("ica:view_data")
	for item in request.POST.items():
		print(item)
		try:
			response = AssessmentQuestionResponse.objects.get(pk=int(item[0]))
			response.points = float(item[1])
			response.save()
		except Exception as e:
			print(e)
			return HttpResponseBadRequest("Failure")
	return HttpResponse("Success")

def logout(request):
	normal_logout(request)
	return render(request, "ica/plain.html", {"msg":"You have been logged out due to 10 minutes of inactivity. You can log in again and resume your competency assessment where you left off at any time."})

def create_in_situ(request):
	try:
		in_situ_assessment = Assessment.objects.get(in_situ_assessment=True, active=True)
	except:
		return render(request, "ica/plain.html", {"msg":"I couldn't find an in-situ assessment. Please contact your administrator."})
	to_send = {'questions':[]}
	for question in in_situ_assessment.get_questions():
		to_send['questions'].append(question)
	to_send['users'] = get_user_model().objects.all()
	return render(request, "ica/create_in_situ.html", to_send)

def create_in_situ_report(request):
	if not request.method == "POST" or not request.user.is_superuser:
		return redirect("ica:begin_assessment")
	assessment = Assessment.objects.get(in_situ_assessment=True, active=True)
	new_instance = InSituAssessmentInstance(technician=request.POST['technician'], assessment=assessment)
	new_instance.save()
	for user_pk in request.POST.getlist('users'):
		new_instance.users.add(int(user_pk))
		new_instance.save()
	required_question_pks = []
	for key in request.POST:
		m = re.match(r"required-(\d+)", key)
		if m:
			required_question_pks.append(int(m.group(1)))
	for question in assessment.get_questions():
			new_response = InSituAssessmentQuestionResponse(assessment_instance=new_instance, question=question)
			if question.pk in required_question_pks:
				new_response.required = True
			new_response.save()
			new_response.generate_response_answers()
	return render(request, "ica/plain.html", {"msg":"In-Situ assessment created successfully!"})

def begin_in_situ(request, instance_pk=None):
	if instance_pk == None:
		#If there is only 1 instance they're on, redirect to it. Otherwise select
		instances = InSituAssessmentInstance.objects.filter(users=request.user, finished__isnull=True)
		if instances.count() == 0:
			return render(request, "ica/plain.html", {"msg":"You are not assigned to any incomplete in-situ assessment instances."})
		elif instances.count() == 1:
			instance_pk = instances[0].pk
		else:
			return render(request, "ica/in_situ_select.html", {"instances":instances})
	#Figure out how to begin the in-situ assessment
	request.session['in_situ_pk'] = instance_pk
	return redirect('ica:in_situ_assessment')

def in_situ_first_time(request, instance_pk):
	try:
		assessment_instance = InSituAssessmentInstance.objects.get(pk=instance_pk)
	except:
		return render(request, "ica/plain.html", {"msg":"I couldn't find the instance you're looking for."})
	if request.method == "POST":
		assessment_instance.confirmed_supervisors.add(request.user)
		assessment_instance.save()
		request.session['in_situ_pk'] = instance_pk
		return redirect("ica:in_situ_assessment")
	return render(request, "ica/in_situ_first_time.html", {"instance_pk":instance_pk, "technician":assessment_instance.technician})

def in_situ_assessment(request, question_pk=None):
	if not 'in_situ_pk' in request.session:
		return redirect("ica:begin_in_situ")
	assessment_instance = InSituAssessmentInstance.objects.get(pk=request.session['in_situ_pk'])
	if not request.user in assessment_instance.confirmed_supervisors.all():
		return redirect('ica:in_situ_first_time', instance_pk=assessment_instance.pk)
	assessment_question_responses = assessment_instance.assessmentquestionresponse_set.order_by('created')
	question_response = None
	for temp_question_response in assessment_question_responses:
		if not temp_question_response.answered():
			question_response = temp_question_response
			break
	if not question_response:
		assessment_instance.finished = timezone.now()
		assessment_instance.save()
		return render(request, "ica/plain.html", {'msg':"Thank you for your submission."})
	if question_pk:
		question_response = assessment_question_responses.get(pk=question_pk)
	else:
		to_send = {}
		to_send['question_dicts'] = []
		for question in assessment_question_responses:
			new_dict = {'pk':question.pk}
			if question.insituassessmentquestionresponse.required:
				new_dict['display'] = "<b>**"+str(question.question)+"**</b>"
			else:
				new_dict['display'] = str(question.question)
			#if question.insituassessmentquestionresponse.respondent == request.user:
			#	new_dict['enable_given_responses']
			to_send['question_dicts'].append(new_dict)
		return render(request, "ica/just_nav.html", to_send)
	required_finished = True
	finished_question_numbers = []
	for temp_question_response in assessment_question_responses:
		if temp_question_response.answered():
			m = re.match(r"(\d+) ", str(temp_question_response.question))
			if m and int(m.group(1)) not in finished_question_numbers:
				finished_question_numbers.append(int(m.group(1)))
		elif temp_question_response.insituassessmentquestionresponse.required:
			required_finished = False
			break
	if len(finished_question_numbers) < 3:
		required_finished = False

	#Figure out what we need to pack
	to_send = {'response_answers':[response_answer for response_answer in question_response.responseanswer_set.order_by('created')]}
	to_send['question_response_pk'] = question_response.pk
	if question_response.insituassessmentquestionresponse.respondent == request.user:
		to_send['enable_given_responses'] = True
	to_send['technician'] = question_response.assessment_instance.insituassessmentinstance.technician
	to_send['question_dicts'] = []
	if required_finished and not 'required_shown' in request.session:
		to_send['required_finished'] = True
		request.session['required_shown'] = True
	for question in assessment_question_responses:
		new_dict = {'pk':question.pk}
		if question.insituassessmentquestionresponse.required:
			new_dict['display'] = "DONE **"+str(question.question)+"**"
		else:
			new_dict['display'] = str(question.question)
		#if question.insituassessmentquestionresponse.respondent == request.user:
		#	new_dict['enable_given_responses']
		to_send['question_dicts'].append(new_dict)
	if question_response.label:
		to_send['overheader'] = question_response.label
	return render(request, "ica/in_situ.html", to_send)