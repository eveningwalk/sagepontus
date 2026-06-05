"""
PT Red Flag REST API
Chrome Extension 및 웹 UI가 호출하는 엔드포인트.

POST /api/pt/analyze/   — SOAP 분석 + 알람 생성
GET  /api/pt/timeline/  — 환자별 세션 이력 조회
GET  /api/pt/alerts/    — 미확인 알람 목록
POST /api/pt/alerts/<id>/acknowledge/ — 알람 확인 처리
"""

import logging
import os
import re
from datetime import date

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from vertical_pt.engine import score_soap, build_patient_context
from vertical_pt.engine.referral import generate_referral_letter
from vertical_pt.engine.soap_extractor import extract_clinical_context
from vertical_pt.models import PatientTimeline, RedFlagAlert
from .serializers import (
    AnalyzeRequestSerializer,
    AnalyzeResponseSerializer,
    PatientTimelineSerializer,
    RedFlagAlertSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def analyze(request):
    """
    SOAP 텍스트 분석 → Red Flag 탐지 → DB 저장 → 알람 반환.

    Request body:
        patient_id, soap_text, session_date?, use_ai?, generate_referral?
    """
    req = AnalyzeRequestSerializer(data=request.data)
    if not req.is_valid():
        return Response(req.errors, status=status.HTTP_400_BAD_REQUEST)

    d = req.validated_data
    soap_text    = d["soap_text"]
    patient_id   = d["patient_id"]
    session_date = d.get("session_date") or date.today()
    use_ai       = d.get("use_ai", False)
    gen_referral = d.get("generate_referral", False)

    # ── 이전 세션 컨텍스트 로드 ───────────────────────────────────────────
    patient_ctx = build_patient_context(patient_id, request.user.id)

    # ── VPPS + Scorer ─────────────────────────────────────────────────────
    result = score_soap(soap_text, use_ai=use_ai)

    # ── clinical_context 추출 (Gemini) ───────────────────────────────────
    clinical_ctx = {}
    try:
        clinical_ctx = extract_clinical_context(soap_text) or {}
        import sys
        print(f"[ANALYZE_DEBUG] clinical_ctx keys={list(clinical_ctx.keys())} primary_dx={clinical_ctx.get('primary_diagnosis','')}", flush=True, file=sys.stderr)
    except Exception as e:
        import sys
        print(f"[ANALYZE_DEBUG] extract_clinical_context FAILED: {e}", flush=True, file=sys.stderr)

    # ── PatientTimeline 저장 ──────────────────────────────────────────────
    timeline = PatientTimeline.objects.create(
        therapist=request.user,
        patient_id=patient_id,
        session_date=session_date,
        soap_text=soap_text,
        clinical_context=clinical_ctx,
        extracted_symptoms=result.get("vpps", {}),
        critical_score=result["score"],
        alarm_level=result["alarm"],
        triggered_condition=result["condition"] or "",
    )

    # ── 알람 저장 (RED / YELLOW만) ────────────────────────────────────────
    alert_id       = None
    referral_text  = ""

    if result["alarm"] in ("RED", "YELLOW"):
        alert = RedFlagAlert.objects.create(
            timeline=timeline,
            condition=result["condition"] or "",
            alarm_level=result["alarm"],
            matched_indicators=result["matched"],
            score=result["score"],
            trigger_label=result.get("trigger", ""),
        )
        alert_id = alert.id

        if gen_referral and result["alarm"] == "RED":
            therapist_name = request.user.get_full_name() or request.user.username
            referral_text  = generate_referral_letter(
                alert,
                patient_id=patient_id,
                therapist_name=therapist_name,
                session_date=session_date,
            )
            alert.referral_letter = referral_text
            alert.save(update_fields=["referral_letter"])

        logger.info(
            "RedFlagAlert created: alarm=%s condition=%s score=%.3f patient=%s",
            result["alarm"], result["condition"], result["score"], patient_id,
        )

    response_data = {
        "alarm":          result["alarm"],
        "condition":      result["condition"],
        "score":          result["score"],
        "matched":        result["matched"],
        "trigger":        result.get("trigger", ""),
        "alert_id":       alert_id,
        "referral_letter": referral_text,
        "patient_context": patient_ctx,
    }
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def patient_timeline(request):
    """환자 세션 이력 조회. ?patient_id=XXX&limit=20"""
    patient_id = request.query_params.get("patient_id")
    limit      = int(request.query_params.get("limit", 20))

    qs = PatientTimeline.objects.filter(therapist=request.user)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)

    serializer = PatientTimelineSerializer(qs.order_by("-session_date")[:limit], many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def alerts_list(request):
    """미확인 알람 목록. ?acknowledged=false (기본)"""
    show_all = request.query_params.get("all", "false").lower() == "true"
    qs = RedFlagAlert.objects.filter(timeline__therapist=request.user)
    if not show_all:
        qs = qs.filter(acknowledged=False)

    serializer = RedFlagAlertSerializer(qs.order_by("-created_at")[:50], many=True)
    return Response(serializer.data)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def generate_referral(request, alert_id: int):
    """
    기존 alert에 대한 리퍼럴 레터 생성/반환.
    세션 중복 생성 없이 alert_id만으로 처리.
    """
    try:
        alert = RedFlagAlert.objects.get(
            id=alert_id,
            timeline__therapist=request.user,
        )
    except RedFlagAlert.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    if not alert.referral_letter:
        therapist_name = request.user.get_full_name() or request.user.username
        letter = generate_referral_letter(
            alert,
            patient_id=alert.timeline.patient_id,
            therapist_name=therapist_name,
            session_date=alert.timeline.session_date,
        )
        alert.referral_letter = letter
        alert.save(update_fields=["referral_letter"])

    return Response({"referral_letter": alert.referral_letter})


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def acknowledge_alert(request, alert_id: int):
    """알람 확인 처리 (센터장 → 확인 완료)."""
    try:
        alert = RedFlagAlert.objects.get(
            id=alert_id,
            timeline__therapist=request.user,
        )
    except RedFlagAlert.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    alert.acknowledged    = True
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["acknowledged", "acknowledged_at"])
    return Response({"status": "acknowledged", "alert_id": alert_id})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def waitlist(request):
    """Landing page waitlist signup — Resend으로 이메일 발송."""
    email = (request.data.get("email") or "").strip().lower()
    source = request.data.get("source", "landing")

    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        return Response({"error": "Invalid email address."}, status=400)

    api_key     = os.environ.get("RESEND_API_KEY", "")
    audience_id = os.environ.get("RESEND_AUDIENCE_ID", "")

    if not api_key:
        logger.warning("RESEND_API_KEY not set — skipping email send")
        return Response({"ok": True})

    try:
        import resend
        resend.api_key = api_key

        if audience_id:
            resend.Contacts.create({"audience_id": audience_id, "email": email, "unsubscribed": False})

        resend.Emails.send({
            "from":    "SagePontus <waitlist@sagepontus.com>",
            "to":      [email],
            "subject": "You're on the SagePontus waitlist 🛡️",
            "html": f"""
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                        max-width:520px;margin:0 auto;padding:40px 24px;color:#0F172A;">
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:32px;">
                <div style="width:36px;height:36px;border-radius:8px;background:#0EA5E9;
                            display:flex;align-items:center;justify-content:center;">
                  <span style="color:#fff;font-size:18px;">🛡️</span>
                </div>
                <span style="font-size:18px;font-weight:700;">SagePontus</span>
              </div>
              <h1 style="font-size:24px;font-weight:800;margin:0 0 12px;">You're on the list.</h1>
              <p style="font-size:16px;color:#475569;line-height:1.6;margin:0 0 24px;">
                We'll reach out as soon as beta access opens.
                Early members get <strong>6 months free</strong>.
              </p>
              <p style="font-size:13px;color:#94A3B8;margin:0;">
                © 2026 SagePontus · Made for clinicians, by clinicians.
              </p>
            </div>""",
        })
    except Exception as e:
        logger.error("Waitlist email failed for %s: %s", email, e)
        return Response({"error": "Failed to join waitlist."}, status=500)

    return Response({"ok": True})
