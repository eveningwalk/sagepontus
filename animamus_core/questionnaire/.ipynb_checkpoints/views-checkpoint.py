from django.shortcuts import render, redirect, get_object_or_404
from django.forms import formset_factory
from .models import Category, Question, ResponseSet, Response
from .forms import QuestionForm

from django.http import JsonResponse
from questionnaire.utils.summary import summarize_text



from django.shortcuts import render
from django.http import JsonResponse
from .models import ResponseSet, Response
#from .summarizer import summarize_text
import json


from django.shortcuts import get_object_or_404
from .models import Category, ResponseSet, Response
from questionnaire.utils.summary import summarize_text
'''
def summary_page(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    session_key = request.session.session_key
    if not session_key:
        return redirect('questionnaire:question_flow', category_slug=category_slug)

    response_set = ResponseSet.objects.filter(session_key=session_key).first()
    if not response_set:
        return redirect('questionnaire:question_flow', category_slug=category_slug)

    responses = response_set.responses.exclude(question_id='summary')
    combined_text = "\n".join(
        f"{r.question_id}: {r.answer}" for r in responses
    )

    # 💡 요약 이미 했는지 확인
    summary_exists = response_set.responses.filter(question_id='summary').exists()

    if not summary_exists and combined_text.strip():
        summary = summarize_text(combined_text)

        # 저장
        Response.objects.create(
            response_set=response_set,
            question_id='summary',
            answer=summary
        )

    return render(request, 'questionnaire/summary_page.html', {
        'response_set': response_set
    })


'''
def summary_page(request, category_slug):
    session_key = request.session.session_key
    response_set = get_object_or_404(ResponseSet, session_key=session_key)

    # 사용자 입력 모음
    user_inputs = "\n".join(
        f"{r.question_id}: {r.answer}" for r in response_set.responses.all() if r.question_id != 'summary'
    )

    print("🧪 사용자 입력 모음:")
    print(user_inputs)

    # 이미 summary가 존재하는지 확인
    summary_exists = response_set.responses.filter(question_id='summary').exists()
    print("🧪 요약 존재 여부:", summary_exists)

    if not summary_exists:
        print("🔄 요약 생성 중...")
        ai_summary = summarize_text(user_inputs)
        print("✅ 요약 결과:", ai_summary)

        Response.objects.create(
            response_set=response_set,
            question_id='summary',
            answer=ai_summary
        )
    else:
        print("⚠️ 이미 요약된 내용 존재")

    return render(request, 'questionnaire/summary_page.html', {
        'response_set': response_set
    })








        

    




# 1️⃣ 설문 시작
def start(request, category_slug='saas'):
    """
    설문 시작: 세션 초기화 후 첫 질문으로 이동
    """
    request.session.flush()
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    # 새 ResponseSet 생성
    ResponseSet.objects.create(session_key=session_key)

    # 첫 질문으로 이동
    return redirect('questionnaire:question_flow', category_slug=category_slug, step=0)


# 2️⃣ 질문 흐름
def question_flow(request, category_slug, step=0):
    category = get_object_or_404(Category, slug=category_slug)
    questions = category.questions.order_by('order')

    if step >= questions.count():
        return redirect('questionnaire:summary', category_slug=category_slug)

    current_question = questions[step]

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            answer_text = form.cleaned_data['answer']
            session_key = request.session.session_key

            response_set, _ = ResponseSet.objects.get_or_create(session_key=session_key)

            Response.objects.create(
                response_set=response_set,
                question_id=current_question.question_id,
                answer=answer_text
            )

            return redirect('questionnaire:question_flow', category_slug=category_slug, step=step+1)
    else:
        form = QuestionForm()

    return render(request, 'questionnaire/question_form.html', {
        'form': form,
        'question': current_question,
        'step': step+1,
        'total': questions.count(),
        'category': category,
    })


# 3️⃣ 설문 요약
'''
def summary_view(request):
    session_key = request.session.session_key
    if not session_key:
        return redirect('questionnaire:start')

    try:
        response_set = ResponseSet.objects.get(session_key=session_key)
    except ResponseSet.DoesNotExist:
        return redirect('questionnaire:start')

    responses = Response.objects.filter(response_set=response_set)

    # AI 요약 함수 호출 (summary.py 의 summarize_text 등)
    all_text = "\n".join([r.answer for r in responses])
    summary_text = summarize_text(all_text) if all_text else ""

    context = {
        'responses': responses,
        'summary_text': summary_text,
    }
    return render(request, 'questionnaire/summary_page.html', context)
    
def summary_view(request, category_slug=None):
    session_key = request.session.session_key
    if not session_key:
        return redirect('questionnaire:start', category_slug=category_slug or 'saas')

    try:
        response_set = ResponseSet.objects.get(session_key=session_key)
    except ResponseSet.DoesNotExist:
        return redirect('questionnaire:start', category_slug=category_slug or 'saas')

    responses = Response.objects.filter(response_set=response_set)

    context = {
        'responses': responses
    }
    return render(request, 'questionnaire/summary.html', context)
'''

# 4️⃣ 최종 요약 prompt
def final_prompt_view(request):
    session_key = request.session.session_key
    if not session_key:
        return render(request, "questionnaire/final_prompt.html", {"prompt": "세션이 만료되었거나 응답 기록이 없습니다."})

    try:
        response_set = ResponseSet.objects.get(session_key=session_key)
    except ResponseSet.DoesNotExist:
        return render(request, "questionnaire/final_prompt.html", {"prompt": "응답 세트가 존재하지 않습니다."})

    responses = Response.objects.filter(response_set=response_set)
    if not responses.exists():
        return render(request, "questionnaire/final_prompt.html", {"prompt": "아직 응답이 없습니다."})

    formatted = "\n".join(f"{r.question_id}: {r.answer}" for r in responses)
    return render(request, "questionnaire/final_prompt.html", {"prompt": formatted})
