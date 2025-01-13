from django.shortcuts import render, redirect, HttpResponse
import random
from exams.models import *
from django.contrib.auth import get_user_model
import cloudinary
import datetime
from django.utils import timezone
import dateutil.parser
import csv
from django.core.files.storage import default_storage
from exams.utils import create_csv
import django_rq
from django.core.paginator import Paginator

# Create your views here.
def index(request):
	if request.user.is_superuser:
		tests = Test.objects.all().order_by('name')
		students = get_user_model().objects.filter(testinstance__isnull=False).distinct().order_by('name')
		return render(request, 'exams/super_view_data.html', {'tests':tests, 'students':students})
	else:
		tests = Test.objects.filter(active=True).order_by('name')
		return render(request, 'exams/select.html', {'tests':tests})

def test_action(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'exams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	return render(request, 'exams/test_action.html', {'test':test})

def submit_response(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'exams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if 'instance' in request.session:
		#Test in progress
		test_instance = TestInstance.objects.get(pk=request.session['instance'])
		#If POST, record an answer, if done redirect to view results for instance
		if request.method == "POST":
			questions = test_instance.testresponse_set.all().order_by('id')
			current_question = questions[int(request.POST['question_number'])-1]
			current_question.answer = str(request.POST['answer'])
			current_question.save()
			unanswered_questions = test_instance.testresponse_set.filter(answer="").order_by('id')
			try:
				request.session.pop('question_generated')
			except:
				pass
			if test.time_limit:
				additional_time = datetime.timedelta(milliseconds = int(request.POST['milliseconds']))
				old_time = test_instance.elapsed_time
				#request.session['elapsed'] = str(old_time + additional_time).split(".")[0]
				test_instance.elapsed_time = old_time + additional_time
				test_instance.save()
			if len(unanswered_questions) == 0:
				request.session.pop('instance')
				test_instance.finished = timezone.now()
				test_instance.save()
				return redirect('exams:view_instance_data', instance=test_instance.id)
		else:
			if test.time_limit != None and 'question_generated' in request.session:
				#old_split = request.session['elapsed'].split(":")
				old_time = test_instance.elapsed_time
				test_instance.elapsed_time = old_time + (timezone.now() - dateutil.parser.parse(request.session['question_generated']))
				test_instance.save()
			return redirect('exams:take_test', test=test.id)
		if 'timed_out' in request.POST:
			return test_timeout(request, test.pk)
		elif 'next_question' in request.POST:
			next_question = int(request.POST['next_question'])
		else:
			next_question = int(request.POST['question_number'])
		return redirect('exams:take_test', test=test.id, question=next_question)
	return redirect('exams:index')

def take_test(request, test, question=None):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'exams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if 'instance' in request.session:
		try:
			test_instance = TestInstance.objects.get(pk=request.session['instance'])
		except Exception as e:
			print(e)
		if test_instance.test == test:
			if request.session.get("question_generated", False) and test.time_limit != None:
				#old_split = request.session['elapsed'].split(":")
				old_time = test_instance.elapsed_time
				#request.session['elapsed'] = str(old_time + datetime.timedelta(seconds=(((timezone.now() - dateutil.parser.parse(request.session['question_generated'])) // datetime.timedelta(seconds=1)))))
				test_instance.elapsed_time = old_time + datetime.timedelta(seconds=((timezone.now() - dateutil.parser.parse(request.session['question_generated']))))
				test_instance.save()
			return next_question(test_instance, request, question)
	elif test.multiple_sittings and TestInstance.objects.filter(test=test, user=request.user, finished=None).count() != 0:
		instance = TestInstance.objects.filter(test=test, user=request.user, finished=None)[0]
		request.session['instance'] = instance.pk
		return next_question(instance, request, question)
	#Generate new test
	questions = []
	for section in test.testsection_set.all():
		if section.objective:
			question_pool = Question.objects.filter(objectives=section.objective, active=True).exclude(pk__in=[q.pk for q in questions])
		elif section.content_area:
			objective_set = Objective.objects.filter(content_area=section.content_area)
			question_pool = Question.objects.filter(objectives__in=objective_set, active=True).distinct().exclude(pk__in=[q.pk for q in questions])
		else:
			return render(request, 'exams/plain.html', {'msg':"This test has a malformed section. Please contact your administrator."})
		try:
			questions += random.sample(list(question_pool), section.questions)
		except:
			return render(request, 'exams/plain.html', {'msg':"Section " + str(section.pk) + " does not have enough questions associated with it. Please contact your administrator."})
	random.shuffle(questions)
	test_instance = TestInstance(test = test, user = request.user)
	test_instance.save()
	for question in questions:
		new_response = TestResponse(test_instance = test_instance, question = question, answer = "")
		new_response.save()
	request.session['instance'] = test_instance.pk
	if test.time_limit != None:
		#request.session['elapsed'] = "00:00:00"
		request.session['question_generated'] = None
	if test.instructions:
		#render instructions splash
		return render(request, "exams/test_instructions.html", {'instructions':test.instructions, 'test_id':test.pk})
	else:
		return next_question(test_instance, request, None)

def next_question(test_instance, request, question_index):
	request.session['question_generated'] = timezone.now().isoformat()
	questions = test_instance.testresponse_set.all().order_by('id')
	if question_index != None:
		try:
			question = questions[question_index].question
		except Exception as e:
			print(e)
			return next_question(test_instance, request, None)
	else:
		unanswered = test_instance.testresponse_set.filter(answer="").order_by('id')
		for response in unanswered:
			question = unanswered[0].question
	to_send = {'text':question.text}
	if question.correct_answer_image:
		temp = [question.correct_answer, question.incorrect_answer_1, question.incorrect_answer_2, question.incorrect_answer_3]
		a1 = []
		for answer in temp:
			if answer != "":
				a1.append(answer)
		a2 = [question.correct_answer_image, question.incorrect_answer_1_image, question.incorrect_answer_2_image, question.incorrect_answer_3_image]
		a2 = a2[0:len(a1)]
		zipped = list(zip(a1, a2))
		random.shuffle(zipped)
		answers, images = list(zip(*zipped))
		image_urls = []
		for image in images:
			image_urls.append(cloudinary.CloudinaryImage(image.image.public_id).build_url(width=300))
		to_send['answer_image_urls'] = image_urls
	else:
		temp = [question.correct_answer, question.incorrect_answer_1, question.incorrect_answer_2, question.incorrect_answer_3]
		answers = []
		for answer in temp:
			if answer != "":
				answers.append(answer)
		random.shuffle(answers)
	to_send['answers'] = answers
	if question.image:
		to_send['image_url'] = cloudinary.CloudinaryImage(question.image.image.public_id).build_url(width=500)
	to_send['name'] = test_instance.test.name
	to_send['test_id'] = test_instance.test.id
	to_send['total_question_number'] = test_instance.total_questions()
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
			to_send['given_answer'] = questions[question_index].answer
	else:
		to_send['current_question_number'] = list(questions).index(unanswered[0]) + 1
	if test_instance.test.time_limit != None:
		#if request.session.get('elapsed', datetime.timedelta(0)) == datetime.timedelta(0):
		if test_instance.elapsed_time == datetime.timedelta(0):
			to_send['elapsed_time'] = "00:00:00"
		else:
			to_send['elapsed_time'] = str(test_instance.elapsed_time)
		to_send['total_time'] = "0" + str(test_instance.test.time_limit)
	return render(request, 'exams/take_test.html', to_send)

def test_timeout(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'exams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if 'instance' in request.session:
		test_instance = TestInstance.objects.get(pk=request.session['instance'])
		for response in test_instance.testresponse_set.filter(answer=""):
			response.answer = "Timed out"
			response.save()
		test_instance.finished = timezone.now()
		test_instance.save()
		try:
			request.session.pop('instance')
			request.session.pop('question_generated')
		except:
			pass
		return redirect('exams:view_instance_data', instance=test_instance.id)
	return redirect('exams:index')

def multi_upload(request):
	if request.user.is_superuser:
		return render(request, "exams/multi_upload.html")
	return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})

def multi_upload_report(request):
	if request.method != "POST":
		return redirect("exams:multi_upload")
	long_string = request.POST['questions']
	questions = long_string.split("\r\n")
	errors = ""
	for question in questions:
		try:
			split_str = question.split("  ")
			if len(split_str) < 13:
				split_str = question.split("\t")
			if len(split_str) < 13:
				errors += "The line \"" + question + "\" didn't parse. This question was not included.\n"
				continue
			new_question = Question(text = split_str[0], correct_answer = split_str[1], incorrect_answer_1 = split_str[2], incorrect_answer_2 = split_str[3], incorrect_answer_3 = split_str[4])
			existing_filter = Question.objects.filter(text = new_question.text, correct_answer = new_question.correct_answer, incorrect_answer_1 = new_question.incorrect_answer_1, incorrect_answer_2 = new_question.incorrect_answer_2, incorrect_answer_3 = new_question.incorrect_answer_3)
			if split_str[8] != "":
				try:
					image = Image.objects.get(name=split_str[8])
				except:
					errors += "The line \"" + question + "\" had an Image name we couldn't find. This question was not included.\n"
					continue
				new_question.image = image
				existing_filter = existing_filter.filter(image = image)
			if split_str[9] != "":
				try:
					image = Image.objects.get(name=split_str[9])
				except:
					errors += "The line \"" + question + "\" had an Image name we couldn't find. This question was not included.\n"
					continue
				new_question.correct_answer_image = image
				existing_filter = existing_filter.filter(correct_answer_image = image)
			if split_str[10] != "":
				try:
					image = Image.objects.get(name=split_str[10])
				except:
					errors += "The line \"" + question + "\" had an Image name we couldn't find. This question was not included.\n"
					continue
				new_question.incorrect_answer_1_image = image
				existing_filter = existing_filter.filter(incorrect_answer_1_image = image)
			if split_str[11] != "":
				try:
					image = Image.objects.get(name=split_str[11])
				except:
					errors += "The line \"" + question + "\" had an Image name we couldn't find. This question was not included.\n"
					continue
				new_question.incorrect_answer_2_image = image
				existing_filter = existing_filter.filter(incorrect_answer_2_image = image)
			if split_str[12] != "":
				try:
					image = Image.objects.get(name=split_str[12])
				except:
					errors += "The line \"" + question + "\" had an Image name we couldn't find. This question was not included.\n"
					continue
				new_question.incorrect_answer_3_image = image
				existing_filter = existing_filter.filter(incorrect_answer_3_image = image)
			if len(split_str) == 14:
				new_question.feedback = split_str[13]
				existing_filter = existing_filter.filter(feedback = split_str[13])
			if existing_filter.count() == 0:
				new_question.save()
			else:
				continue
			try:
				content_area = ContentArea.objects.get(name=split_str[5])
			except:
				content_area = ContentArea(name=split_str[5])
				content_area.save()
			try:
				objective = Objective.objects.get(name=split_str[6])
				if objective.content_area == None:
					objective.content_area = content_area
					objective.save()
			except:
				objective = Objective(name=split_str[6], content_area=content_area)
				objective.save()
			new_question.objectives.add(objective)
			if split_str[7] != "":
				try:
					objective_2 = Objective.objects.get(name=split_str[7])
				except:
					objective_2 = Objective(name=split_str[7], content_area=None)
					objective_2.save()
				new_question.objectives.add(objective_2)
			new_question.save()
		except Exception as e:
			errors += "The line \"" + question + "\" didn't parse. This question was not included.\n"
			print(e)
			continue
	if errors == "":
		errors = "All questions processed successfully!"
	return render(request, "exams/plain.html", {"msg":errors})

def view_instance_data(request, instance):
	try:
		instance = TestInstance.objects.get(pk=instance)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the test instance you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and instance.finished == None:
		return render(request, "exams/plain.html", {'msg':"You are not authorized to view tests which were not completed.\nUse the above link to return to the menu."})
	responses = []
	for response in instance.testresponse_set.all():
		responses.append({'objective_str':",".join([objective.name for objective in response.question.objectives.all()]), 'question':response.question.text, 'correct_answer':response.question.correct_answer, 'given_answer':response.answer, 'correct':response.correct(), 'incorrect_answer_1':response.question.incorrect_answer_1, 'incorrect_answer_2':response.question.incorrect_answer_2, 'incorrect_answer_3':response.question.incorrect_answer_3, 'feedback':response.get_feedback()})
		if response.question.image:
			responses[-1]['question_image_url'] = cloudinary.CloudinaryImage(response.question.image.image.public_id).build_url()
		if response.question.correct_answer_image:
			responses[-1]['correct_answer_image_url'] = cloudinary.CloudinaryImage(response.question.correct_answer_image.image.public_id).build_url()
		if response.question.incorrect_answer_1_image:
			responses[-1]['incorrect_answer_1_image_url'] = cloudinary.CloudinaryImage(response.question.incorrect_answer_1_image.image.public_id).build_url()
		if response.question.incorrect_answer_2_image:
			responses[-1]['incorrect_answer_2_image_url'] = cloudinary.CloudinaryImage(response.question.incorrect_answer_2_image.image.public_id).build_url()
		if response.question.incorrect_answer_3_image:
			responses[-1]['incorrect_answer_3_image_url'] = cloudinary.CloudinaryImage(response.question.incorrect_answer_3_image.image.public_id).build_url()
	responses.sort(key=lambda x : x['objective_str'])
	return render(request, "exams/view_instance.html", {"responses":responses})

def view_test_data(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if request.user.is_superuser:
		instances = TestInstance.objects.filter(test=test).order_by('-created')
	else:
		instances = TestInstance.objects.filter(test=test, user=request.user, finished__isnull=False).order_by('-created')
	paginator = Paginator(instances, 25)
	page = paginator.get_page(request.GET.get('page', 1))
	clean_instances = []
	for instance in page:
		new_instance = {"pk":instance.pk, "created":instance.created, "correct":instance.score(), "incorrect":instance.total_questions()-instance.score()}
		if request.user.is_superuser:
			new_instance["student"] = instance.user.name
		clean_instances.append(new_instance)
	page.object_list = clean_instances
	return render(request, "exams/view_test.html", {"instances":page, "super":request.user.is_superuser, "test":test.name})

def view_student_data(request, student):
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	instances = TestInstance.objects.filter(user=student).order_by('created')
	paginator = Paginator(instances, 25)
	page = paginator.get_page(request.GET.get('page', 1))
	clean_instances = []
	for instance in page:
		clean_instances.append({"pk":instance.pk, "created":instance.created, "test":instance.test.name, "correct":instance.score(), "incorrect":instance.total_questions()-instance.score()})
	page.object_list = clean_instances
	return render(request, "exams/view_student.html", {"instances":page, "student":student.name})

def download_student_select(request):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	participants = [user for user in get_user_model().objects.all() if not user.is_superuser]
	return render(request, 'exams/download_select.html', {'participants':participants})

def download_student(request, student):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	tests = Test.objects.filter(testinstance__user=student).distinct()
	return render(request, 'exams/download_test.html', {'tests':tests, 'student':student.pk})

def download_student_test(request, student, test):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	args_dict = {}
	args_dict['student_pk'] = student.pk
	args_dict['test_pk'] = test.pk
	args_dict['filename'] = str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__student_' + student.name + "_test_" + test.name.replace("/", "|") + "_responses.csv"
	
	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()
	return redirect("exams:queued")

def download(request):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	tests = Test.objects.all()
	return render(request, 'exams/select.html', {'tests':tests, 'download':True})

def download_test(request, test):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})

	args_dict = {}
	args_dict['filename'] = str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__test_' + test.name.replace("/", "|") + '_data.csv'
	args_dict['test_pk'] = test.pk

	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()
	return redirect("exams:queued")

def delete_test_instance(request, instance, return_address):
	try:
		instance = TestInstance.objects.get(pk=instance)
	except:
		return render(request, "exams/plain.html", {'msg':"I couldn't find the test instance you're looking for.\nUse the above link to return to the menu."})
	test = instance.test
	user = instance.user
	instance.delete()
	if return_address == "user":
		return redirect("exams:view_student_data", user.pk)
	return redirect("exams:view_test_data", test.pk)

def queued(request):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	files = File.objects.all()
	args = []
	for file in files:
		#Check if the file exists and is finished
		args.append({'name':file.name, 'created':file.created, 'ready':default_storage.exists(file.name)})
	return render(request, "exams/queued.html", {"files":args})

def retrieve(request, filename):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "exams/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	if not default_storage.exists(filename):
		return redirect("exams:queued")

	retrieved_file = default_storage.open(filename, 'r')

	response = HttpResponse(retrieved_file, content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=' + filename.replace(" ", "_").replace(",", "_")

	return response

def delete(request, filename):
	if not request.user.is_superuser:
		return render(request, "exams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "exams/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	default_storage.delete(filename)
	file.delete()
	return redirect("exams:queued")