from django.shortcuts import render, redirect, HttpResponse
import random
from realexams.models import *
from django.contrib.auth import get_user_model
import cloudinary
import datetime
from django.utils import timezone
import dateutil.parser
import unicodecsv as csv
from django.core.files.storage import default_storage
from realexams.utils import create_csv
import django_rq
from django.core.paginator import Paginator

# Create your views here.
def index(request):
	if request.user.is_superuser:
		tests = Test.objects.all().order_by('name')
		students = get_user_model().objects.filter(realinstance__isnull=False).distinct().order_by('name')
		return render(request, 'realexams/super_view_data.html', {'tests':tests, 'students':students})
	else:
		feedback_tests = Test.objects.filter(testinstance__user=request.user, testinstance__feedback_released=True).distinct()
		tests = Test.objects.filter(active=True, students=request.user).union(feedback_tests).order_by('name')
		return render(request, 'realexams/select.html', {'tests':tests})

def test_action(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'realexams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	return render(request, 'realexams/test_action.html', {'test':test})

def submit_response(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'realexams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if 'instance' in request.session:
		#Test in progress
		test_instance = TestInstance.objects.get(pk=request.session['instance'])
		#If POST, record an answer, if done redirect to view results for instance
		if request.method == "POST":
			questions = test_instance.testresponse_set.all().order_by('id')
			current_question = questions[int(request.POST['question_number'])-1]
			current_question.answer = str(request.POST['answer'])
			#Grade multiple choice questions
			if current_question.correct():
				current_question.earned_points = current_question.question.points
			else:
				current_question.earned_points = 0
			current_question.save()
			unanswered_questions = test_instance.testresponse_set.filter(answer="").order_by('id')
			try:
				request.session.pop('question_generated')
			except:
				pass
			if test.time_limit:
				additional_time = datetime.timedelta(milliseconds = int(request.POST['milliseconds']))
				old_split = request.session['elapsed'].split(":")
				old_time = datetime.timedelta(hours = int(old_split[0]), minutes = int(old_split[1]), seconds = int(old_split[2].split(".")[0]))
				request.session['elapsed'] = str(old_time + additional_time).split(".")[0]
			if unanswered_questions.count() == 0:
				request.session.pop('instance')
				try:
					request.session.pop('elapsed')
				except:
					pass
				test_instance.finished = timezone.now()
				test_instance.save()
				if not test.retake:
					test.students.remove(request.user)
					test.save()
				return redirect('realexams:view_instance_data', instance=test_instance.id)
		else:
			if test.time_limit != None:
				old_split = request.session['elapsed'].split(":")
				old_time = datetime.timedelta(hours = int(old_split[0]), minutes=int(old_split[1]), seconds = int(old_split[2].split(".")[0]))
				request.session['elapsed'] = str(old_time + (timezone.now() - dateutil.parser.parse(request.session['question_generated'])))
			return redirect('realexams:take_test', test=test.id)
		if "timed_out" in request.POST:
			return test_timeout(request, test.pk)
		elif "next_question" in request.POST:
			next_question = int(request.POST["next_question"])
		else:
			next_question = int(request.POST["question_number"])
		return redirect('realexams:take_test', test=test.id, question=next_question)
	return render(request, 'realexams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})

def reenter(request, instance):
	try:
		instance = TestInstance.objects.get(pk=instance)
	except:
		return render(request, 'realexams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and not request.user == instance.user:
		return render(request, 'realexams/plain.html', {'msg':"You are not authorized to view this test. Please contact your administrator if you believe this is an error.\nUse the above link to return to the menu."})
	request.session['instance'] = instance.pk
	if instance.test.time_limit != None:
		request.session['elapsed'] = "00:00:00"
		request.session['question_generated'] = None
	return next_question(instance, request, None)

def take_test(request, test, question=None):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'realexams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and not request.user in test.students.all():
		return render(request, 'realexams/plain.html', {'msg':"You are not authorized to take this test. Please contact your administrator if you believe this is an error.\nUse the above link to return to the menu."})
	try:
		if 'instance' in request.session and TestInstance.objects.get(pk=request.session['instance']).test == test:
			if request.session.get("question_generated", False) and test.time_limit != None:
				old_split = request.session['elapsed'].split(":")
				old_time = datetime.timedelta(hours = int(old_split[0]), minutes=int(old_split[1]), seconds = int(old_split[2].split(".")[0]))
				request.session['elapsed'] = str(old_time + datetime.timedelta(seconds=(((timezone.now() - dateutil.parser.parse(request.session['question_generated'])) // datetime.timedelta(seconds=1)))))
			return next_question(TestInstance.objects.get(pk=request.session['instance']), request, question)
		elif test.multiple_sittings and TestInstance.objects.filter(test=test, user=request.user, finished=None).count() != 0:
			instance = TestInstance.objects.filter(test=test, user=request.user, finished=None)[0]
			request.session['instance'] = instance.pk
			return next_question(instance, request, question)
	except Exception as e:
		print(e)
	#Generate new test
	questions = test.questions.all().order_by('id')
	if questions.count() == 0:
		questions = [order.question for order in TestQuestionOrdering.objects.filter(test=test).order_by('ordering')]
	test_instance = TestInstance(test = test, user = request.user)
	if test.auto_release_feedback:
		test_instance.feedback_released = True
	test_instance.save()
	for question in questions:
		new_response = TestResponse(test_instance = test_instance, question = question, answer = "", earned_points=0)
		new_response.save()
	request.session['instance'] = test_instance.pk
	if test.time_limit != None:
		request.session['elapsed'] = "00:00:00"
		request.session['question_generated'] = None
	if test.instructions:
		#render instructions splash
		return render(request, "realexams/test_instructions.html", {'instructions':test.instructions, 'test_id':test.pk})
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
		question = unanswered[0].question
	to_send = {'text':question.text}
	to_send['short_answer'] = question.short_answer()
	if not question.short_answer():
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
	try:
		if request.session['elapsed'] == datetime.timedelta(0):
			to_send['elapsed_time'] = "00:00:00"
		else:
			to_send['elapsed_time'] = str(request.session['elapsed'])
		to_send['total_time'] = "0" + str(test_instance.test.time_limit)
	except:
		pass
	return render(request, 'realexams/take_test.html', to_send)

def test_timeout(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, 'realexams/plain.html', {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if 'instance' in request.session:
		test_instance = TestInstance.objects.get(pk=request.session['instance'])
		for response in test_instance.testresponse_set.filter(answer=""):
			response.answer = "Timed out"
			response.save()
		request.session.pop('instance')
		try:
			request.session.pop('elapsed')
		except:
			pass
		try:
			request.session.pop('question_generated')
		except:
			pass
		return redirect('realexams:view_instance_data', instance=test_instance.id)
	return redirect('realexams:index')

def multi_upload(request):
	if request.user.is_superuser:
		return render(request, "realexams/multi_upload.html")
	return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})

def multi_upload_report(request):
	if request.method != "POST":
		return redirect("realexams:multi_upload")
	long_string = request.POST['questions']
	questions = long_string.split("\r\n")
	deletable_questions = []
	ordering = 1
	errors = ""
	try:
		if request.POST.get('time_limit', False):
			new_test = Test(name=request.POST['name'], time_limit=request.POST['time_limit'])
		else:
			new_test = Test(name=request.POST['name'])
		if request.POST.get('autorelease', False):
			new_test.auto_release_feedback = True
		new_test.save()
	except Exception as e:
		for del_question in deletable_questions:
			del_question.delete()
		return render(request, "realexams/plain.html", {"msg":"There was a problem saving the test. Please re-do this test. All questions have been deleted."})
	for question in questions:
		try:
			split_str = question.split("  ")
			if len(split_str) < 13:
				split_str = question.split("\t")
			if len(split_str) < 13:
				for del_question in deletable_questions:
					del_question.delete()
				return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 1. Please re-do this test."})
			new_question = Question(text = split_str[0], correct_answer = split_str[1], incorrect_answer_1 = split_str[2], incorrect_answer_2 = split_str[3], incorrect_answer_3 = split_str[4])
			existing_filter = Question.objects.filter(text = new_question.text, correct_answer = new_question.correct_answer, incorrect_answer_1 = new_question.incorrect_answer_1, incorrect_answer_2 = new_question.incorrect_answer_2, incorrect_answer_3 = new_question.incorrect_answer_3)
			if split_str[8] != "":
				try:
					image = Image.objects.get(name=split_str[8])
				except:
					for del_question in deletable_questions:
						del_question.delete()
					return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this test."})
				new_question.image = image
				existing_filter = existing_filter.filter(image = image)
			if split_str[9] != "":
				try:
					image = Image.objects.get(name=split_str[9])
				except:
					for del_question in deletable_questions:
						del_question.delete()
					return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this test."})
				new_question.correct_answer_image = image
				existing_filter = existing_filter.filter(correct_answer_image = image)
			if split_str[10] != "":
				try:
					image = Image.objects.get(name=split_str[10])
				except:
					for del_question in deletable_questions:
						del_question.delete()
					return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this test."})
				new_question.incorrect_answer_1_image = image
				existing_filter = existing_filter.filter(incorrect_answer_1_image = image)
			if split_str[11] != "":
				try:
					image = Image.objects.get(name=split_str[11])
				except:
					for del_question in deletable_questions:
						del_question.delete()
					return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this test."})
				new_question.incorrect_answer_2_image = image
				existing_filter = existing_filter.filter(incorrect_answer_2_image = image)
			if split_str[12] != "":
				try:
					image = Image.objects.get(name=split_str[12])
				except:
					for del_question in deletable_questions:
						del_question.delete()
					return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 2. Please re-do this test."})
				new_question.incorrect_answer_3_image = image
				existing_filter = existing_filter.filter(incorrect_answer_3_image = image)
			if len(split_str) >= 14:
				new_question.feedback = split_str[13]
				existing_filter = existing_filter.filter(feedback = split_str[13])
			if len(split_str) >= 15:
				new_question.points = split_str[14]
				existing_filter = existing_filter.filter(points = float(split_str[14]))	
			if existing_filter.count() == 0:
				new_question.save()
				new_ordering = TestQuestionOrdering(question=new_question, test=new_test, ordering=ordering)
				new_ordering.save()
				ordering += 1
				deletable_questions.append(new_question)
			elif existing_filter.count() == 1:
				new_ordering = TestQuestionOrdering(question=existing_filter[0], test=new_test, ordering=ordering)
				new_ordering.save()
				ordering += 1
				new_question = existing_filter[0]
			else:
				for del_question in deletable_questions:
					del_question.delete()
				return render(request, "realexams/plain.html", {"msg":"The database has something terribly wrong, please call Eli before uploading any more questions."})
			try:
				content_area = ContentArea.objects.get(name=split_str[5])
			except:
				content_area = ContentArea(name=split_str[5])
				content_area.save()
			try:
				objective = Objective.objects.get(name=split_str[6])
			except:
				objective = Objective(name=split_str[6], content_area=content_area)
				objective.save()
			new_question.objectives.add(objective)
			if split_str[7] != "":
				try:
					objective_2 = Objective.objects.get(name=split_str[7])
				except:
					objective_2 = Objective(name=split_str[7], content_area=content_area)
					objective_2.save()
				new_question.objectives.add(objective_2)
				new_question.save()
		except Exception as e:
			for del_question in deletable_questions:
				del_question.delete()
			return render(request, "realexams/plain.html", {"msg":"The line \"" + question + "\" didn't parse code 3. Please re-do this test.\n" + str(e)})
	return render(request, "realexams/plain.html", {"msg":"All questions processed successfully!"})

def view_instance_data(request, instance):
	try:
		instance = TestInstance.objects.get(pk=instance)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the test instance you're looking for.\nUse the above link to return to the menu."})
	if not request.user.is_superuser and not instance.feedback_released:
		return render(request, "realexams/plain.html", {'msg':"The instance you're looking for hasn't had feedback released yet.\nUse the above link to return to the menu."})
	responses = []
	for response in instance.testresponse_set.all().order_by('pk'):
		responses.append({'objective_str':",".join([objective.name for objective in response.question.objectives.all()]), 'question':response.question.text, 'correct_answer':response.question.correct_answer, 'given_answer':response.answer, 'correct':response.correct(), 'pk':response.pk, 'incorrect_answer_1':response.question.incorrect_answer_1, 'incorrect_answer_2':response.question.incorrect_answer_2, 'incorrect_answer_3':response.question.incorrect_answer_3, 'feedback':response.get_feedback(), 'score':response.earned_points, 'max_score':response.question.points})
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
	##responses.sort(key=lambda x : x['objective_str'])
	return render(request, "realexams/view_instance.html", {"responses":responses, "released":instance.feedback_released})

def view_test_data(request, test):
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	if request.user.is_superuser:
		instances = TestInstance.objects.filter(test=test).order_by('-created')
	else:
		instances = TestInstance.objects.filter(test=test, user=request.user, feedback_released=True).order_by('-created')
	to_send = []
	if instances.count() == 0:
		return render(request, "realexams/plain.html", {"msg":"I couldn't find any test instances you have access to. They may not have feedback released yet.\nUse the above link to return to the menu."})
	for instance in instances:
		to_append = {"pk":instance.pk, "created":instance.created, "score":instance.score(), "total_score":instance.test.total_score(), "released":instance.feedback_released}
		if request.user.is_superuser:
			to_append["student"] = instance.user.name
		to_send.append(to_append)
	paginator = Paginator(to_send, 25)
	paginated_to_send = paginator.get_page(request.GET.get('page', 1))
	return render(request, "realexams/view_test.html", {"instances":paginated_to_send, "test":test.name})

def view_student_data(request, student):
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	instances = TestInstance.objects.filter(user=student).order_by('created')
	to_send = []
	for instance in instances:
		to_send.append({"pk":instance.pk, "created":instance.created, "test":instance.test.name, "score":instance.score(), "total_score":instance.test.total_score(), "released":instance.feedback_released})
	paginator = Paginator(to_send, 25)
	paginated_to_send = paginator.get_page(request.GET.get('page', 1))
	return render(request, "realexams/view_student.html", {"instances":paginated_to_send, "student":student.name})

def download(request):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	tests = Test.objects.all()
	return render(request, 'realexams/select.html', {'tests':tests, 'download':True})

def download_test(request, test):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	args_dict = {}
	args_dict['test_pk'] = test.pk
	args_dict['filename'] = str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__test_' + test.name.replace("/", "|") + '_data.csv'

	#Queue job
	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()
	#Create Queued page
	return redirect("realexams:queued")

def download_student_select(request):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	participants = [user for user in get_user_model().objects.all() if not user.is_superuser]
	return render(request, 'realexams/download_select.html', {'participants':participants})

def download_student(request, student):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	tests = Test.objects.filter(testinstance__user=student).distinct()
	return render(request, 'realexams/download_test.html', {'tests':tests, 'student':student.pk})

def download_student_test(request, student, test):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		student = get_user_model().objects.get(pk=student)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the student you're looking for.\nUse the above link to return to the menu."})
	try:
		test = Test.objects.get(pk=test)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the test you're looking for.\nUse the above link to return to the menu."})
	args_dict = {}
	args_dict['student_pk'] = student.pk
	args_dict['test_pk'] = test.pk
	args_dict['filename'] = str(datetime.datetime.today()).replace(":", "").replace(".", "") + '__student_' + student.name + "_test_" + test.name.replace("/", "|") + "_responses.csv"
	
	django_rq.enqueue(create_csv, args_dict)
	new_file = File(name=args_dict['filename'])
	new_file.save()
	return redirect("realexams:queued")

def delete_test_instance(request, instance, return_address):
	try:
		instance = TestInstance.objects.get(pk=instance)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the test instance you're looking for.\nUse the above link to return to the menu."})
	test = instance.test
	user = instance.user
	instance.delete()
	if return_address == "user":
		return redirect("realexams:view_student_data", user.pk)
	return redirect("realexams:view_test_data", test.pk)

def mark(request, response):
	try:
		response = TestResponse.objects.get(pk=response)
		if not request.user.is_superuser and not response.test_instance.user == request.user:
			return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
		response.manual_correct = not response.manual_correct
		response.save()
		return view_instance_data(request, response.test_instance.pk)
	except:
		return render(request, "realexams/plain.html", {"msg":"I couldn't find the response you're looking for.\nUse the above link to return to the menu."})

def queued(request):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	files = File.objects.all()
	args = []
	for file in files:
		#Check if the file exists and is finished
		args.append({'name':file.name, 'created':file.created, 'ready':default_storage.exists(file.name)})
	return render(request, "realexams/queued.html", {"files":args})

def retrieve(request, filename):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "realexams/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	if not default_storage.exists(filename):
		return redirect("realexams:queued")

	retrieved_file = default_storage.open(filename, 'r')

	response = HttpResponse(retrieved_file, content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=' + filename.replace(" ", "_").replace(",", "_")

	return response

def delete(request, filename):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "realexams/plain.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	default_storage.delete(filename)
	file.delete()
	return redirect("realexams:queued")

def feedback(request):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	if not request.method == "POST":
		return redirect("realexams:index")
	print(request.POST)
	for item in request.POST.items():
		print(item)
		try:
			response = TestResponse.objects.get(pk=int(item[0]))
			response.feedback = item[1]
			response.save()
		except Exception as e:
			print(e)
	return HttpResponse("Success")

def release_feedback(request, instance, student=False):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		instance = TestInstance.objects.get(pk=instance)
	except:
		return render(request, "realexams/plain.html", {'msg':"I couldn't find the test instance you're looking for.\nUse the above link to return to the menu."})
	instance.feedback_released = True
	instance.save()
	if student:
		return view_student_data(request, instance.user.pk)
	else:
		return view_test_data(request, instance.test.pk)

def score(request):
	if not request.user.is_superuser:
		return render(request, "realexams/plain.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	if not request.method == "POST":
		return redirect("realexams:index")
	for item in request.POST.items():
		try:
			response = TestResponse.objects.get(pk=int(item[0]))
			response.earned_points = float(item[1])
			response.save()
		except Exception as e:
			print(e)
	return HttpResponse("Success")