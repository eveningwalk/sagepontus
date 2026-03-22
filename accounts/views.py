from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required

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
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)  # ✅ 가입 후 자동 로그인
            #return redirect('questionnaire:home', category='common', order=1)
            return redirect('questionnaire:home')
        else:
            print(form.errors)
    else:
        form = UserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login(request):
    error = False
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            #return redirect('questionnaire:home', category='common', order=1)
            return redirect('questionnaire:home')
        else:
            error = True
    return render(request, 'accounts/login.html', {'error': error})
    

def logout(request):
    auth_logout(request)
    return redirect('accounts:login')

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
