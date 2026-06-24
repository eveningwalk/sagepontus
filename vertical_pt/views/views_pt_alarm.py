"""PT Red Flag 웹 UI 뷰."""

import datetime
import json
import logging
import re

logger = logging.getLogger(__name__)

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
from vertical_pt.engine.referral import generate_referral_letter, generate_referral_letter_ai, generate_multi_referral_letter
from vertical_pt.engine.documents import generate_document, DOC_TITLES
from vertical_pt.engine.documents_ai import generate_document_ai
from vertical_pt.engine.soap_extractor import extract_clinical_context
from vertical_pt.engine.scribe import process_audio
from vertical_pt.engine.referral_tracker import (
    send_referral_email, mark_sent, mark_followup,
)
from vertical_pt.models import AuditPair, GeneratedDocument, PatientTimeline, RedFlagAlert


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
            "clinical_context":    s.clinical_context or {},
            "created_at":          s.created_at.strftime("%Y-%m-%d %H:%M"),
            "matched_indicators":  alert.matched_indicators if alert else [],
            "referral_letter":     alert.referral_letter if alert else "",
            # 리퍼럴 추적 Phase 1
            "alert_id":                alert.id if alert else None,
            "referral_sent_at":        alert.referral_sent_at.strftime("%Y-%m-%d") if alert and alert.referral_sent_at else None,
            "referral_sent_to_email":  alert.referral_sent_to_email if alert else "",
            "referral_email_delivered": alert.referral_email_delivered if alert else False,
            "referral_followup_checked": alert.referral_followup_checked if alert else False,
            "monitoring_flagged":      alert.monitoring_flagged if alert else False,
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
            "alert_id":                alert.id if alert else None,
            "referral_sent_at":        alert.referral_sent_at.strftime("%Y-%m-%d") if alert and alert.referral_sent_at else None,
            "referral_sent_to_email":  alert.referral_sent_to_email if alert else "",
            "referral_email_delivered": alert.referral_email_delivered if alert else False,
            "referral_followup_checked": alert.referral_followup_checked if alert else False,
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


# ── AJAX: SOAP 저장 (VPPA 분석 포함) ─────────────────────────────

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

    # SOAP 임상 컨텍스트 AI 추출 (temperature=0, 입력 분류만)
    try:
        clinical_ctx = extract_clinical_context(soap_text)
        if any(v for v in clinical_ctx.values() if v):
            timeline.clinical_context = clinical_ctx
            timeline.save(update_fields=["clinical_context"])
    except Exception:
        pass

    alert = None
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
        "referral_letter": "",
        "patient_context": patient_ctx,
    })


# ── AJAX: 문서 생성 (multi-session history 기반) ─────────────────

_SOAP_SECTION_STOP = re.compile(
    r'^(Plan|Assessment|Objective|Subjective|Diagnosis|Measurements|History|Chief|Observation)\s*:',
    re.IGNORECASE,
)

_FUNC_LIM_RE = re.compile(
    r'\b(antalgic\s+gait|unable\s+to|cannot|difficulty\s+(?:with|performing)|'
    r'limited\s+by|restricted\s+to|decreased\s+(?:ability|function)|'
    r'unable\s+to\s+perform|requires\s+assist|'
    r'weakness|extremity\s+weakness|근력\s*저하|상지\s*약화|하지\s*약화|'
    r'일상생활\s*(?:제한|불가|어려움))\b',
    re.IGNORECASE,
)
_LOM_RE = re.compile(r'^(.{3,40}?)\s+LOM\b', re.IGNORECASE)
# LOM 매칭 결과에서 "Measurements:", "STG:", "3. " 같은 접두어 제거
_LOM_CLEANUP = re.compile(
    r'^(?:(?:Measurements|Objective|Subjective|Plan|LTG|STG|History|Chief|Diagnosis)\s*:\s*)?'
    r'(?:\d+[\.\)]\s*)?',
    re.IGNORECASE,
)


def _soap_goals_fallback(sessions) -> dict:
    """
    clinical_context에 필드 누락 시 SOAP 텍스트 직접 파싱으로 보완 — API 재호출 없음.

    - LTG/STG: 역순 탐색 — 가장 최근 세션의 목표 우선 (목표 업데이트 반영)
    - onset_duration: 순방향 — 초진 기록 우선
    - functional_limitations: 전 세션 스캔 (LOM 패턴 + 기능 제한 키워드)
    """
    onset: str | None = None
    func_lims: list[str] = []

    # Pass 1 (forward): onset + functional_limitations — 전 세션 스캔
    for session in sessions:
        soap = (session.soap_text or "").strip()
        if not soap:
            continue
        current = None
        for line in soap.splitlines():
            stripped = line.strip()
            if not stripped:
                current = None
                continue
            if re.match(r'^(LTG|STG)\s*:', stripped, re.IGNORECASE):
                current = 'goals'
            elif re.match(r'^Onset\s*:', stripped, re.IGNORECASE) and onset is None:
                val = re.sub(r'^Onset\s*:\s*', '', stripped, flags=re.IGNORECASE).strip()
                if val and val.lower() not in ('not certain', 'unknown', 'n/a', ''):
                    onset = val
                current = None
            elif _SOAP_SECTION_STOP.match(stripped):
                current = None

            if current == 'goals':
                continue  # goals 라인은 Pass 2에서 처리

            lom_m = _LOM_RE.match(stripped)
            if lom_m:
                body = _LOM_CLEANUP.sub('', lom_m.group(1)).strip()
                if body and len(body) > 2:
                    lim = f"{body} — limited range of motion"
                    if lim not in func_lims:
                        func_lims.append(lim)
            elif _FUNC_LIM_RE.search(stripped) and stripped not in func_lims:
                func_lims.append(stripped)

    # Pass 2 (reverse): LTG/STG — 가장 최근 세션의 명시적 목표를 우선 사용
    ltg: list[str] = []
    stg: list[str] = []
    for session in reversed(sessions):
        soap = (session.soap_text or "").strip()
        if not soap:
            continue
        current = None
        for line in soap.splitlines():
            stripped = line.strip()
            if not stripped:
                current = None
                continue
            if re.match(r'^LTG\s*:', stripped, re.IGNORECASE):
                current = 'ltg'
                rest = re.sub(r'^LTG\s*:\s*', '', stripped, flags=re.IGNORECASE).strip()
                if rest and rest not in ltg:
                    ltg.append(rest)
            elif re.match(r'^STG\s*:', stripped, re.IGNORECASE):
                current = 'stg'
                rest = re.sub(r'^STG\s*:\s*', '', stripped, flags=re.IGNORECASE).strip()
                if rest and rest not in stg:
                    stg.append(rest)
            elif _SOAP_SECTION_STOP.match(stripped):
                current = None
            elif current == 'ltg' and stripped not in ltg:
                ltg.append(stripped)
            elif current == 'stg' and stripped not in stg:
                stg.append(stripped)
        if ltg or stg:
            break  # 가장 최근 세션의 goals 발견 시 중단

    return {
        "goals_ltg":              ltg,
        "goals_stg":              stg,
        "onset_duration":         onset,
        "functional_limitations": func_lims,
    }


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

    # 가장 최근 임상 컨텍스트 선택 — 내부 전용 키 제외 후 실제 임상 필드가 있는 것만
    _INTERNAL_KEYS = {"soap_section_overrides"}
    clinical_context = {}
    for s in reversed(sessions):
        ctx = s.clinical_context or {}
        clinical_fields = {k: v for k, v in ctx.items() if k not in _INTERNAL_KEYS}
        if any(v for v in clinical_fields.values() if v):
            clinical_context = clinical_fields
            break

    # 누락 필드 SOAP 텍스트 직접 파싱으로 보완 (API 재호출 없음)
    fallback = _soap_goals_fallback(sessions)
    for key in ("goals_ltg", "goals_stg", "onset_duration", "functional_limitations"):
        if not clinical_context.get(key) and fallback.get(key):
            clinical_context[key] = fallback[key]

    latest_timeline = sessions[-1]

    # ── 캐시 확인: 같은 latest_timeline + doc_type으로 이미 생성된 문서 재사용 ──
    # 새 세션이 추가되면 latest_timeline이 바뀌므로 자동 무효화됨
    cached = {
        doc.version: doc
        for doc in GeneratedDocument.objects.filter(
            therapist=request.user,
            timeline=latest_timeline,
            doc_type=doc_type,
        ).order_by("-created_at")
    }

    # ── Template 버전 ─────────────────────────────────────────────────
    tmpl_doc = cached.get(GeneratedDocument.VERSION_TEMPLATE)
    if not tmpl_doc:
        try:
            template_text = generate_document(
                doc_type=doc_type,
                sessions=sessions,
                patient_ctx=patient_ctx,
                therapist_name=therapist_name,
                patient_id=patient_id,
                clinic_name=clinic_name,
                clinical_context=clinical_context,
            )
        except Exception as e:
            return JsonResponse({"error": f"Document generation failed: {e}"}, status=500)
        tmpl_doc = GeneratedDocument.objects.create(
            timeline=latest_timeline,
            therapist=request.user,
            doc_type=doc_type,
            version=GeneratedDocument.VERSION_TEMPLATE,
            content=template_text,
        )

    # ── AI 버전: 캐시 없을 때만 Gemini 호출 ──────────────────────────
    ai_doc = cached.get(GeneratedDocument.VERSION_AI)
    if not ai_doc:
        try:
            few_shots = list(
                GeneratedDocument.objects
                .filter(therapist=request.user, doc_type=doc_type, chosen=True)
                .order_by("-chosen_at")
                .values_list("content", flat=True)[:3]
            )
            ai_text = generate_document_ai(
                doc_type=doc_type,
                sessions=sessions,
                therapist_name=therapist_name,
                patient_id=patient_id,
                clinic_name=clinic_name,
                clinical_context=clinical_context,
                few_shot_examples=few_shots or None,
            )
            ai_doc = GeneratedDocument.objects.create(
                timeline=latest_timeline,
                therapist=request.user,
                doc_type=doc_type,
                version=GeneratedDocument.VERSION_AI,
                content=ai_text,
            )
        except Exception as e:
            logger.warning("AI document generation failed for %s: %s", doc_type, e)

    return JsonResponse({
        "ok":           True,
        "doc_type":     doc_type,
        "title":        DOC_TITLES[doc_type],
        "generated_at": datetime.date.today().strftime("%B %d, %Y"),
        "session_count": len(sessions),
        "template": {"id": tmpl_doc.id, "content": tmpl_doc.content},
        "ai":        {"id": ai_doc.id, "content": ai_doc.content} if ai_doc else None,
    })


# ── AJAX: 오디오 → S/O 텍스트 변환 ──────────────────────────────

@login_required
@require_http_methods(["POST"])
def transcribe_audio(request):
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": "audio file required"}, status=400)

    max_mb = 25
    if audio_file.size > max_mb * 1024 * 1024:
        return JsonResponse({"error": f"파일 크기 {max_mb}MB 초과"}, status=400)

    try:
        result = process_audio(audio_file.read())
    except RuntimeError as e:
        return JsonResponse({"error": str(e)}, status=502)
    except Exception as e:
        return JsonResponse({"error": f"변환 실패: {e}"}, status=500)

    return JsonResponse({
        "ok":       True,
        "S":        result["S"],
        "O":        result["O"],
        "full_text": result["full_text"],
        "provider": result["provider"],
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
        pass  # letter generated on explicit user action (flywheel signal)

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
        "session_date":    datetime.date.today().strftime("%Y-%m-%d"),
    }
    return redirect("vertical_pt:pt_result")


@login_required
def result_view(request):
    ctx = request.session.pop("pt_result", None)
    if not ctx:
        return redirect("vertical_pt:pt_index")
    ctx["score_pct"] = round((ctx.get("score") or 0) * 100)
    return render(request, "vertical_pt/result.html", ctx)


# ── 리퍼럴 추적 Phase 1 ──────────────────────────────────────────

def _get_alert_for_user(alert_id: int, user):
    """alert가 해당 therapist 소유인지 확인 후 반환."""
    try:
        return RedFlagAlert.objects.select_related("timeline").get(
            id=alert_id, timeline__therapist=user
        )
    except RedFlagAlert.DoesNotExist:
        return None


@login_required
@require_http_methods(["POST"])
def referral_generate(request, alert_id):
    """웹앱에서 referral letter 생성 — template + AI 버전 비교, DB 캐싱."""
    alert = _get_alert_for_user(alert_id, request.user)
    if not alert:
        return JsonResponse({"error": "Not found"}, status=404)

    therapist_name = request.user.get_full_name() or request.user.username
    clinic_name = ""
    try:
        if request.user.pt_profile:
            clinic_name = request.user.pt_profile.clinic_name or ""
    except Exception:
        pass

    # ── 캐시 확인 ─────────────────────────────────────────────────────
    cached = {
        doc.version: doc
        for doc in GeneratedDocument.objects.filter(
            therapist=request.user,
            timeline=alert.timeline,
            doc_type="referral",
        ).order_by("-created_at")
    }

    # ── Template 버전 ─────────────────────────────────────────────────
    tmpl_doc = cached.get(GeneratedDocument.VERSION_TEMPLATE)
    if not tmpl_doc:
        if not alert.referral_letter:
            letter = generate_referral_letter(
                alert,
                patient_id=alert.timeline.patient_id,
                therapist_name=therapist_name,
                session_date=alert.timeline.session_date,
            )
            alert.referral_letter = letter
            alert.save(update_fields=["referral_letter"])
        tmpl_doc = GeneratedDocument.objects.create(
            timeline=alert.timeline,
            therapist=request.user,
            doc_type="referral",
            version=GeneratedDocument.VERSION_TEMPLATE,
            content=alert.referral_letter,
            generation_params={"alert_id": alert.id},
        )

    # ── AI 버전: 캐시 없을 때만 Gemini 호출 ──────────────────────────
    ai_doc = cached.get(GeneratedDocument.VERSION_AI)
    if not ai_doc:
        try:
            few_shots = list(
                GeneratedDocument.objects
                .filter(therapist=request.user, doc_type="referral", chosen=True)
                .order_by("-chosen_at")
                .values_list("content", flat=True)[:3]
            )
            ai_text = generate_referral_letter_ai(
                alert,
                patient_id=alert.timeline.patient_id,
                therapist_name=therapist_name,
                clinic_name=clinic_name,
                few_shot_examples=few_shots or None,
            )
            ai_doc = GeneratedDocument.objects.create(
                timeline=alert.timeline,
                therapist=request.user,
                doc_type="referral",
                version=GeneratedDocument.VERSION_AI,
                content=ai_text,
                generation_params={"alert_id": alert.id},
            )
        except Exception as e:
            logger.warning("AI referral generation failed for alert %s: %s", alert_id, e)

    return JsonResponse({
        "referral_letter": tmpl_doc.content,   # backward compat
        "template": {"id": tmpl_doc.id, "content": tmpl_doc.content},
        "ai":        {"id": ai_doc.id, "content": ai_doc.content} if ai_doc else None,
    })


@login_required
@require_http_methods(["POST"])
def referral_send(request, alert_id):
    """리퍼럴 레터 이메일 발송 + '보냈음' 상태 기록."""
    alert = _get_alert_for_user(alert_id, request.user)
    if not alert:
        return JsonResponse({"error": "Not found"}, status=404)

    try:
        data     = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    to_email   = (data.get("to_email") or "").strip()
    send_email = bool(to_email)

    if send_email:
        delivered = send_referral_email(
            alert, to_email=to_email,
            therapist_name=request.user.get_full_name() or request.user.username,
        )
    else:
        mark_sent(alert, to_email=to_email)
        delivered = None  # 이메일 없이 수동 체크

    return JsonResponse({
        "ok":        True,
        "email_sent": send_email,
        "delivered":  delivered,
        "sent_at":    alert.referral_sent_at.isoformat() if alert.referral_sent_at else None,
    })


@login_required
@require_http_methods(["POST"])
def referral_mark_followup(request, alert_id):
    """PT가 '환자 follow-up 완료' 체크."""
    alert = _get_alert_for_user(alert_id, request.user)
    if not alert:
        return JsonResponse({"error": "Not found"}, status=404)

    mark_followup(alert)
    return JsonResponse({
        "ok":          True,
        "followup_at": alert.referral_followup_at.isoformat(),
    })


@login_required
@require_http_methods(["DELETE"])
def admin_clear_sessions(request):
    """전체 세션 삭제 (현재 유저)."""
    deleted, _ = PatientTimeline.objects.filter(therapist=request.user).delete()
    return JsonResponse({"ok": True, "deleted": deleted})


@login_required
@require_http_methods(["POST"])
def admin_reseed_ajax(request):
    """전체 삭제 + 실습 케이스 16개 + Margaret 10개 재적재 + 재스코어링."""
    import time
    import json as _json
    from pathlib import Path
    from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter

    # 1. 전체 삭제
    PatientTimeline.objects.filter(therapist=request.user).delete()

    results = {"seeded": 0, "errors": []}

    # 2. 16개 실습 케이스
    cases_path = Path(__file__).resolve().parents[2] / "data" / "soap_samples" / "cases.json"
    if cases_path.exists():
        cases = _json.loads(cases_path.read_text(encoding="utf-8"))
        for case in cases:
            try:
                pt       = case.get("patient", {})
                soap     = _build_soap_text(case)
                age, sex = pt.get("age",""), pt.get("sex","")
                if age:
                    soap = f"Patient: {age}yo {sex}\n" + soap
                try:
                    session_date = datetime.date.fromisoformat(
                        pt.get("eval_date","").replace("/","-"))
                except Exception:
                    session_date = datetime.date(2022,12,1) + datetime.timedelta(days=case["id"])

                _create_session(request.user, f"PT-{case['id']:03d}",
                                pt.get("name","Unknown"), session_date, soap)
                results["seeded"] += 1
            except Exception as e:
                results["errors"].append(str(e))


    # 3. Margaret Wilson 10회
    from vertical_pt.management.commands.seed_multi_session_patient import SESSIONS, PATIENT_ID, PATIENT_NAME
    for s in SESSIONS:
        try:
            _create_session(request.user, PATIENT_ID, PATIENT_NAME,
                            s["date"], s["soap"].strip())
            results["seeded"] += 1
        except Exception as e:
            results["errors"].append(str(e))

    # 4. ComplianceCase 재생성 (Direct Access deadline이 있는 주 배정)
    from vertical_pt.models import ComplianceCase
    ComplianceCase.objects.filter(therapist=request.user).delete()

    today = datetime.date.today()
    _STATES   = ["NY", "NJ", "AL", "DE", "MO", "NY", "NJ", "AL", "NY", "DE",
                 "MO", "NJ", "AL", "NY", "NJ", "MO"]   # 16개 PT-xxx 용
    _INSURERS = ["bcbs", "aetna", "medicare", "cigna", "united", "bcbs",
                 "aetna", "medicare", "cigna", "bcbs", "united", "aetna",
                 "bcbs", "medicare", "cigna", "united"]
    compliance_count = 0
    for i in range(1, 17):
        pid        = f"PT-{i:03d}"
        state      = _STATES[i - 1]
        start_date = today - datetime.timedelta(days=(i * 4) + 2)
        notified   = (start_date + datetime.timedelta(days=5)) if i % 4 == 0 else None
        poc_sent   = (start_date + datetime.timedelta(days=7)) if i % 6 == 0 else None
        ComplianceCase.objects.update_or_create(
            therapist=request.user, patient_id=pid,
            defaults={
                "state":                 state,
                "treatment_start_date":  start_date,
                "insurer_type":          _INSURERS[i - 1],
                "physician_notified_at": notified,
                "plan_of_care_sent_at":  poc_sent,
            }
        )
        compliance_count += 1

    # Margaret Wilson — NY (10일 기한), 8일 경과 → urgent
    ComplianceCase.objects.update_or_create(
        therapist=request.user, patient_id=PATIENT_ID,
        defaults={
            "state":                "NY",
            "treatment_start_date": today - datetime.timedelta(days=8),
            "insurer_type":         "bcbs",
            "physician_notified_at": None,
            "plan_of_care_sent_at":  None,
        }
    )
    compliance_count += 1
    results["compliance_seeded"] = compliance_count

    return JsonResponse({"ok": True, **results})


def _build_soap_text(case: dict) -> str:
    """seed_soap_samples.py의 _flatten_soap 인라인."""
    s, o, a, p = (case.get(k, {}) for k in ("S","O","A","P"))
    lines = []
    for key, field in [("Chief complaint",s.get("chief_complaint","")),
                       ("Onset",         s.get("onset","")),
                       ("History",        s.get("history",""))]:
        if field and field != "Not certain":
            lines.append(f"{key}: {field}")
    if s.get("additional"):  lines.append(s["additional"])
    for key, field in [("Diagnosis",    o.get("diagnosis","")),
                       ("Objective",    o.get("objective_data","")),
                       ("Measurements", o.get("measurements",""))]:
        if field: lines.append(f"{key}: {field}")
    if isinstance(a, dict):
        if a.get("ltg"): lines.append(f"LTG: {a['ltg']}")
        if a.get("stg"): lines.append(f"STG: {a['stg']}")
    if p: lines.append(f"Plan: {p}")
    return "\n".join(lines)


def _create_session(user, patient_id, patient_name, session_date, soap_text):
    result = score_soap(soap_text)
    timeline = PatientTimeline.objects.create(
        therapist=user, patient_id=patient_id, patient_name=patient_name,
        session_date=session_date, soap_text=soap_text,
        extracted_symptoms=result.get("vpps",{}),
        critical_score=result["score"], alarm_level=result["alarm"],
        triggered_condition=result["condition"] or "",
    )

    # clinical_context AI 추출 — save_soap_ajax / seed_multi_session_patient 와 동일 경로
    try:
        clinical_ctx = extract_clinical_context(soap_text)
        if any(v for v in clinical_ctx.values() if v):
            timeline.clinical_context = clinical_ctx
            timeline.save(update_fields=["clinical_context"])
    except Exception:
        pass

    if result["alarm"] in ("RED","YELLOW"):
        active = result.get("conditions",[])
        name   = user.get_full_name() or user.username
        alert  = RedFlagAlert.objects.create(
            timeline=timeline, condition=result["condition"] or "",
            alarm_level=result["alarm"], matched_indicators=result["matched"],
            score=result["score"], trigger_label=result.get("trigger",""),
        )
        from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter
        letter = (generate_multi_referral_letter(active, patient_id=patient_id, therapist_name=name)
                  if len(active) > 1 else
                  generate_referral_letter(alert, patient_id=patient_id, therapist_name=name))
        alert.referral_letter = letter
        alert.save(update_fields=["referral_letter"])


@login_required
@require_http_methods(["POST"])
def backfill_rescore_ajax(request):
    """사이드바 임시 버튼 — 현재 유저의 세션을 최신 VPPA로 재스코어링."""
    from vertical_pt.engine import score_soap
    from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter

    qs = PatientTimeline.objects.filter(therapist=request.user)
    changed = 0
    for timeline in qs:
        result   = score_soap(timeline.soap_text)
        new_alarm = result["alarm"]
        new_score = result["score"]
        old_alarm = timeline.alarm_level

        if new_alarm != old_alarm or abs((timeline.critical_score or 0) - (new_score or 0)) > 0.01:
            timeline.alarm_level         = new_alarm
            timeline.critical_score      = new_score
            timeline.triggered_condition = result["condition"] or ""
            timeline.extracted_symptoms  = result.get("vpps", {})
            timeline.save(update_fields=[
                "alarm_level", "critical_score",
                "triggered_condition", "extracted_symptoms",
            ])
            timeline.alerts.all().delete()
            if new_alarm in ("RED", "YELLOW"):
                therapist_name    = request.user.get_full_name() or request.user.username
                active_conditions = result.get("conditions", [])
                alert = RedFlagAlert.objects.create(
                    timeline=timeline,
                    condition=result["condition"] or "",
                    alarm_level=new_alarm,
                    matched_indicators=result["matched"],
                    score=new_score,
                    trigger_label=result.get("trigger", ""),
                )
                if len(active_conditions) > 1:
                    letter = generate_multi_referral_letter(
                        active_conditions,
                        patient_id=timeline.patient_id,
                        therapist_name=therapist_name,
                    )
                else:
                    letter = generate_referral_letter(
                        alert,
                        patient_id=timeline.patient_id,
                        therapist_name=therapist_name,
                    )
                alert.referral_letter = letter
                alert.save(update_fields=["referral_letter"])
            changed += 1

    total = qs.count()
    return JsonResponse({"ok": True, "total": total, "changed": changed})


@login_required
@require_http_methods(["POST"])
def save_section_overrides(request, session_id):
    """세션별 SOAP 섹션 오버라이드 저장 → clinical_context.soap_section_overrides."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        timeline = PatientTimeline.objects.get(id=session_id, therapist=request.user)
    except PatientTimeline.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    overrides = data.get("overrides", {})

    ctx = timeline.clinical_context or {}
    ctx["soap_section_overrides"] = overrides
    timeline.clinical_context = ctx
    timeline.save(update_fields=["clinical_context"])

    # 섹션 교정이 있을 때만 AuditPair 기록
    # original_content = 원본 SOAP 텍스트, edited_content = 치료사 섹션 배정 JSON
    if overrides:
        import json as _json
        AuditPair.objects.create(
            type=AuditPair.TYPE_SOAP,
            timeline=timeline,
            therapist=request.user,
            doc_type="section_override",
            original_content=timeline.soap_text,
            edited_content=_json.dumps(overrides, ensure_ascii=False),
        )

    return JsonResponse({"ok": True})


# ── Phase 7: Audit Loop ──────────────────────────────────────────────


@login_required
@require_http_methods(["POST"])
def save_soap_edit(request, timeline_id):
    """치료사가 수정한 SOAP을 (원본, 수정본) 쌍으로 저장."""
    try:
        timeline = PatientTimeline.objects.get(id=timeline_id, therapist=request.user)
    except PatientTimeline.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    edited = data.get("edited_soap", "").strip()
    if not edited:
        return JsonResponse({"error": "edited_soap required"}, status=400)

    AuditPair.objects.create(
        type=AuditPair.TYPE_SOAP,
        timeline=timeline,
        therapist=request.user,
        original_content=timeline.soap_text,
        edited_content=edited,
    )
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def save_alarm_decision(request, alert_id):
    """Alarm 채택/기각/수정 결정을 저장."""
    alert = _get_alert_for_user(alert_id, request.user)
    if not alert:
        return JsonResponse({"error": "Not found"}, status=404)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    decision = data.get("decision", "").upper()
    if decision not in (AuditPair.DECISION_ADOPTED, AuditPair.DECISION_REJECTED, AuditPair.DECISION_MODIFIED):
        return JsonResponse({"error": "decision must be ADOPTED / REJECTED / MODIFIED"}, status=400)

    AuditPair.objects.create(
        type=AuditPair.TYPE_ALARM,
        timeline=alert.timeline,
        alert=alert,
        therapist=request.user,
        decision=decision,
        decision_reason=data.get("reason", "").strip(),
        original_content=alert.referral_letter,
        edited_content=data.get("edited_referral", "").strip(),
    )
    return JsonResponse({"ok": True, "decision": decision})


@login_required
@require_http_methods(["POST"])
def save_doc_edit(request, patient_id, doc_type):
    """치료사가 수정한 문서를 (원본, 수정본) 쌍으로 저장."""
    from vertical_pt.engine.documents import DOC_TITLES
    if doc_type not in DOC_TITLES:
        return JsonResponse({"error": f"Unknown doc_type: {doc_type}"}, status=400)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    original = data.get("original_doc", "").strip()
    edited   = data.get("edited_doc", "").strip()
    if not edited:
        return JsonResponse({"error": "edited_doc required"}, status=400)

    # 가장 최근 세션을 timeline 참조로 사용
    timeline = (
        PatientTimeline.objects
        .filter(therapist=request.user, patient_id=patient_id)
        .order_by("-session_date", "-created_at")
        .first()
    )
    if not timeline:
        return JsonResponse({"error": "No sessions found"}, status=404)

    from vertical_pt.engine.section_diff import compute_section_diffs
    diffs = compute_section_diffs(original, edited)

    AuditPair.objects.create(
        type=AuditPair.TYPE_DOCUMENT,
        timeline=timeline,
        therapist=request.user,
        doc_type=doc_type,
        original_content=original,
        edited_content=edited,
        section_diffs=diffs,
    )
    return JsonResponse({"ok": True})


@login_required
def export_audit_pairs(request):
    """수집된 paired data를 JSON으로 export."""
    pair_type = request.GET.get("type")
    qs = AuditPair.objects.filter(therapist=request.user).select_related("timeline", "alert")
    if pair_type:
        qs = qs.filter(type=pair_type)

    rows = []
    for p in qs.order_by("-created_at")[:500]:
        rows.append({
            "id":               p.id,
            "type":             p.type,
            "timeline_id":      p.timeline_id,
            "patient_id":       p.timeline.patient_id,
            "session_date":     str(p.timeline.session_date),
            "alert_id":         p.alert_id,
            "original_content": p.original_content,
            "edited_content":   p.edited_content,
            "decision":         p.decision,
            "decision_reason":  p.decision_reason,
            "doc_type":         p.doc_type,
            "section_diffs":    p.section_diffs,
            "created_at":       p.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({
        "count": len(rows),
        "pairs": rows,
    })


@login_required
def referral_print(request, alert_id):
    """리퍼럴 레터 인쇄 전용 HTML 페이지 (브라우저 print-to-PDF 유도)."""
    alert = _get_alert_for_user(alert_id, request.user)
    if not alert:
        return JsonResponse({"error": "Not found"}, status=404)

    letter = alert.referral_letter or "(No referral letter generated)"
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Referral Letter — {alert.timeline.patient_id}</title>
<style>
  body{{font-family:'Times New Roman',serif;font-size:12pt;
       max-width:700px;margin:48px auto;color:#111;white-space:pre-wrap;line-height:1.6}}
  @media print{{body{{margin:24px}}@page{{margin:2cm}}}}
</style>
<script>window.onload=()=>window.print();</script>
</head><body>{letter}</body></html>"""
    from django.http import HttpResponse
    return HttpResponse(html, content_type="text/html")


@login_required
@require_http_methods(["POST"])
def choose_doc_version(request, doc_id: int):
    """PT가 선택한 문서 버전을 chosen=True로 저장 — Flywheel few-shot 공급원."""
    from django.utils import timezone
    try:
        doc = GeneratedDocument.objects.get(id=doc_id, therapist=request.user)
    except GeneratedDocument.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    doc.chosen    = True
    doc.chosen_at = timezone.now()
    doc.save(update_fields=["chosen", "chosen_at"])

    # 리퍼럴 레터 선택 시 alert.referral_letter도 동기화 (이메일 발송 등 downstream 보호)
    if doc.doc_type == "referral":
        alert_id = doc.generation_params.get("alert_id")
        if alert_id:
            try:
                alert = RedFlagAlert.objects.get(id=alert_id, timeline__therapist=request.user)
                alert.referral_letter = doc.content
                alert.save(update_fields=["referral_letter"])
            except RedFlagAlert.DoesNotExist:
                pass

    return JsonResponse({"ok": True, "chosen_id": doc_id, "version": doc.version})


# ── Patient Contacts (수신자 관리) ────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def patient_contacts(request, patient_id: str):
    """GET: 환자 수신자 목록 / POST: 수신자 추가."""
    from vertical_pt.models import PatientContact

    if request.method == "GET":
        contacts = PatientContact.objects.filter(
            therapist=request.user, patient_id=patient_id
        ).values("id", "role", "name", "email", "organization")
        return JsonResponse({"contacts": list(contacts)})

    data = json.loads(request.body)
    role  = data.get("role", "")
    email = data.get("email", "").strip()
    name  = data.get("name", "").strip()
    if not email or not name or role not in dict(PatientContact.ROLE_CHOICES):
        return JsonResponse({"error": "role, name, email required"}, status=400)

    contact, _ = PatientContact.objects.update_or_create(
        therapist=request.user, patient_id=patient_id, role=role,
        defaults={"name": name, "email": email,
                  "organization": data.get("organization", "").strip()},
    )
    return JsonResponse({"ok": True, "id": contact.id})


@login_required
@require_http_methods(["DELETE"])
def patient_contact_delete(request, contact_id: int):
    from vertical_pt.models import PatientContact
    deleted, _ = PatientContact.objects.filter(
        id=contact_id, therapist=request.user
    ).delete()
    if not deleted:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({"ok": True})


# ── Document Email Send ───────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def send_document_email(request):
    """
    최종 문서를 선택된 수신자에게 이메일 발송.

    Body JSON:
        patient_id  : str
        doc_type    : str
        doc_title   : str
        content     : str  (최종 문서 내용)
        recipients  : [{id, name, email, role}]  — 선택된 수신자
    """
    from django.core.mail import EmailMessage, BadHeaderError
    from django.conf import settings

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    patient_id  = data.get("patient_id", "").strip()
    doc_title   = data.get("doc_title", "Document").strip()
    doc_type    = data.get("doc_type", "").strip()
    content     = data.get("content", "").strip()
    recipients  = data.get("recipients", [])

    if not content:
        return JsonResponse({"error": "content required"}, status=400)
    if not recipients:
        return JsonResponse({"error": "recipients required"}, status=400)

    therapist_name  = request.user.get_full_name() or request.user.username
    therapist_email = request.user.email or settings.DEFAULT_FROM_EMAIL

    subject = f"[Sage Pontus PT] {doc_title} — Patient {patient_id}"

    email_body = (
        f"Dear Recipient,\n\n"
        f"Please find below a clinical document from {therapist_name}, PT.\n\n"
        f"{'=' * 72}\n\n"
        f"{content}\n\n"
        f"{'=' * 72}\n\n"
        f"This document was generated by Sage Pontus PT documentation system.\n"
        f"Patient identity is protected — anonymous ID only.\n\n"
        f"Regards,\n{therapist_name}, PT\n"
    )

    sent_to = []
    failed  = []
    for r in recipients:
        to_email = r.get("email", "").strip()
        if not to_email:
            continue
        try:
            msg = EmailMessage(
                subject=subject,
                body=email_body,
                from_email=f"{therapist_name} via Sage Pontus <{settings.DEFAULT_FROM_EMAIL}>",
                to=[to_email],
                reply_to=[therapist_email] if therapist_email else [],
            )
            msg.send(fail_silently=False)
            sent_to.append({"email": to_email, "name": r.get("name", ""), "role": r.get("role", "")})
        except BadHeaderError:
            failed.append({"email": to_email, "error": "Invalid header"})
        except Exception as e:  # noqa: BLE001
            failed.append({"email": to_email, "error": str(e)})

    if not sent_to:
        return JsonResponse({"error": "All sends failed", "failed": failed}, status=500)

    # 발송 이력 기록
    timeline = (
        PatientTimeline.objects
        .filter(therapist=request.user, patient_id=patient_id)
        .order_by("-session_date", "-created_at")
        .first()
    )
    if timeline:
        AuditPair.objects.create(
            type=AuditPair.TYPE_DOCUMENT,
            timeline=timeline,
            therapist=request.user,
            doc_type=f"{doc_type}__email",
            original_content=content,
            edited_content=json.dumps({"sent_to": sent_to}),
        )

    return JsonResponse({"ok": True, "sent_to": sent_to, "failed": failed})


# ── Alarm Action: 임상가 의도 기록 + 리퍼럴 레터 생성 ──────────────────────────

@login_required
@require_http_methods(["POST"])
def alarm_action(request, alert_id):
    """
    임상가의 알람 액션 기록.

    action="referral"  → AuditPair(ADOPTED) + 리퍼럴 레터 생성 반환
    action="monitor"   → AuditPair(MONITORING) 저장 (YELLOW 전용)
    """
    from django.utils import timezone as _tz

    alert = _get_alert_for_user(alert_id, request.user)
    if not alert:
        return JsonResponse({"error": "Not found"}, status=404)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    action = data.get("action", "").strip()
    if action not in ("referral", "monitor"):
        return JsonResponse({"error": "action must be 'referral' or 'monitor'"}, status=400)

    if action == "monitor":
        if alert.alarm_level != "YELLOW":
            return JsonResponse({"error": "monitor action is only valid for YELLOW alerts"}, status=400)
        alert.monitoring_flagged    = True
        alert.monitoring_flagged_at = _tz.now()
        alert.save(update_fields=["monitoring_flagged", "monitoring_flagged_at"])
        AuditPair.objects.create(
            type=AuditPair.TYPE_ALARM,
            timeline=alert.timeline,
            alert=alert,
            therapist=request.user,
            decision=AuditPair.DECISION_MONITORING,
            decision_reason="Flagged for monitoring by clinician",
        )
        return JsonResponse({"ok": True, "action": "monitor"})

    # action == "referral"
    therapist_name = request.user.get_full_name() or request.user.username
    clinic_name = ""
    try:
        if request.user.pt_profile:
            clinic_name = request.user.pt_profile.clinic_name or ""
    except Exception:
        pass

    if not alert.referral_letter:
        active_conditions = []
        try:
            from vertical_pt.engine import score_soap
            result = score_soap(alert.timeline.soap_text)
            active_conditions = result.get("conditions", [])
        except Exception:
            pass

        if len(active_conditions) > 1:
            letter = generate_multi_referral_letter(
                active_conditions,
                patient_id=alert.timeline.patient_id,
                therapist_name=therapist_name,
                clinic_name=clinic_name,
                session_date=alert.timeline.session_date,
            )
        else:
            letter = generate_referral_letter(
                alert,
                patient_id=alert.timeline.patient_id,
                therapist_name=therapist_name,
                clinic_name=clinic_name,
                session_date=alert.timeline.session_date,
            )
        alert.referral_letter = letter
        alert.save(update_fields=["referral_letter"])

    AuditPair.objects.create(
        type=AuditPair.TYPE_ALARM,
        timeline=alert.timeline,
        alert=alert,
        therapist=request.user,
        decision=AuditPair.DECISION_ADOPTED,
        decision_reason="Clinician generated referral letter — alarm adopted",
        original_content=alert.referral_letter,
    )

    return JsonResponse({"ok": True, "action": "referral", "referral_letter": alert.referral_letter})


# ── Pilot Feedback ────────────────────────────────────────────────────────────

# ── Compliance Dashboard ──────────────────────────────────────────────────────

@login_required
def compliance_dashboard_json(request):
    """
    클리닉 전체 Compliance 현황 — 기한 임박/초과 항목 포함.

    Returns:
        urgent_count  : D-3 이내 마감 항목 수
        overdue_count : 기한 초과 항목 수
        sections      : direct_access / insurance / red_flags / documents / exposure
    """
    import datetime as _dt
    from vertical_pt.models import ComplianceCase
    from vertical_pt.engine.documents import DOC_TITLES

    today = _dt.date.today()
    URGENT_DAYS = 3

    cases = list(ComplianceCase.objects.filter(therapist=request.user))

    # ── Section 1: Direct Access ──────────────────────────────────────────────
    da_items = []
    for c in cases:
        da_dl = c.da_physician_deadline()
        if da_dl is None:
            continue
        days_left = (da_dl - today).days
        item = {
            "patient_id":            c.patient_id,
            "state":                 c.state,
            "treatment_start_date":  str(c.treatment_start_date) if c.treatment_start_date else None,
            "da_deadline_date":      str(da_dl),
            "da_days_left":          days_left,
            "physician_notified_at": str(c.physician_notified_at) if c.physician_notified_at else None,
            "plan_of_care_sent_at":  str(c.plan_of_care_sent_at) if c.plan_of_care_sent_at else None,
            "status": (
                "done"    if c.physician_notified_at else
                "overdue" if days_left < 0 else
                "urgent"  if days_left <= URGENT_DAYS else
                "ok"
            ),
        }
        da_items.append(item)

    da_pending        = [x for x in da_items if x["status"] in ("ok", "urgent", "overdue")]
    poc_pending_count = sum(1 for c in cases if c.treatment_start_date and not c.plan_of_care_sent_at)

    da_urgent   = [x for x in da_pending if x["status"] == "urgent"]
    da_overdue  = [x for x in da_pending if x["status"] == "overdue"]

    # ── Section 2: Insurance ─────────────────────────────────────────────────
    ins_items = []
    for c in cases:
        filing_dl = c.insurance_filing_deadline()
        appeal_dl = c.appeal_deadline()

        # Claim pending
        if filing_dl and not c.claim_submitted_at:
            days_left = (filing_dl - today).days
            ins_items.append({
                "patient_id":          c.patient_id,
                "insurer_type":        c.insurer_type,
                "insurer_name":        c.insurer_name,
                "kind":                "filing",
                "deadline_date":       str(filing_dl),
                "days_left":           days_left,
                "status": (
                    "overdue" if days_left < 0 else
                    "urgent"  if days_left <= URGENT_DAYS else
                    "ok"
                ),
            })

        # Appeal pending
        if c.claim_rejected_at and appeal_dl and not c.appeal_submitted_at:
            days_left = (appeal_dl - today).days
            ins_items.append({
                "patient_id":          c.patient_id,
                "insurer_type":        c.insurer_type,
                "insurer_name":        c.insurer_name,
                "kind":                "appeal",
                "deadline_date":       str(appeal_dl),
                "days_left":           days_left,
                "status": (
                    "overdue" if days_left < 0 else
                    "urgent"  if days_left <= URGENT_DAYS else
                    "ok"
                ),
            })

    ins_urgent  = [x for x in ins_items if x["status"] == "urgent"]
    ins_overdue = [x for x in ins_items if x["status"] == "overdue"]

    # ── Section 3: Red Flags ─────────────────────────────────────────────────
    open_alerts = list(
        RedFlagAlert.objects
        .filter(timeline__therapist=request.user, acknowledged=False)
        .select_related("timeline")
        .order_by("-created_at")
    )
    referral_not_sent  = [a for a in open_alerts if not a.referral_sent_at]
    followup_incomplete = [
        a for a in open_alerts
        if a.referral_sent_at and not a.referral_followup_checked
    ]

    # ── Section 4: Documents ─────────────────────────────────────────────────
    # All unique patients who have at least one session
    all_patient_ids = set(
        PatientTimeline.objects
        .filter(therapist=request.user)
        .values_list("patient_id", flat=True)
        .distinct()
    )

    from vertical_pt.models import GeneratedDocument as GD
    doc_stats = {}
    for dt, title in DOC_TITLES.items():
        generated_ids = set(
            GD.objects
            .filter(therapist=request.user, doc_type=dt)
            .values_list("timeline__patient_id", flat=True)
            .distinct()
        )
        chosen_ids = set(
            GD.objects
            .filter(therapist=request.user, doc_type=dt, chosen=True)
            .values_list("timeline__patient_id", flat=True)
            .distinct()
        )
        doc_stats[dt] = {
            "title":          title,
            "generated":      len(generated_ids),
            "chosen":         len(chosen_ids),
            "not_generated":  len(all_patient_ids - generated_ids),
        }

    # Patients with RED/YELLOW alarm but no referral doc generated
    alarmed_ids = set(
        PatientTimeline.objects
        .filter(therapist=request.user)
        .exclude(alarm_level="NONE")
        .values_list("patient_id", flat=True)
        .distinct()
    )
    referral_generated_ids = set(
        GD.objects
        .filter(therapist=request.user, doc_type="referral")
        .values_list("timeline__patient_id", flat=True)
        .distinct()
    )
    doc_incomplete = list(alarmed_ids - referral_generated_ids)

    # ── Section 5: Exposure Summary ──────────────────────────────────────────
    score = 0
    red_count    = sum(1 for a in open_alerts if a.alarm_level == "RED")
    yellow_count = sum(1 for a in open_alerts if a.alarm_level == "YELLOW")
    score += min(red_count * 20, 60)
    score += min(yellow_count * 10, 30)
    score += min(len(referral_not_sent) * 15, 30)
    score += min(len(da_overdue) * 20, 40)
    score += min(len(ins_overdue) * 15, 30)
    score = min(score, 100)

    # ── Aggregate counts ─────────────────────────────────────────────────────
    urgent_count  = len(da_urgent) + len(ins_urgent)
    overdue_count = len(da_overdue) + len(ins_overdue)

    return JsonResponse({
        "urgent_count":  urgent_count,
        "overdue_count": overdue_count,
        "sections": {
            "direct_access": {
                "total":                  len(cases),
                "physician_pending":      len([x for x in da_items if not x["physician_notified_at"]]),
                "plan_of_care_pending":   poc_pending_count,
                "urgent":                 da_urgent,
                "overdue":                da_overdue,
                "all":                    da_items,
            },
            "insurance": {
                "claim_pending":   len([x for x in ins_items if x["kind"] == "filing"]),
                "appeal_pending":  len([x for x in ins_items if x["kind"] == "appeal"]),
                "urgent":          ins_urgent,
                "overdue":         ins_overdue,
                "all":             ins_items,
            },
            "red_flags": {
                "open_alerts":          len(open_alerts),
                "referral_not_sent":    len(referral_not_sent),
                "followup_incomplete":  len(followup_incomplete),
                "alerts": [
                    {
                        "alert_id":          a.id,
                        "patient_id":        a.timeline.patient_id,
                        "alarm_level":       a.alarm_level,
                        "condition":         a.condition,
                        "session_date":      str(a.timeline.session_date),
                        "referral_sent_at":  str(a.referral_sent_at) if a.referral_sent_at else None,
                        "followup_checked":  a.referral_followup_checked,
                    }
                    for a in open_alerts[:50]
                ],
            },
            "documents": {
                "by_type":    doc_stats,
                "incomplete": doc_incomplete,
            },
            "exposure": {
                "liability_score": score,
                "breakdown": {
                    "open_red_alerts":       red_count,
                    "open_yellow_alerts":    yellow_count,
                    "referral_not_sent":     len(referral_not_sent),
                    "da_overdue":            len(da_overdue),
                    "insurance_overdue":     len(ins_overdue),
                },
            },
        },
    })


@login_required
@require_http_methods(["GET", "POST"])
def compliance_case_detail(request, patient_id: str):
    """GET: 환자 compliance 상세 / POST: 생성 또는 업데이트."""
    from vertical_pt.models import ComplianceCase

    if request.method == "GET":
        try:
            c = ComplianceCase.objects.get(therapist=request.user, patient_id=patient_id)
            return JsonResponse({"case": c.to_dict()})
        except ComplianceCase.DoesNotExist:
            return JsonResponse({"case": None})

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    _date_fields = (
        "treatment_start_date", "physician_notified_at",
        "plan_of_care_sent_at", "claim_submitted_at",
        "claim_rejected_at", "appeal_submitted_at",
    )
    _int_fields = ("da_deadline_days", "appeal_deadline_days")

    import datetime as _dt

    defaults = {}
    for f in _date_fields:
        if f in data:
            raw = data[f]
            if raw:
                try:
                    defaults[f] = _dt.date.fromisoformat(raw)
                except ValueError:
                    return JsonResponse({"error": f"Invalid date for {f}: {raw}"}, status=400)
            else:
                defaults[f] = None

    for f in _int_fields:
        if f in data:
            raw = data[f]
            defaults[f] = int(raw) if raw not in (None, "") else None

    for f in ("state", "insurer_type", "insurer_name", "notes"):
        if f in data:
            defaults[f] = (data[f] or "").strip()

    case, created = ComplianceCase.objects.update_or_create(
        therapist=request.user,
        patient_id=patient_id,
        defaults=defaults,
    )
    return JsonResponse({"ok": True, "created": created, "case": case.to_dict()})


@require_http_methods(["POST"])
def submit_feedback(request):
    """파일럿 챗봇 피드백 수집 — 비인증도 허용 (익명 피드백)."""
    from vertical_pt.models import PilotFeedback
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    msg = data.get("message", "").strip()
    if not msg:
        return JsonResponse({"error": "message required"}, status=400)

    PilotFeedback.objects.create(
        user       = request.user if request.user.is_authenticated else None,
        category   = data.get("category", PilotFeedback.CAT_IMPROVEMENT),
        message    = msg,
        page_url   = data.get("page_url", "")[:300],
        patient_id = data.get("patient_id", "")[:100],
        doc_type   = data.get("doc_type", "")[:50],
        action_log = data.get("action_log", [])[:5],
    )
    return JsonResponse({"ok": True})
