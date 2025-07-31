from django.shortcuts import render, redirect


# Create your views here.

from django.http import HttpRequest
from django.shortcuts import render, redirect
from .forms import QuestionForm
from .models import ResponseSet, Response
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
'''
QUESTIONS = [
    {'id': 'problem', 'text': '당신이 해결하려는 문제는 무엇인가요?'},
    {'id': 'result_form', 'text': '결과물은 어떤 형태이길 원하나요?'},
    {'id': 'tech_stack', 'text': '어떤 기술 스택을 염두에 두고 있나요?'},
    {'id': 'mvp_or_design', 'text': 'MVP 우선인가요, 설계 우선인가요?'},
    {'id': 'skills', 'text': 'HTML, CSS, Django, Notion 익숙도는 어떤가요?'},
    {'id': 'idea', 'text': '어떤 웹서비스를 만들고 싶으신가요?'},
    {'id': 'audience', 'text': '이 서비스를 사용할 주 타겟은 누구인가요?'},
    {'id': 'features', 'text': '이 서비스에 꼭 필요한 기능 3가지를 골라주세요.'},
]

QUESTIONS = [
    {"id": "goal_problem", "text": "당신이 해결하려는 문제는 무엇인가요?"},
    {"id": "goal_output", "text": "결과물은 어떤 형태이길 원하나요?"},
    {"id": "tech_stack", "text": "어떤 기술 스택을 염두에 두고 있나요?"},
    {"id": "style_pref", "text": "빠르게 MVP를 구현하는 쪽과, 완성도 높은 설계를 먼저 고민하는 것 중 어떤 걸 선호하시나요?"},
    {"id": "tech_level", "text": "HTML, CSS, Django, Notion 중 얼마나 익숙하신가요?"},
    {"id": "idea_origin", "text": "이 아이디어가 떠오른 계기나 꼭 만들고 싶다고 느낀 이유가 있으신가요?"},
    {"id": "target_user", "text": "이 서비스를 사용할 주 타겟은 누구인가요?"},
    {"id": "emotion", "text": "그들이 어떤 감정을 느낄지 상상해볼 수 있을까요? 어떤 고민을 가장 먼저 덜어주고 싶으신가요?"},
    {"id": "feature", "text": "이 서비스에 꼭 필요한 기능 3가지를 골라주세요."},
    {"id": "expectation", "text": "이 기능들이 구현된다면 어떤 점이 가장 기대되시나요? 걱정되는 점이 있다면 알려주세요."}
]
'''

QUESTIONS = [
    {
        "id": "goal_problem",
        "text": "당신이 해결하려는 문제는 무엇인가요?",
        "placeholder": "제품 기획을 혼자 하다 보니, 무엇부터 시작해야 할지 막막했어요.",
        "hint": "겪고 있는 문제나, 불편함을 자유롭게 적어주세요."
    },
    {
        "id": "desired_outcome",
        "text": "이 문제를 해결하면 어떤 결과를 기대하시나요?",
        "placeholder": "기획 단계가 명확해져서 빠르게 MVP를 만들 수 있을 것 같아요.",
        "hint": "문제가 해결되었을 때 어떤 변화가 생기기를 바라는지 적어주세요."
    },
    {
        "id": "tech_stack",
        "text": "익숙한 기술이나 도구가 있다면 알려주세요.",
        "placeholder": "HTML, CSS는 가능하고, Notion으로 문서 정리는 자주 해요.",
        "hint": "개발/기획 도구 또는 사용해본 툴을 자유롭게 적어주세요."
    },
    {
        "id": "preference",
        "text": "어떤 접근 방식이 본인에게 더 잘 맞는다고 느끼시나요?",
        "placeholder": "일단 먼저 만들어보면서 개선하는 게 익숙해요.",
        "hint": "설계부터 꼼꼼히 하는 스타일인지, 아니면 빠르게 시도하며 조정하는 편인지 말해주세요."
    },
    {
        "id": "target_user",
        "text": "이 서비스를 사용할 타겟 사용자는 누구인가요?",
        "placeholder": "온라인 쇼핑몰 운영자 또는 1인 창업가",
        "hint": "사용자의 나이대, 직업, 상황 등을 자유롭게 적어주세요."
    },
    {
        "id": "target_emotion",
        "text": "그 사용자는 어떤 감정이나 고민을 갖고 있을까요?",
        "placeholder": "제품 기획이 막막해서 어디서부터 시작해야 할지 모른다.",
        "hint": "감정, 불편, 고민 등 사용자의 내면을 떠올려주세요."
    },
    {
        "id": "core_function",
        "text": "당신이 생각하는 핵심 기능 3가지를 적어주세요.",
        "placeholder": "자동 키워드 추출 / 경쟁 제품 요약 / 수요 예측 그래프",
        "hint": "서비스에서 꼭 들어가야 한다고 생각하는 주요 기능을 적어주세요."
    },
    {
        "id": "expectation",
        "text": "이 서비스에서 기대하는 부분이 있다면 무엇인가요?",
        "placeholder": "혼자서 기획을 정리하고 빠르게 MVP를 만들 수 있었으면 해요.",
        "hint": "도움을 받고 싶은 부분이나 기대하는 효과를 말해주세요."
    },
    {
        "id": "concern",
        "text": "가장 걱정되거나 우려되는 점은 무엇인가요?",
        "placeholder": "너무 많은 기능을 넣다 보면 본질이 흐려질까 걱정돼요.",
        "hint": "기획, 구현, 사용자 반응 등 어떤 것이든 괜찮습니다."
    }
]


responses = {}
EMOTION_HINT_THRESHOLD = 15  #
'''
def index(request: HttpRequest):
    request.session['step'] = 0
    request.session['responses'] = {}
    return redirect('next_question')

def next_question(request: HttpRequest):
    step = request.session.get('step', 0)
    responses = request.session.get('responses', {})

    if request.method == 'POST':
        responses[QUESTIONS[step - 1]['id']] = request.POST.get('answer')
        request.session['responses'] = responses

    if step >= len(QUESTIONS):
        return redirect('complete')

    context = {
        'question': QUESTIONS[step]['text'],
        'step': step + 1,
        'total': len(QUESTIONS),
    }
    request.session['step'] = step + 1
    return render(request, 'questionnaire/question.html', context)

def complete(request: HttpRequest):
    responses = request.session.get('responses', {})
    return render(request, 'questionnaire/complete.html', {'responses': responses})
'''
@csrf_exempt
def questionnaire_view(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    current_q = int(request.session.get('current_q', 0))

    if current_q >= len(QUESTIONS):
        return redirect('questionnaire:summary')

    question = QUESTIONS[current_q]
    form = QuestionForm(request.POST or None)
    hint = None

    if request.method == 'POST':
        if form.is_valid():
            answer = form.cleaned_data['answer']

            # 정확한 session_key를 기반으로 저장
            rs, _ = ResponseSet.objects.get_or_create(session_key=session_key)
            Response.objects.create(
                response_set=rs,
                question_id=question['id'],
                answer=answer
            )

            # 다음 질문으로
            request.session['current_q'] = current_q + 1
            return redirect('questionnaire:questionnaire')

    return render(request, 'questionnaire/questionnaire.html', {
        'question': question['text'],
        'form': form,
        'hint': hint,
    })

@csrf_exempt
def questionnaire_view_v2(request):
    current_q = int(request.session.get('current_q', 0))
    session_key = request.session.session_key or request.session.save()

    if current_q >= len(QUESTIONS):
        return redirect('questionnaire:summary')

    question = QUESTIONS[current_q]
    form = QuestionForm(request.POST or None)
    hint = question.get("hint")
    placeholder = question.get("placeholder")  # 예시용 텍스트

    if request.method == 'POST' and form.is_valid():
        answer = form.cleaned_data['answer']
        rs, _ = ResponseSet.objects.get_or_create(session_key=session_key)
        Response.objects.create(
            response_set=rs,
            question_id=question['id'],
            answer=answer
        )
        request.session['current_q'] = current_q + 1
        return redirect('questionnaire:question')

    return render(request, 'questionnaire/question.html', {
        'form': form,
        'question': question,
        'hint': hint,
        'placeholder': placeholder,
    })




# views.py
def summary_view(request):
    session_key = request.session.session_key
    print("현재 세션 키:", session_key)
    if not session_key:
        #return redirect('start')  # 세션이 없다면 시작으로
        return redirect('questionnaire:start')

    try:
        response_set = ResponseSet.objects.get(session_key=session_key)
    except ResponseSet.DoesNotExist:
        #return redirect('start')
        return redirect('questionnaire:start')

    responses = Response.objects.filter(response_set=response_set)
    if not responses.exists():
        #return redirect('start')
        return redirect('questionnaire:start')

    context = {
        'responses': responses
    }
    print(context)
    return render(request, 'questionnaire/summary.html', context)


'''
def final_prompt_view(request):
    """최종 요약 결과물을 보여주는 뷰"""
    last_response_set = ResponseSet.objects.last()
    #last_response_set = Response.objects.last()

    if not last_response_set:
        return render(request, "questionnaire/final_prompt.html", {"prompt": "아직 응답이 없습니다."})

    # 예시: 전체 응답을 기반으로 하나의 Prompt 텍스트 생성
    all_answers = last_response_set.answers
    formatted = "\n".join(f"{q_id}: {answer}" for q_id, answer in all_answers.items())

    return render(request, "questionnaire/final_prompt.html", {"prompt": formatted})
'''
def final_prompt_view(request):
    """최종 요약 결과물을 보여주는 뷰"""
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

    # 질문 ID와 응답 조합
    formatted = "\n".join(f"{r.question_id}: {r.answer}" for r in responses)

    return render(request, "questionnaire/final_prompt.html", {"prompt": formatted})



    

# views.py
def start_questionnaire(request):
    request.session.flush()  # 세션 완전 초기화
    #return redirect('questionnaire:questionnaire')  # 질문으로 이동
    return redirect('questionnaire:question')  # 질문으로 이동

