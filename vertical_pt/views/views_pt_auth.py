"""PT 전용 회원가입 / 로그인 / 로그아웃."""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from vertical_pt.forms import PTSignupForm


def pt_signup(request):
    if request.user.is_authenticated:
        return redirect("vertical_pt:pt_index")

    form = PTSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("vertical_pt:pt_index")

    return render(request, "vertical_pt/pt_signup.html", {"form": form})


def pt_login(request):
    if request.user.is_authenticated:
        return redirect("vertical_pt:pt_index")

    error = ""
    if request.method == "POST":
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        # email로 username 조회 후 인증
        from django.contrib.auth.models import User
        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            username = email  # fallback: username 직접 입력 허용

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get("next", "")
            return redirect(next_url or "vertical_pt:pt_index")
        else:
            error = "Invalid email or password."

    return render(request, "vertical_pt/pt_login.html", {"error": error})


def pt_logout(request):
    logout(request)
    return redirect("vertical_pt:pt_login")
