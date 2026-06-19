import random
import re

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods


def _is_tester(user):
    return user.groups.filter(name='tester').exists()

from questionnaire.models import PerfTestResult
from questionnaire.models.models_braintree import BrainBlockNode
from questionnaire.prompts.service import _chat_generate_with_usage
from questionnaire.prompts.gemini_client import generate_with_context_cache

_AI_GENERATION = {"max_tokens": 6000, "temperature": 0.7}

MODEL_PRICING = {
    "Gemini 2.5 Flash":  {"input": 0.15,  "cache_write": 0.15,   "cache_read": 0.0375, "tier": "저가"},
    "Claude Haiku 4.5":  {"input": 0.80,  "cache_write": 1.00,   "cache_read": 0.08,   "tier": "저가"},
    "GPT-4o mini":       {"input": 0.15,  "cache_write": 0.15,   "cache_read": 0.075,  "tier": "저가"},
    "Claude Sonnet 4.5": {"input": 3.00,  "cache_write": 3.75,   "cache_read": 0.30,   "tier": "중가"},
    "GPT-4o":            {"input": 2.50,  "cache_write": 2.50,   "cache_read": 1.25,   "tier": "고가"},
}

MONTHLY_SESSIONS = 200

SAMPLE_CASES = [
    {
        "case": "뇌졸중 환자 SOAP 노트",
        "prompt_a": "저는 재활병원에서 근무하는 물리치료사예요. 주로 뇌졸중 편마비 환자를 담당해요. 오늘 환자는 65세 남성이고, 3개월 전 좌측 MCA 뇌졸중 이후 우측 편마비가 왔어요. Berg Balance Scale 28점, 10MWT 0.4m/s예요. 저는 보통 PNF 기반으로 접근하는데, 보험 청구 서류도 자주 써야 해서 ICD-10 코드도 잘 알고 있어야 해요. SOAP 형식으로 작성해줘요.",
        "b_system": "# 역할과 상황\n재활병원 신경과 병동 소속 물리치료사. 뇌졸중 후 편마비 성인(60~80대) 전담.\n\n# 목표\nSOAP 노트 작성, 보험 청구 서류(ICD-10) 대응, 보행 재활 프로토콜 설계.\n\n# 기대 응답 방식\n의료 기록 형식으로 간결하게. PNF·과제지향훈련 관점 반영. EBP 근거 한 줄 포함.",
        "b_task": "65세 남성, MCA 뇌졸중 3개월, 우측 편마비. Berg 28, 10MWT 0.4m/s. SOAP 노트 작성.",
    },
    {
        "case": "ACL 재건술 후 HEP",
        "prompt_a": "저는 스포츠 클리닉에서 일하는 물리치료사인데요, 이번에 ACL 재건술을 받은 25세 남성 환자가 있어요. 수술 후 6주가 됐고 현재 보조기 착용 중이에요. ROM은 신전 -5도, 굴곡 100도예요. MMT는 대퇴사두근 3+/5예요. 아직 달리기는 안 되고 자전거 정도는 가능한 시기예요. 환자가 20대 운동선수라서 복귀 목표가 있어요. 홈 운동 프로그램을 만들어줄 수 있어요?",
        "b_system": "# 역할과 상황\n재활병원 신경과 병동 소속 물리치료사. 뇌졸중 후 편마비 성인(60~80대) 전담.\n\n# 목표\nSOAP 노트 작성, 보험 청구 서류(ICD-10) 대응, 보행 재활 프로토콜 설계.\n\n# 기대 응답 방식\n의료 기록 형식으로 간결하게. PNF·과제지향훈련 관점 반영. EBP 근거 한 줄 포함.",
        "b_task": "25세 남성, ACL 재건술 6주. 보조기 착용, ROM 신전 -5°/굴곡 100°, 대퇴사두근 MMT 3+. 6주차 HEP 작성.",
    },
]


def _count_tokens(text: str) -> int:
    korean = len(re.findall(r'[가-힣]', text))
    others = len(re.sub(r'[가-힣\s]', '', text))
    spaces = len(re.findall(r'\s+', text))
    return int(korean * 1.5 + others / 4 + spaces * 0.3)


def _token_analysis(prompt_a: str, b_system: str, b_task: str) -> dict:
    tok_a        = _count_tokens(prompt_a + ("\n\n" + b_task if b_task else ""))
    tok_b_system = _count_tokens(b_system)
    tok_b_task   = _count_tokens(b_task)
    tok_b_total  = tok_b_system + tok_b_task

    reduction         = (tok_a - tok_b_total) / tok_a * 100 if tok_a else 0
    writing_reduction = (tok_a - tok_b_task)  / tok_a * 100 if tok_a else 0

    pricing = []
    for model, p in MODEL_PRICING.items():
        ca = tok_a * p["input"] / 1_000_000 * MONTHLY_SESSIONS
        cb_cached = (
            tok_b_system * p["cache_write"] / 1_000_000 * 1
            + tok_b_system * p["cache_read"]  / 1_000_000 * (MONTHLY_SESSIONS - 1)
            + tok_b_task   * p["input"]        / 1_000_000 * MONTHLY_SESSIONS
        )
        saved  = round(ca - cb_cached, 4)
        pct    = round(saved / ca * 100, 1) if ca else 0
        pricing.append({
            "model": model, "tier": p["tier"],
            "cost_a": round(ca, 4),
            "cost_b_cached": round(cb_cached, 4),
            "saved": saved, "pct": pct,
        })

    return {
        "tok_a": tok_a,
        "tok_b_system": tok_b_system,
        "tok_b_task": tok_b_task,
        "tok_b_total": tok_b_total,
        "reduction": round(reduction, 1),
        "writing_reduction": round(writing_reduction, 1),
        "pricing": pricing,
    }


@login_required
@require_http_methods(["GET", "POST"])
def perf_test(request):
    """폼 페이지만 렌더링. 분석은 /perf-test/run/ 에서 AJAX로 처리."""
    form_data = {"case_name": "", "prompt_a": "", "b_system": "", "b_task": ""}

    if request.method == "POST":
        action = request.POST.get("action", "prefill")

        if action == "load_sample":
            idx = int(request.POST.get("sample_idx", 0))
            s = SAMPLE_CASES[idx % len(SAMPLE_CASES)]
            form_data = {"case_name": s["case"], "prompt_a": s["prompt_a"],
                         "b_system": s["b_system"], "b_task": s["b_task"]}
        else:
            form_data = {
                "case_name": request.POST.get("case_name", ""),
                "prompt_a":  request.POST.get("prompt_a", ""),
                "b_system":  request.POST.get("b_system", ""),
                "b_task":    request.POST.get("b_task", ""),
            }

    history = PerfTestResult.objects.filter(user=request.user).values(
        "id", "case_name", "created_at",
        "tokens", "usage_a", "usage_b",
    )[:20]

    user_trees = [
        {"title": b.braintree.title or "(무제)", "prompt": b.cached_result_2}
        for b in BrainBlockNode.objects.filter(
            braintree__user=request.user,
            type="domain",
        ).exclude(cached_result_2="").select_related("braintree").order_by("-id")[:10]
        if b.cached_result_2
    ]

    return render(request, "questionnaire/test/perf_test.html", {
        "form_data":        form_data,
        "samples":          [{"idx": i, "name": c["case"]} for i, c in enumerate(SAMPLE_CASES)],
        "monthly_sessions": MONTHLY_SESSIONS,
        "history":          list(history),
        "user_trees":       user_trees,
        "is_tester":        _is_tester(request.user),
    })


def _calc_actual_cost(usage_a: dict, usage_b: dict) -> dict:
    flash_price = {"input": 0.05, "cache_read": 0.0125, "output": 0.60}
    def cost(usage, is_b):
        inp    = usage.get("input_tokens", 0)
        out    = usage.get("output_tokens", 0)
        cached = usage.get("cached_tokens", 0) if is_b else 0
        fresh  = inp - cached
        return round((fresh * flash_price["input"] + cached * flash_price["cache_read"] + out * flash_price["output"]) / 1_000_000, 6)
    a = cost(usage_a, False)
    b = cost(usage_b, True)
    saved = round(a - b, 6)
    return {
        "a_per_session":   a,
        "b_per_session":   b,
        "saved_per_session": saved,
        "saved_pct":       round(saved / a * 100, 1) if a else 0,
        "cache_supported": usage_b.get("cache_supported", False),
    }


@login_required
@require_http_methods(["GET"])
def perf_test_detail(request, pk):
    record = PerfTestResult.objects.filter(pk=pk, user=request.user).first()
    if not record:
        return JsonResponse({"error": "Not found"}, status=404)
    flipped = record.flipped or False
    return JsonResponse({
        "id":          record.id,
        "case_name":   record.case_name,
        "prompt_a":    record.prompt_a,
        "b_system":    record.b_system,
        "b_task":      record.b_task,
        "tokens":      record.tokens,
        "result_a":    record.result_a,
        "result_b":    record.result_b,
        "result_1":    record.result_b if flipped else record.result_a,
        "result_2":    record.result_a if flipped else record.result_b,
        "usage_a":     record.usage_a,
        "usage_b":     record.usage_b,
        "actual_cost": _calc_actual_cost(record.usage_a, record.usage_b),
        "flipped":     flipped,
        "vote":        record.vote or "",
    })


@login_required
@require_http_methods(["POST"])
def perf_test_run(request):
    """토큰 분석 + AI A/B 호출을 한 번에 처리해 JSON 반환."""
    prompt_a = request.POST.get("prompt_a", "").strip()
    b_system = request.POST.get("b_system", "").strip()
    b_task   = request.POST.get("b_task", "").strip()

    if not prompt_a or not b_system or not b_task:
        return JsonResponse({"error": "prompt_a, b_system, b_task를 모두 입력해 주세요."}, status=400)

    tokens = _token_analysis(prompt_a, b_system, b_task)

    try:
        generate = _chat_generate_with_usage()
        result_a, usage_a = generate("gemini-2.5-flash", f"{prompt_a}\n\n{b_task}", _AI_GENERATION, system="한국어로 답변하세요.")
        usage_a.setdefault("cached_tokens", 0)
        usage_a.setdefault("fresh_tokens", usage_a.get("input_tokens", 0))
        usage_a["cache_supported"] = False

        result_b, usage_b = generate_with_context_cache("gemini-2.5-flash", b_task, _AI_GENERATION, system=b_system)

        flipped = random.choice([True, False])

        record = PerfTestResult.objects.create(
            user=request.user,
            case_name=request.POST.get("case_name", "").strip(),
            prompt_a=prompt_a,
            b_system=b_system,
            b_task=b_task,
            tokens=tokens,
            result_a=result_a,
            result_b=result_b,
            usage_a=usage_a,
            usage_b=usage_b,
            flipped=flipped,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    # 실측 기반 단일 세션 비용 계산 (Gemini 2.5 Flash 기준)
    flash_price = {"input": 0.05, "cache_read": 0.0125, "output": 0.60}
    def _session_cost(usage, is_b):
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        cached = usage.get("cached_tokens", 0) if is_b else 0
        fresh = inp - cached
        return round(
            (fresh * flash_price["input"] + cached * flash_price["cache_read"] + out * flash_price["output"])
            / 1_000_000, 6
        )

    actual_cost = {
        "a_per_session": _session_cost(usage_a, False),
        "b_per_session": _session_cost(usage_b, True),
        "cache_supported": usage_b.get("cache_supported", False),
    }
    actual_cost["saved_per_session"] = round(actual_cost["a_per_session"] - actual_cost["b_per_session"], 6)
    actual_cost["saved_pct"] = round(
        actual_cost["saved_per_session"] / actual_cost["a_per_session"] * 100, 1
    ) if actual_cost["a_per_session"] else 0

    return JsonResponse({
        "id":          record.id,
        "tokens":      tokens,
        "flipped":     flipped,
        "result_1":    result_b if flipped else result_a,
        "result_2":    result_a if flipped else result_b,
        "usage_a":     usage_a,
        "usage_b":     usage_b,
        "actual_cost": actual_cost,
    })


@login_required
@require_http_methods(["GET"])
def perf_test_compare(request, pk):
    record = get_object_or_404(PerfTestResult, pk=pk)
    flipped = record.flipped or False
    return render(request, "questionnaire/test/compare.html", {
        "record":   record,
        "result_1": record.result_b if flipped else record.result_a,
        "result_2": record.result_a if flipped else record.result_b,
        "voted":    bool(record.vote),
        "winner":   ("Sage Pontus" if record.vote == "B" else "기존 방식") if record.vote else None,
        "chosen_num": ("1" if (flipped and record.vote == "B") or (not flipped and record.vote == "A") else "2") if record.vote else None,
    })


@login_required
@require_http_methods(["POST"])
def perf_test_vote(request):
    record_id = request.POST.get("record_id")
    chosen    = request.POST.get("chosen")  # '1' or '2'

    record = PerfTestResult.objects.filter(pk=record_id, user=request.user).first()
    if not record:
        return JsonResponse({"error": "Not found"}, status=404)
    if chosen not in ("1", "2"):
        return JsonResponse({"error": "Invalid choice"}, status=400)

    flipped = record.flipped or False
    if chosen == "1":
        record.vote = "B" if flipped else "A"
    else:
        record.vote = "A" if flipped else "B"
    record.save(update_fields=["vote"])

    return JsonResponse({
        "vote":    record.vote,
        "flipped": record.flipped,
        "winner":  "Sage Pontus" if record.vote == "B" else "기존 방식",
    })
