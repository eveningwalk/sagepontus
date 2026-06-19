"""
16개 SOAP 실습 케이스 → chrisnam 계정 세션으로 적재.

사용법:
    python manage.py seed_soap_samples [--clear]

옵션:
    --clear   기존 chrisnam 세션 삭제 후 재적재
"""

import datetime
import json
import time
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from vertical_pt.engine.scorer import score_soap
from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter
from vertical_pt.engine.soap_extractor import extract_clinical_context
from vertical_pt.models import PatientTimeline, RedFlagAlert

_CASES_PATH = Path(__file__).resolve().parents[4] / "sagepontus" / "data" / "soap_samples" / "cases.json"


def _flatten_soap(case: dict) -> str:
    """cases.json 구조체 → 단일 SOAP 텍스트."""
    s = case.get("S", {})
    o = case.get("O", {})
    a = case.get("A", {})
    p = case.get("P", "")

    lines = []

    # S
    cc = s.get("chief_complaint", "")
    if cc:
        lines.append(f"Chief complaint: {cc}")
    onset = s.get("onset", "")
    if onset and onset != "Not certain":
        lines.append(f"Onset: {onset}")
    hist = s.get("history", "")
    if hist:
        lines.append(f"History: {hist}")
    add = s.get("additional", "")
    if add:
        lines.append(add)

    # O
    dx = o.get("diagnosis", "")
    if dx:
        lines.append(f"Diagnosis: {dx}")
    obj = o.get("objective_data", "")
    if obj:
        lines.append(f"Objective: {obj}")
    meas = o.get("measurements", "")
    if meas:
        lines.append(f"Measurements: {meas}")

    # A
    ltg = a.get("ltg", "") if isinstance(a, dict) else ""
    stg = a.get("stg", "") if isinstance(a, dict) else ""
    if ltg:
        lines.append(f"LTG: {ltg}")
    if stg:
        lines.append(f"STG: {stg}")

    # P
    if p:
        lines.append(f"Plan: {p}")

    return "\n".join(lines)


class Command(BaseCommand):
    help = "16개 SOAP 실습 케이스를 chrisnam 계정 세션으로 적재합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="기존 chrisnam PT 세션 전체 삭제 후 재적재"
        )
        parser.add_argument(
            "--username", default="chrisnam",
            help="대상 계정 (기본: chrisnam)"
        )

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found."))
            return

        if options["clear"]:
            deleted, _ = PatientTimeline.objects.filter(therapist=user).delete()
            self.stdout.write(self.style.WARNING(f"기존 세션 {deleted}개 삭제됨."))

        with open(_CASES_PATH, encoding="utf-8") as f:
            cases = json.load(f)

        self.stdout.write(f"{len(cases)}개 케이스 적재 시작...")

        for case in cases:
            pt = case.get("patient", {})
            patient_name = pt.get("name", "Unknown")
            age          = pt.get("age", "")
            sex          = pt.get("sex", "")
            eval_date    = pt.get("eval_date", "")

            # patient_id: 이름 기반 (중복 허용 — 실습 데이터라 익명 처리)
            patient_id = f"PT-{case['id']:03d}"

            soap_text = _flatten_soap(case)
            if age:
                soap_text = f"Patient: {age}yo {sex}\n" + soap_text

            # 날짜 파싱
            try:
                session_date = datetime.datetime.strptime(eval_date, "%Y/%m/%d").date()
            except (ValueError, TypeError):
                session_date = datetime.date(2022, 12, 1) + datetime.timedelta(days=case["id"])

            result = score_soap(soap_text)

            timeline = PatientTimeline.objects.create(
                therapist=user,
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
                if len(active_conditions) > 1:
                    referral_letter = generate_multi_referral_letter(
                        active_conditions,
                        patient_id=patient_id,
                        therapist_name=username,
                        session_date=session_date,
                    )
                else:
                    referral_letter = generate_referral_letter(
                        alert,
                        patient_id=patient_id,
                        therapist_name=username,
                        session_date=session_date,
                    )
                alert.referral_letter = referral_letter
                alert.save(update_fields=["referral_letter"])

            # ── AI 임상 컨텍스트 추출 (temperature=0, 최대 3회 재시도) ──
            self.stdout.write(f"  [{case['id']:2d}] {patient_name:8s} — AI 추출 중...", ending="\r")
            ctx_status = "- ctx"
            for attempt in range(3):
                try:
                    if attempt > 0:
                        time.sleep(2 ** attempt)  # 2s, 4s
                    clinical_ctx = extract_clinical_context(soap_text)
                    has_data = any(v for v in clinical_ctx.values() if v)
                    if has_data:
                        timeline.clinical_context = clinical_ctx
                        timeline.save(update_fields=["clinical_context"])
                        ctx_status = "✓ ctx"
                        break
                except Exception as e:
                    ctx_status = f"✗ ({e})"
            time.sleep(0.5)  # rate limit 방지

            alarm_display = {
                "RED":    self.style.ERROR("RED"),
                "YELLOW": self.style.WARNING("YELLOW"),
                "NONE":   self.style.SUCCESS("NONE"),
            }.get(result["alarm"], result["alarm"])

            conds = ", ".join(c["condition"] for c in active_conditions) or "-"
            self.stdout.write(
                f"  [{case['id']:2d}] {patient_name:8s} {patient_id}  "
                f"alarm={alarm_display}  hits={result['vpps']['hit_count']}  "
                f"conditions=[{conds}]  {ctx_status}"
            )

        self.stdout.write(self.style.SUCCESS(f"\n완료: {len(cases)}개 세션 적재 + AI 컨텍스트 추출 → {username}"))
