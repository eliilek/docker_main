from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse
import random
from django.forms.models import model_to_dict
import json
import cloudinary
import datetime
from thesis_readiness.models import *
from django.contrib.auth import get_user_model, login
from django.core import serializers
import csv
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from thesis_readiness.utils import create_csv
import django_rq
import re

# Create your views here.
def index(request):
	if request.user.is_superuser:
		assessments = Assessment.objects.all().order_by('name')
		students = get_user_model().objects.filter(assessmentinstance__isnull=False).distinct().order_by('name')
		return render(request, 'thesis_readiness/super_view_data.html', {'assessments':assessments, 'students':students})
	else:
		assessments = Assessment.objects.filter(active=True, students=request.user).order_by('name')
		return render(request, 'thesis_readiness/select.html', {'assessments':assessments})

def multi_upload(request):
	if request.user.is_superuser:
		return render(request, "thesis_readiness/multi_upload.html")
	return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})

def multi_upload_2(request):
	if request.user.is_superuser:
		return render(request, "thesis_readiness/multi_upload_2.html")
	return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})

def multi_upload_report(request):
	if request.method != "POST":
		return redirect("thesis_readiness:multi_upload")
	long_string = request.POST['questions'].replace("…", "...").replace("“", "\"").replace("”", "\"")
	questions = long_string.split("\r\n")
	new_questions = []
	deletable_questions = []
	objectives = {}
	objective_2 = None
	for question in questions:
		try:
			split_str = question.split("  ")
			if len(split_str) < 7 or len(split_str)%3 != 1:
				split_str = question.split("\t")
			if len(split_str) < 7 or len(split_str)%3 != 1:
				for del_question in deletable_questions:
					del_question.delete()
				return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 1. Please re-do this assessment."})
			new_correct_answers = []
			new_incorrect_answers = []
			new_question = Question(text=split_str[0], key=split_str[4])
			existing_filter = Question.objects.filter(text=split_str[0], key=split_str[4])
			if split_str[5] != "":
				new_question.points = float(split_str[5])
				existing_filter = existing_filter.filter(points=float(split_str[5]))
			try:
				objective = Objective.objects.get(name=split_str[1])
			except:
				objective = Objective(name=split_str[1])
				objective.save()
			try:
				objectives[objective.name] += 1
			except:
				objectives[objective.name] = 1
			existing_filter = existing_filter.filter(objectives=objective)
			if split_str[2] != "":
				try:
					objective_2 = Objective.objects.get(name=split_str[2])
				except:
					objective_2 = Objective(name=split_str[2])
					objective_2.save()
				try:
					objectives[objective_2.name] += 1
				except:
					objectives[objective_2.name] = 1
				existing_filter = existing_filter.filter(objectives=objective_2)
			if split_str[3] != "":
				try:
					image = Image.objects.get(name=split_str[3])
				except:
					for del_question in deletable_questions:
						del_question.delete()
					return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this assessment."})
				new_question.image = image
				existing_filter = existing_filter.filter(image = image)
			if split_str[6] == "y" or split_str[6] == "Y":
				new_question.select_all = True
				existing_filter = existing_filter.filter(select_all = True)
			if len(split_str) != 7:
				for i in range(7, len(split_str), 3):
					existing_answers = Answer.objects.filter(text=split_str[i])
					if split_str[i+1] != "":
						existing_answers = existing_answers.filter(image__name=split_str[i+1])
					if existing_answers.count() == 0:
						new_answer = Answer(text=split_str[i])
						if split_str[i+1] != "":
							try:
								new_answer.image = Image.objects.get(name=split_str[i+1])
							except:
								for del_question in deletable_questions:
									del_question.delete()
								return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this assessment."})
						new_answer.save()
					else:
						new_answer = existing_answers[0]
					if split_str[i+2] == "y" or split_str[i+2] == "Y":
						new_correct_answers.append(new_answer)
						existing_filter = existing_filter.filter(correct_answers=new_answer)
					elif split_str[i+2] == "n" or split_str[i+2] == "N":
						new_incorrect_answers.append(new_answer)
						existing_filter = existing_filter.filter(incorrect_answers=new_answer)
					else:
						for del_question in deletable_questions:
							del_question.delete()
					return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse because an answer wasn't labeled correct or incorrect. Please re-do this assessment."})

			if existing_filter.count() == 0:
				new_question.save()
				new_question.objectives.add(objective)
				if objective_2:
					new_question.objectives.add(objective_2)
				if len(new_correct_answers) != 0:
					new_question.correct_answers.add(*new_correct_answers)
				if len(new_incorrect_answers) != 0:
					new_question.incorrect_answers.add(*new_incorrect_answers)
				new_question.save()
				new_questions.append(new_question)
				deletable_questions.append(new_question)
			else:
				new_questions.append(existing_filter[0])
		except Exception as e:
			for del_question in deletable_questions:
				del_question.delete()
			return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 3. Please re-do this assessment.\n" + str(e)})

	try:
		new_assessment = Assessment(name=request.POST['name'])
		new_assessment.instructions = request.POST['instructions']
		new_assessment.part_instructions = request.POST['part-instructions']
		new_assessment.save()
		new_assessment.questions.add(*new_questions)
	except Exception as e:
		for del_question in deletable_questions:
			del_question.delete()
		return render(request, "thesis_readiness/plain.html", {"msg":"There was a problem saving the assessment. Please re-do this assessment. All questions have been deleted."})
	return render(request, "thesis_readiness/plain.html", {"msg":"All questions processed successfully!"})

def multi_upload_report_part_2(request):
	if request.method != "POST":
		return redirect("thesis_readiness:multi_upload_2")
	long_string = request.POST['questions'].replace("…", "...").replace("“", "\"").replace("”", "\"")
	questions = long_string.split("\r\n")
	deletable_questions = []
	for question in questions:
		try:
			split_str = question.split("  ")
			if len(split_str) < 6 or len(split_str)%3 != 0:
				split_str = question.split("\t")
			if len(split_str) < 6 or len(split_str)%3 != 0:
				for del_question in deletable_questions:
					del_question.delete()
				return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 1. Please re-do this assessment."})
			new_correct_answers = []
			new_incorrect_answers = []
			try:
				graph = Graph.objects.get(name=split_str[0])
			except:
				for del_question in deletable_questions:
					del_question.delete()
				return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse because I couldn't find that graph name. Please re-do this assessment."})
			new_question = Question(text=split_str[2], key=split_str[3])
			existing_filter = Question.objects.filter(text=split_str[2], key=split_str[3], graph=graph)
			if split_str[4] != "":
				new_question.points = float(split_str[4])
				existing_filter = existing_filter.filter(points=float(split_str[4]))
			try:
				objective = Objective.objects.get(name=split_str[1])
			except:
				objective = Objective(name=split_str[1])
				objective.save()
			existing_filter = existing_filter.filter(objectives=objective)
			if split_str[5] == "y" or split_str[5] == "Y":
				new_question.select_all = True
				existing_filter = existing_filter.filter(select_all = True)
			if len(split_str) != 6:
				for i in range(6, len(split_str), 3):
					if split_str[i] == "":
						continue
					existing_answers = Answer.objects.filter(text=split_str[i])
					if split_str[i+1] != "":
						existing_answers = existing_answers.filter(image__name=split_str[i+1])
					if existing_answers.count() == 0:
						new_answer = Answer(text=split_str[i])
						if split_str[i+1] != "":
							try:
								new_answer.image = Image.objects.get(name=split_str[i+1])
							except:
								for del_question in deletable_questions:
									del_question.delete()
								return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this assessment."})
						new_answer.save()
					else:
						new_answer = existing_answers[0]
					if split_str[i+2] == "y" or split_str[i+2] == "Y":
						new_correct_answers.append(new_answer)
						existing_filter = existing_filter.filter(correct_answers=new_answer)
					elif split_str[i+2] == "n" or split_str[i+2] == "N":
						new_incorrect_answers.append(new_answer)
						existing_filter = existing_filter.filter(incorrect_answers=new_answer)
					else:
						for del_question in deletable_questions:
							del_question.delete()
						return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse because an answer wasn't labeled correct or incorrect. Please re-do this assessment."})

			if existing_filter.count() == 0:
				new_question.save()
				new_question.objectives.add(objective)
				if len(new_correct_answers) != 0:
					new_question.correct_answers.add(*new_correct_answers)
				if len(new_incorrect_answers) != 0:
					new_question.incorrect_answers.add(*new_incorrect_answers)
				new_question.save()
				deletable_questions.append(new_question)
			else:
				new_question = existing_filter[0]
			graph.questions.add(new_question)
			graph.save()
		except Exception as e:
			for del_question in deletable_questions:
				del_question.delete()
			return render(request, "thesis_readiness/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 3. Please re-do this assessment.\n" + str(e)})
	return render(request, "thesis_readiness/plain.html", {"msg":"All questions processed successfully!"})

def take_assessment(request, assessment, question=None):
	try:
		assessment = Assessment.objects.get(pk=assessment)
	except:
		return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and not request.user in assessment.students.all():
		return render(request, 'thesis_readiness/plain.html', {'msg':"You are not authorized to view this assessment. Please contact your administrator if you believe this is an error.\nUse the above link to return to the menu."})
	try:
		assessment_instance = AssessmentInstance.objects.get(pk=request.session['instance'])
		if assessment_instance.assessment == assessment:
			if assessment.part_1:
				return next_question(assessment_instance, request, question)
			else:
				return next_graph(assessment_instance, request, question)
	except Exception as e:
		print(e)
	if AssessmentInstance.objects.filter(user=request.user, assessment=assessment, finished__isnull=True).count() == 1:
		request.session['instance'] = AssessmentInstance.objects.filter(user=request.user, assessment=assessment, finished__isnull=True)[0].pk
		instance = AssessmentInstance.objects.get(pk=request.session['instance'])
		if assessment.part_1:
			return next_question(instance, request, question)
		else:
			return next_graph(instance, request, question)
	elif AssessmentInstance.objects.filter(user=request.user, assessment=assessment, finished__isnull=True).count() > 1:
		return render(request, "thesis_readiness/plain.html", {"msg":"The database has something terribly wrong, please contact Eli."})
	#Generate new assessment
	assessment_instance = AssessmentInstance(assessment = assessment, user = request.user)
	assessment_instance.save()
	if assessment.part_1:
		questions = assessment.questions.all().order_by('id')
		for question in questions:
			new_response = AssessmentResponse(assessment_instance = assessment_instance, question = question, answer = "", earned_points = 0)
			new_response.save()
		request.session['instance'] = assessment_instance.pk
		return next_question(assessment_instance, request, None)
	else:
		used_graphs_1 = []
		used_graphs_2 = []
		for treatment_design_quantity in assessment.section_1_treatment_designs.all():
			if Graph.objects.filter(treatment_design=treatment_design_quantity.treatment_design, section_1=True).count() < treatment_design_quantity.quantity:
				assessment_instance.delete()
				return render(request, "thesis_readiness/plain.html", {"msg":"The database has something terribly wrong, please contact Eli."})
			used_graphs_1 += Graph.objects.random(treatment_design_quantity.quantity, treatment_design_quantity.treatment_design, True, exclude=[graph.id for graph in used_graphs_1])
		for treatment_design_quantity in assessment.section_2_treatment_designs.all():
			if Graph.objects.filter(treatment_design=treatment_design_quantity.treatment_design, section_1=False).count() < treatment_design_quantity.quantity:
				assessment_instance.delete()
				return render(request, "thesis_readiness/plain.html", {"msg":"The database has something terribly wrong, please contact Eli."})
			used_graphs_2 += Graph.objects.random(treatment_design_quantity.quantity, treatment_design_quantity.treatment_design, False, exclude=[graph.id for graph in used_graphs_2])
		random.shuffle(used_graphs_1)
		random.shuffle(used_graphs_2)
		final_graphs = used_graphs_1 + used_graphs_2
		for graph in final_graphs:
			for question in graph.questions.all().order_by('id'):
				new_response = AssessmentResponse(assessment_instance = assessment_instance, question = question, answer = "", earned_points=0, graph=graph)
				new_response.save()
		try:
			final_question = Question.objects.filter(objectives__name="Final Question")[0]
		except:
			assessment_instance.delete()
			return render(request, "thesis_readiness/plain.html", {"msg":"The database has something terribly wrong, please contact Eli."})
		final_response = AssessmentResponse(assessment_instance = assessment_instance, question = final_question, answer = "", earned_points=0)
		final_response.save()
		request.session['instance'] = assessment_instance.pk
		return next_graph(assessment_instance, request, None)

def instructions(request, assessment):
	try:
		assessment = Assessment.objects.get(pk=assessment)
	except:
		return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and not request.user in assessment.students.all():
		return render(request, 'thesis_readiness/plain.html', {'msg':"You are not authorized to view this assessment. Please contact your administrator if you believe this is an error.\nUse the above link to return to the menu."})
	if assessment.instructions != "":
		return render(request, "thesis_readiness/instructions.html", {'instructions':assessment.instructions, 'assessment_id':assessment.pk, 'inst_set':1})
	else:
		return redirect('thesis_readiness:part_instructions', assessment=assessment.pk)

def part_instructions(request, assessment):
	try:
		assessment = Assessment.objects.get(pk=assessment)
	except:
		return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and not request.user in assessment.students.all():
		return render(request, 'thesis_readiness/plain.html', {'msg':"You are not authorized to view this assessment. Please contact your administrator if you believe this is an error.\nUse the above link to return to the menu."})
	if assessment.part_instructions != "":
		return render(request, "thesis_readiness/instructions.html", {'instructions':assessment.part_instructions, 'assessment_id':assessment.pk, 'inst_set':2})
	else:
		return redirect('thesis_readiness:take_assessment', assessment=assessment.pk)

def next_question(assessment_instance, request, question_index):
	questions = assessment_instance.assessmentresponse_set.all().order_by('id')
	if question_index != None:
		try:
			question = questions[question_index].question
		except Exception as e:
			print(e)
			return next_question(assessment_instance, request, None)
	else:
		unanswered = assessment_instance.assessmentresponse_set.filter(answer="").order_by('id')
		question = unanswered[0].question
	to_send = {'questions':[]}
	to_send['questions'].append({'text':question.text, 'question_type':question.question_type(), 'id':question.id})
	answers = []
	for answer in question.correct_answers.all():
		answers.append(answer)
	for answer in question.incorrect_answers.all():
		answers.append(answer)
	random.shuffle(answers)
	#Currently assumes either all or no answers will have an image
	image_urls = []
	images_flag = False
	for answer in answers:
		if answer.image:
			image_urls.append(cloudinary.CloudinaryImage(answer.image.image.public_id).build_url(width=300))
			images_flag = True
		else:
			image_urls.append(None)
	to_send['questions'][0]['answers'] = answers
	if images_flag:
		to_send['questions'][0]['answer_image_urls'] = image_urls
	if question.image:
		to_send['questions'][0]['image_url'] = cloudinary.CloudinaryImage(question.image.image.public_id).build_url(width=1000)
	to_send['name'] = assessment_instance.assessment.name
	to_send['assessment_id'] = assessment_instance.assessment.id
	to_send['total_question_number'] = assessment_instance.total_questions()
	total_question_range = []
	for question in questions:
		if question.answer == "":
			total_question_range.append(len(total_question_range)+1)
		else:
			total_question_range.append("** " + str(len(total_question_range)+1) + " **")
	to_send['total_question_range'] = total_question_range
	if question_index != None:
		to_send['current_question_number'] = question_index + 1
		if questions[question_index].answer != "":
			to_send['questions'][0]['given_answer'] = questions[question_index].answer
	else:
		to_send['current_question_number'] = list(questions).index(unanswered[0]) + 1
	return render(request, 'thesis_readiness/take_assessment.html', to_send)

def next_graph(assessment_instance, request, graph_index=None):
	responses = assessment_instance.assessmentresponse_set.all().order_by('id')
	graphs = []
	for response in responses:
		if not response.graph in graphs:
			graphs.append(response.graph)
	if graph_index != None:
		try:
			graph = graphs[graph_index]
		except Exception as e:
			print(e)
			return next_graph(assessment_instance, request, None)
	else:
		graph = graphs[0]
	questions = [response.question for response in responses.filter(graph=graph).order_by('id')]
	if graph == None:
		to_send = {'questions':[]}
	else:
		to_send = {'questions':[], 'image_url':cloudinary.CloudinaryImage(graph.image.public_id).build_url(width=1000)}
	if graph_index != None:
		to_send['current_graph_number'] = graph_index + 1
	else:
		to_send['current_graph_number'] = 1
	for question in questions:
		question_dict = {'text':question.text, 'question_type':question.question_type(), 'id':question.id}
		answers = []
		for answer in question.correct_answers.all():
			answers.append(answer)
		for answer in question.incorrect_answers.all():
			answers.append(answer)
		random.shuffle(answers)
		image_urls = []
		images_flag = False
		for answer in answers:
			if answer.image:
				image_urls.append(cloudinary.CloudinaryImage(answer.image.image.public_id).build_url(width=300))
				images_flag = True
			else:
				image_urls.append(None)
		question_dict['answers'] = answers
		if images_flag:
			question_dict['answer_image_urls'] = image_urls
		if responses.get(question=question).answer != "":
			question_dict['given_answer'] = responses.get(question=question).answer
		to_send['questions'].append(question_dict)
	to_send['name'] = assessment_instance.assessment.name
	to_send['assessment_id'] = assessment_instance.assessment.id
	to_send['total_graph_number'] = len(graphs)
	total_graph_range = []
	for graph in graphs:
		answered_count = 0
		for response in responses.filter(graph=graph).order_by('id'):
			if response.answer != "":
				answered_count += 1
		if answered_count == 0:
			total_graph_range.append(len(total_graph_range)+1)
		elif answered_count == responses.filter(graph=graph).count():
			total_graph_range.append("** " + str(len(total_graph_range)+1) + " **")
		else:
			total_graph_range.append("* " + str(len(total_graph_range)+1) + " *")
	to_send['total_graph_range'] = total_graph_range
	return render(request, 'thesis_readiness/take_assessment.html', to_send)

def submit_response(request, assessment):
	try:
		assessment = Assessment.objects.get(pk=assessment)
	except:
		return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})
	if 'instance' in request.session:
		assessment_instance = AssessmentInstance.objects.get(pk=request.session['instance'])
		if request.method == "POST":
			print(request.POST)
			my_re = re.compile(r"answer(\d)+")
			for key in request.POST:
				match = my_re.match(key)
				if match:
					current_response = assessment_instance.assessmentresponse_set.get(question__id=re.sub("answer", "", match.group(0)))
					if request.POST.getlist(key) == []:
						current_response.answer = str(request.POST[key])
					else:
						current_response.answer = ",".join(request.POST.getlist(key))
					#Grade Multiple Choice Questions
					if current_response.correct():
						current_response.earned_points = current_response.question.points
					current_response.save()
			unanswered_questions = assessment_instance.assessmentresponse_set.filter(answer="").order_by('id')
			if unanswered_questions.count() == 0:
				request.session.pop('instance')
				assessment_instance.finished = timezone.now()
				assessment_instance.save()
				try:
					assessment_instance.assessment.students.remove(request.user)
					assessment_instance.assessment.save()
				except:
					return render(request, 'thesis_readiness/plain.html', {'msg':"You're all done, but there was an error with the unassignment. Please let your admin know."})
				#TODO get some better instructions
				return render(request, 'thesis_readiness/plain.html', {'msg':"You're all done!"})
		else:
			return redirect('thesis_readiness:take_assessment', assessment=assessment.id)
		if "next_question" in request.POST:
			next_question = int(request.POST["next_question"])
		else:
			next_question = int(request.POST["question_number"])
		return redirect('thesis_readiness:take_assessment', assessment=assessment.id, question=next_question)
	return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})


#def submit_response(request, assessment):
#	try:
#		assessment = Assessment.objects.get(pk=assessment)
#	except:
#		return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})
#	if 'instance' in request.session:
#		#assessment in progress
#		assessment_instance = AssessmentInstance.objects.get(pk=request.session['instance'])
#		#If POST, record an answer, if done redirect to view results for instance
#		if request.method == "POST":
#			questions = assessment_instance.assessmentresponse_set.all().order_by('id')
#			current_question = questions[int(request.POST['question_number'])-1]
#			current_question.answer = str(request.POST['answer'])
#			#Grade multiple choice questions
#			if current_question.correct():
#				current_question.earned_points = current_question.question.points
#			current_question.save()
#			unanswered_questions = assessment_instance.assessmentresponse_set.filter(answer="").order_by('id')
#			if unanswered_questions.count() == 0:
#				request.session.pop('instance')
#				assessment_instance.finished = timezone.now()
#				assessment_instance.save()
#				try:
#					assessment_instance.assessment.students.remove(request.user)
#					assessment_instance.assessment.save()
#				except:
#					return render(request, 'thesis_readiness/plain.html', {'msg':"You're all done, but there was an error with the unassignment. Please let your admin know."})
#				#TODO get some better instructions
#				return render(request, 'thesis_readiness/plain.html', {'msg':"You're all done!"})
#		else:
#			return redirect('thesis_readiness:take_assessment', assessment=assessment.id)
#		if "next_question" in request.POST:
#			next_question = int(request.POST["next_question"])
#		else:
#			next_question = int(request.POST["question_number"])
#		return redirect('thesis_readiness:take_assessment', assessment=assessment.id, question=next_question)
#	return render(request, 'thesis_readiness/plain.html', {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})

def view_instance_data(request, instance):
	try:
		instance = AssessmentInstance.objects.get(pk=instance)
	except:
		return render(request, "thesis_readiness/plain.html", {'msg':"I couldn't find the assessment instance you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser:
		return render(request, 'thesis_readiness/plain.html', {'msg':"You are not authorized to view this assessment. Please contact your administrator if you believe this is an error.\nUse the above link to return to the menu."})
	
	responses = []
	for response in instance.assessmentresponse_set.all().order_by('pk'):
		new_dict = {'objective_str':",".join([objective.name for objective in response.question.objectives.all()]), 'question':response.question.text, 'key':response.question.key, 'pk':response.pk, 'score':response.earned_points, 'max_score':response.question.points, 'correct':response.correct(), 'given_answer':response.answer}
		if response.question.correct_string() != "":
			new_dict['correct_string'] = response.question.correct_string()
		if response.question.incorrect_string() != "":
			new_dict['incorrect_string'] = response.question.incorrect_string()
		if response.question.image:
			new_dict['image_url'] = cloudinary.CloudinaryImage(response.question.image.image.public_id).build_url()
		if response.graph:
			new_dict['image_url'] = cloudinary.CloudinaryImage(response.graph.image.public_id).build_url()
		responses.append(new_dict)
	##responses.sort(key=lambda x : x['objective_str'])
	return render(request, "thesis_readiness/view_instance.html", {"responses":responses})

def score(request):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	if not request.method == "POST":
		return redirect("thesis_readiness:index")
	for item in request.POST.items():
		try:
			response = AssessmentResponse.objects.get(pk=int(item[0]))
			response.earned_points = float(item[1])
			response.save()
		except Exception as e:
			print(e)
	return HttpResponse("Success")

def key(request):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	if not request.method == "POST":
		return redirect("thesis_readiness:index")
	for item in request.POST.items():
		try:
			response = AssessmentResponse.objects.get(pk=int(item[0]))
			response.question.key = item[1]
			response.question.save()
		except Exception as e:
			print(e)
	return HttpResponse("Success")

def view_assessment_data(request, assessment):
	try:
		assessment = Assessment.objects.get(pk=assessment)
	except:
		return render(request, "thesis_readiness/plain.html", {'msg':"I couldn't find the assessment you're looking for.\nUse the above link to return to the menu."})
	if request.user.is_superuser:
		instances = AssessmentInstance.objects.filter(assessment=assessment).order_by('-created')
	else:
		instances = AssessmentInstance.objects.filter(assessment=assessment, user=request.user).order_by('-created')
	to_send = []
	for instance in instances:
		to_append = {"pk":instance.pk, "created":instance.created, "score":instance.score(), "total_score":instance.total_score()}
		if request.user.is_superuser:
			to_append["student"] = instance.user.name
		to_send.append(to_append)
	paginator = Paginator(to_send, 25)
	paginated_to_send = paginator.get_page(request.GET.get('page', 1))
	return render(request, "thesis_readiness/view_assessment.html", {"instances":paginated_to_send, "assessment":assessment.name})

def delete_assessment_instance(request, instance, return_address):
	try:
		instance = AssessmentInstance.objects.get(pk=instance)
	except:
		return render(request, "thesis_readiness/plain.html", {'msg':"I couldn't find the assessment instance you're looking for.\nUse the above link to return to the menu."})
	assessment = instance.assessment
	user = instance.user
	instance.delete()
	if return_address == "user":
		return redirect("thesis_readiness:view_student_data", user.pk)
	return redirect("thesis_readiness:view_assessment_data", assessment.pk)

def view_student_data(request, student):
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "thesis_readiness/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	instances = AssessmentInstance.objects.filter(user=student).order_by('created')
	to_send = []
	for instance in instances:
		to_send.append({"pk":instance.pk, "created":instance.created, "assessment":instance.assessment.name, "score":instance.score(), "total_score":instance.total_score()})
	paginator = Paginator(to_send, 25)
	paginated_to_send = paginator.get_page(request.GET.get('page', 1))
	return render(request, "thesis_readiness/view_student.html", {"instances":paginated_to_send, "student":student.name})

def download(request):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	assessments = Assessment.objects.all()
	return render(request, 'thesis_readiness/select.html', {'assessments':assessments, 'download':True})

def download_student_select(request):
	return HttpResponse("Not implemented yet")

def download_assessment(request, assessment):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		assessment = Assessment.objects.get(pk=assessment)
	except:
		return render(request, "thesis_readiness/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})

	args_dict = {}
	args_dict['filename'] = str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__test_' + assessment.name.replace("/", "|") + '_data.csv'
	args_dict['assessment_pk'] = assessment.pk

	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()
	return redirect("thesis_readiness:queued")

def queued(request):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	files = File.objects.all()
	args = []
	for file in files:
		#Check if the file exists and is finished
		args.append({'name':file.name, 'created':file.created, 'ready':default_storage.exists(file.name)})
	return render(request, "thesis_readiness/queued.html", {"files":args})

def retrieve(request, filename):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "thesis_readiness/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	if not default_storage.exists(filename):
		return redirect("thesis_readiness:queued")

	retrieved_file = default_storage.open(filename, 'r')

	response = HttpResponse(retrieved_file, content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=' + filename.replace(" ", "_").replace(",", "_")

	return response

def delete(request, filename):
	if not request.user.is_superuser:
		return render(request, "thesis_readiness/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "thesis_readiness/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	default_storage.delete(filename)
	file.delete()
	return redirect("thesis_readiness:queued")