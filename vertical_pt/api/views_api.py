"""
PT Red Flag REST API
Chrome Extension 및 웹 UI가 호출하는 엔드포인트.

POST /api/pt/analyze/   — SOAP 분석 + 알람 생성
GET  /api/pt/timeline/  — 환자별 세션 이력 조회
GET  /api/pt/alerts/    — 미확인 알람 목록
POST /api/pt/alerts/<id>/acknowledge/ — 알람 확인 처리
"""

import logging
from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vertical_pt.engine import score_soap, build_patient_context
from vertical_pt.engine.referral import generate_referral_letter
from vertical_pt.models import PatientTimeline, RedFlagAlert
from .serializers import (
    AnalyzeRequestSerializer,
    AnalyzeResponseSerializer,
    PatientTimelineSerializer,
    RedFlagAlertSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
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

    # ── PatientTimeline 저장 ──────────────────────────────────────────────
    timeline = PatientTimeline.objects.create(
        therapist=request.user,
        patient_id=patient_id,
        session_date=session_date,
        soap_text=soap_text,
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
