"""PT Red Flag 웹 UI 뷰."""

import datetime
import json
import re

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
from vertical_pt.engine.soap_extractor import extract_clinical_context
from vertical_pt.engine.scribe import process_audio
from vertical_pt.engine.referral_tracker import (
    send_referral_email, mark_sent, mark_followup,
)
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

    # SOAP 임상 컨텍스트 AI 추출 (temperature=0, 입력 분류만)
    try:
        clinical_ctx = extract_clinical_context(soap_text)
        if any(v for v in clinical_ctx.values() if v):
            timeline.clinical_context = clinical_ctx
            timeline.save(update_fields=["clinical_context"])
    except Exception:
        pass

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

    - LTG/STG: 명시적 레이블 이후 다음 섹션까지 라인 수집 (최초 세션 기준)
    - onset_duration: "Onset:" 레이블 값 (의미 없는 값 제외)
    - functional_limitations: LOM 패턴 + 기능 제한 키워드 (전 세션 스캔)
    """
    ltg, stg, onset = [], [], None
    func_lims: list[str] = []

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
            elif re.match(r'^Onset\s*:', stripped, re.IGNORECASE) and onset is None:
                val = re.sub(r'^Onset\s*:\s*', '', stripped, flags=re.IGNORECASE).strip()
                if val and val.lower() not in ('not certain', 'unknown', 'n/a', ''):
                    onset = val
                current = None
            elif _SOAP_SECTION_STOP.match(stripped):
                current = None
            elif current == 'ltg' and stripped not in ltg:
                ltg.append(stripped)
            elif current == 'stg' and stripped not in stg:
                stg.append(stripped)

            # functional_limitations: LOM 패턴 — goals 섹션 제외, 접두어 클린업
            lom_m = _LOM_RE.match(stripped)
            if lom_m and current not in ('ltg', 'stg'):
                body = _LOM_CLEANUP.sub('', lom_m.group(1)).strip()
                if body and len(body) > 2:
                    lim = f"{body} — limited range of motion"
                    if lim not in func_lims:
                        func_lims.append(lim)
            # functional_limitations: 기능 제한 키워드 포함 라인 — goals 섹션 제외
            elif current not in ('ltg', 'stg') and _FUNC_LIM_RE.search(stripped) and stripped not in func_lims:
                func_lims.append(stripped)

        if ltg or stg:
            break  # 첫 번째(가장 초기) 세션에서 goals 발견 시 중단

    return {
        "goals_ltg":            ltg,
        "goals_stg":            stg,
        "onset_duration":       onset,
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

    try:
        doc_text = generate_document(
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

    return JsonResponse({
        "ok":           True,
        "doc_type":     doc_type,
        "doc":          doc_text,
        "title":        DOC_TITLES[doc_type],
        "generated_at": datetime.date.today().strftime("%B %d, %Y"),
        "session_count": len(sessions),
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
    """사이드바 임시 버튼 — 현재 유저의 세션을 최신 VPPS로 재스코어링."""
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

    ctx = timeline.clinical_context or {}
    ctx["soap_section_overrides"] = data.get("overrides", {})
    timeline.clinical_context = ctx
    timeline.save(update_fields=["clinical_context"])
    return JsonResponse({"ok": True})


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
