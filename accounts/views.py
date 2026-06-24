import json

from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from animamus_project.auth_views import authenticate_by_email
from .models import EarlyAccessSignup

def landing_page(request):
    category_name = request.GET.get('category')
    questions = []

    if category_name:
        try:
            category = Category.objects.get(name=category_name)
            questions = Question.objects.filter(category=category).order_by('order')
        except Category.DoesNotExist:
            pass

    return render(request, 'accounts/landing.html', {'questions': questions})
    #return render(request, 'base.html', {'questions': questions})
    

def signup(request):
    from .forms import EarlyAccessSignupForm
    if request.method == 'POST':
        form = EarlyAccessSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'accounts/signup.html', {'success': True})
    else:
        form = EarlyAccessSignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login(request):
    error = False
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        user = authenticate_by_email(request, email, password)
        if user:
            auth_login(request, user)
            return redirect('questionnaire:home')
        else:
            error = True
    return render(request, 'accounts/login.html', {'error': error})
    

def logout(request):
    auth_logout(request)
    return redirect('home')


@csrf_exempt
@require_http_methods(["POST"])
def api_signup(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    email = data.get('email', '').strip().lower()
    industry = data.get('industry', '').strip()

    if not email or not industry:
        return JsonResponse({'error': '이메일과 업종을 입력해주세요.'}, status=400)

    valid_industries = [c[0] for c in EarlyAccessSignup.INDUSTRY_CHOICES]
    if industry not in valid_industries:
        return JsonResponse({'error': '유효하지 않은 업종입니다.'}, status=400)

    if EarlyAccessSignup.objects.filter(email=email).exists():
        return JsonResponse({'error': '이미 등록된 이메일입니다.'}, status=409)

    EarlyAccessSignup.objects.create(email=email, industry=industry)
    return JsonResponse({'message': '신청이 완료되었습니다.'}, status=201)


@require_http_methods(["GET"])
def api_check_email(request):
    email = request.GET.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'available': False, 'error': '이메일을 입력해주세요.'}, status=400)
    available = not EarlyAccessSignup.objects.filter(email=email).exists()
    return JsonResponse({'available': available})


@login_required
def show_question_step(request, category, order):
    ...
    if request.method == 'POST':
        answer_text = request.POST.get('answer')
        if answer_text:
            UserAnswer.objects.create(
                user=request.user,
                question=question,
                answer_text=answer_text
            )
