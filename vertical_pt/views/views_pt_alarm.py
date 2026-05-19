"""PT Red Flag 웹 UI 뷰."""

import datetime
import json

from django.contrib.auth.decorators import login_required as _login_required
from functools import wraps

def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect as _redirect
            from django.urls import reverse
            return _redirect(f"{reverse('vertical_pt:pt_login')}?next={request.path}")
        return func(request, *args, **kwargs)
    return wrapper
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from vertical_pt.engine import score_soap, build_patient_context
from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter
from vertical_pt.engine.documents import generate_document, DOC_TITLES
from vertical_pt.models import PatientTimeline, RedFlagAlert


# ── 사이드바 앱 셸 ─────────────────────────────────────────────────

@login_required
def index(request):
    return render(request, "vertical_pt/pt_app.html")


# ── AJAX: 환자 목록 ───────────────────────────────────────────────

@login_required
def patient_list_json(request):
    seen = {}
    qs = (
        PatientTimeline.objects
        .filter(therapist=request.user)
        .order_by("-session_date", "-created_at")
    )
    for t in qs:
        pid = t.patient_id
        if pid not in seen:
            seen[pid] = {
                "patient_id":    pid,
                "patient_name":  t.patient_name,
                "last_session":  str(t.session_date),
                "latest_alarm":  t.alarm_level,
                "session_count": 0,
            }
        seen[pid]["session_count"] += 1

    return JsonResponse({"patients": list(seen.values())})


# ── AJAX: 환자 ID 자동 생성 ───────────────────────────────────────

@login_required
def generate_patient_id(request):
    today = datetime.date.today().strftime("%y%m%d")   # e.g. "260518"
    prefix = f"PT-{today}-"
    existing = (
        PatientTimeline.objects
        .filter(therapist=request.user, patient_id__startswith=prefix)
        .values_list("patient_id", flat=True)
        .distinct()
    )
    seq = len(set(existing)) + 1
    return JsonResponse({"patient_id": f"{prefix}{seq:03d}"})


# ── 공통: patient_id 정규화 ───────────────────────────────────────

def _normalize_pid(raw: str, fallback: str = "ANON") -> str:
    return (raw.strip().upper() or fallback)


# ── AJAX: 환자 세션 목록 ──────────────────────────────────────────

@login_required
def patient_sessions_json(request, patient_id):
    qs = (
        PatientTimeline.objects
        .filter(therapist=request.user, patient_id=patient_id)
        .order_by("-session_date", "-created_at")
    )
    sessions = []
    for s in qs:
        alert = s.alerts.order_by("-created_at").first()
        sessions.append({
            "id":                  s.id,
            "session_date":        str(s.session_date),
            "alarm_level":         s.alarm_level,
            "triggered_condition": s.triggered_condition,
            "critical_score":      round((s.critical_score or 0) * 100),
            "soap_text":           s.soap_text,
            "created_at":          s.created_at.strftime("%Y-%m-%d %H:%M"),
            "matched_indicators":  alert.matched_indicators if alert else [],
            "referral_letter":     alert.referral_letter if alert else "",
        })
    patient_name = qs[0].patient_name if qs else ""
    return JsonResponse({
        "patient_id":   patient_id,
        "patient_name": patient_name,
        "sessions":     sessions,
    })


# ── AJAX: Alarm 현황 대시보드 ─────────────────────────────────

@login_required
def alarm_dashboard_json(request):
    qs = (
        PatientTimeline.objects
        .filter(therapist=request.user)
        .exclude(alarm_level="NONE")
        .order_by("-session_date", "-created_at")
        .select_related()
        .prefetch_related("alerts")
    )
    rows = []
    for s in qs:
        alert = s.alerts.order_by("-created_at").first()
        rows.append({
            "id":                  s.id,
            "patient_id":          s.patient_id,
            "patient_name":        s.patient_name,
            "session_date":        str(s.session_date),
            "alarm_level":         s.alarm_level,
            "triggered_condition": s.triggered_condition,
            "critical_score":      round((s.critical_score or 0) * 100),
            "soap_text":           s.soap_text,
            "matched_indicators":  alert.matched_indicators if alert else [],
            "referral_letter":     alert.referral_letter if alert else "",
        })

    red    = [r for r in rows if r["alarm_level"] == "RED"]
    yellow = [r for r in rows if r["alarm_level"] == "YELLOW"]
    return JsonResponse({
        "red":    red,
        "yellow": yellow,
        "counts": {"red": len(red), "yellow": len(yellow)},
    })


# ── AJAX: 세션 삭제 ───────────────────────────────────────────

@login_required
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    try:
        session = PatientTimeline.objects.get(id=session_id, therapist=request.user)
    except PatientTimeline.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    patient_id = session.patient_id
    session.delete()

    # 환자의 남은 세션 수 반환 (0이면 사이드바에서도 제거)
    remaining = PatientTimeline.objects.filter(
        therapist=request.user, patient_id=patient_id
    ).count()
    return JsonResponse({"ok": True, "patient_id": patient_id, "remaining": remaining})


# ── AJAX: SOAP 저장 (VPPS 분석 포함) ─────────────────────────────

@login_required
@require_http_methods(["POST"])
def save_soap_ajax(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    soap_text       = data.get("soap_text", "").strip()
    patient_id      = _normalize_pid(data.get("patient_id", ""))
    patient_name    = data.get("patient_name", "").strip()
    date_str        = data.get("session_date", "")
    confirmed_rf_ids = data.get("confirmed_rf_ids", []) or []

    if not soap_text and not confirmed_rf_ids:
        return JsonResponse({"error": "SOAP text is required"}, status=400)

    try:
        session_date = datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        session_date = datetime.date.today()

    result      = score_soap(soap_text, pre_confirmed_ids=confirmed_rf_ids if confirmed_rf_ids else None)
    patient_ctx = build_patient_context(patient_id, request.user.id)

    timeline = PatientTimeline.objects.create(
        therapist=request.user,
        patient_id=patient_id,
        patient_name=patient_name,
        session_date=session_date,
        soap_text=soap_text,
        extracted_symptoms=result.get("vpps", {}),
        critical_score=result["score"],
        alarm_level=result["alarm"],
        triggered_condition=result["condition"] or "",
    )

    alert = None
    referral_letter = ""
    active_conditions = result.get("conditions", [])
    if result["alarm"] in ("RED", "YELLOW"):
        alert = RedFlagAlert.objects.create(
            timeline=timeline,
            condition=result["condition"] or "",
            alarm_level=result["alarm"],
            matched_indicators=result["matched"],
            score=result["score"],
            trigger_label=result.get("trigger", ""),
        )
        if result["alarm"] in ("RED", "YELLOW"):
            therapist_name = request.user.get_full_name() or request.user.username
            if len(active_conditions) > 1:
                referral_letter = generate_multi_referral_letter(
                    active_conditions,
                    patient_id=patient_id,
                    therapist_name=therapist_name,
                )
            else:
                referral_letter = generate_referral_letter(
                    alert, patient_id=patient_id, therapist_name=therapist_name
                )
            alert.referral_letter = referral_letter
            alert.save(update_fields=["referral_letter"])

    vpps = result.get("vpps", {})
    return JsonResponse({
        "ok":              True,
        "timeline_id":     timeline.id,
        "alarm":           result["alarm"],
        "condition":       result["condition"] or "",
        "score":           round((result["score"] or 0) * 100),
        "matched":         result["matched"],
        "trigger":         result.get("trigger", ""),
        "conditions":      active_conditions,
        "vpps_hits":       vpps.get("hits", []),
        "referral_letter": referral_letter,
        "patient_context": patient_ctx,
    })


# ── AJAX: 문서 생성 (multi-session history 기반) ─────────────────

@login_required
@require_http_methods(["POST"])
def generate_doc_ajax(request, patient_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    doc_type = data.get("doc_type", "").strip()
    if doc_type not in DOC_TITLES:
        return JsonResponse({"error": f"Unknown doc_type: {doc_type}"}, status=400)

    sessions = list(
        PatientTimeline.objects
        .filter(therapist=request.user, patient_id=patient_id)
        .prefetch_related("alerts")
        .order_by("session_date", "created_at")
    )
    if not sessions:
        return JsonResponse({"error": "No sessions found for this patient"}, status=404)

    patient_ctx  = build_patient_context(patient_id, request.user.id)
    therapist_name = request.user.get_full_name() or request.user.username
    clinic_name    = ""
    try:
        if request.user.pt_profile:
            clinic_name = request.user.pt_profile.clinic_name or ""
    except Exception:
        pass

    try:
        doc_text = generate_document(
            doc_type=doc_type,
            sessions=sessions,
            patient_ctx=patient_ctx,
            therapist_name=therapist_name,
            patient_id=patient_id,
            clinic_name=clinic_name,
        )
    except Exception as e:
        return JsonResponse({"error": f"Document generation failed: {e}"}, status=500)

    return JsonResponse({
        "ok":           True,
        "doc_type":     doc_type,
        "doc":          doc_text,
        "title":        DOC_TITLES[doc_type],
        "generated_at": datetime.date.today().strftime("%B %d, %Y"),
        "session_count": len(sessions),
    })


# ── 기존 POST-redirect 플로우 (하위 호환 유지) ───────────────────

@login_required
@require_http_methods(["POST"])
def analyze_view(request):
    soap_text  = request.POST.get("soap_text", "").strip()
    patient_id = _normalize_pid(request.POST.get("patient_id", ""), fallback="PT-ANON")

    if not soap_text:
        return redirect("vertical_pt:pt_index")

    patient_ctx = build_patient_context(patient_id, request.user.id)
    result      = score_soap(soap_text)

    timeline = PatientTimeline.objects.create(
        therapist=request.user,
        patient_id=patient_id,
        session_date=datetime.date.today(),
        soap_text=soap_text,
        extracted_symptoms=result.get("vpps", {}),
        critical_score=result["score"],
        alarm_level=result["alarm"],
        triggered_condition=result["condition"] or "",
    )

    alert = None
    referral_letter = ""
    if result["alarm"] in ("RED", "YELLOW"):
        alert = RedFlagAlert.objects.create(
            timeline=timeline,
            condition=result["condition"] or "",
            alarm_level=result["alarm"],
            matched_indicators=result["matched"],
            score=result["score"],
            trigger_label=result.get("trigger", ""),
        )
        if result["alarm"] == "RED":
            therapist_name  = request.user.get_full_name() or request.user.username
            referral_letter = generate_referral_letter(
                alert, patient_id=patient_id, therapist_name=therapist_name
            )
            alert.referral_letter = referral_letter
            alert.save(update_fields=["referral_letter"])

    request.session["pt_result"] = {
        "alarm":           result["alarm"],
        "condition":       result["condition"],
        "score":           result["score"],
        "matched":         result["matched"],
        "trigger":         result.get("trigger", ""),
        "alert_id":        alert.id if alert else None,
        "referral_letter": referral_letter,
        "patient_context": patient_ctx,
        "soap_text":       soap_text,
        "patient_id":      patient_id,
    }
    return redirect("vertical_pt:pt_result")


@login_required
def result_view(request):
    ctx = request.session.pop("pt_result", None)
    if not ctx:
        return redirect("vertical_pt:pt_index")
    ctx["score_pct"] = round((ctx.get("score") or 0) * 100)
    return render(request, "vertical_pt/result.html", ctx)
