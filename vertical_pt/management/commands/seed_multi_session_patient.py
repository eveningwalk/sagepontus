"""
10회 치료 이력을 가진 테스트 환자 페르소나 적재.

페르소나: Margaret Wilson, 58yo F
진단: L4-L5 disc herniation + right leg radiculopathy
경과: 초기 평가 → 개선 → 고원기 → Red Flag 출현(session 8) → 추적 관찰

사용법:
    python manage.py seed_multi_session_patient
    python manage.py seed_multi_session_patient --clear
    python manage.py seed_multi_session_patient --username chrisnam
"""

import datetime
import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from vertical_pt.engine.scorer import score_soap
from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter
from vertical_pt.engine.soap_extractor import extract_clinical_context
from vertical_pt.models import PatientTimeline, RedFlagAlert

PATIENT_ID   = "PT-MARGARET-001"
PATIENT_NAME = "Margaret Wilson"

SESSIONS = [
    # ── Session 1: Initial evaluation ─────────────────────────────────
    {
        "date": datetime.date(2026, 2, 18),
        "soap": """\
Patient: 58yo Female
Chief complaint: Low back pain radiating to right leg for 6 weeks. Started after lifting heavy boxes.
Onset: 6 weeks ago, gradual onset after activity
History: No prior PT. Desk job (accountant). No recent trauma. HTN, controlled on lisinopril.

Diagnosis: L4-L5 disc herniation with right L5 radiculopathy (MRI confirmed 2026-02-10)
Objective: Antalgic gait, leans left. Forward flexion 30 degrees limited by pain and radiation.
Measurements: VAS 7/10 at rest, 9/10 with activity. SLR Rt: positive at 35 degrees. Dermatomal numbness R lateral shin.
MMT: Rt hip flexion 4/5, Rt knee extension 4/5, Rt ankle dorsiflexion 3+/5

LTG: Independent functional mobility, return to work without pain limitation in 8 weeks
STG: Reduce VAS to 4/10, improve SLR to 60 degrees in 3 weeks
Plan: Lumbar traction 10 min, TENS 15 min, McKenzie extension protocol, core stabilization initiation. HEP given.
""",
    },
    # ── Session 2 ──────────────────────────────────────────────────────
    {
        "date": datetime.date(2026, 2, 25),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Continued low back pain with right leg radiation. Slightly better than initial visit.
History: Reports HEP compliance 5/7 days. Sleeping on side with pillow between knees helps.

Diagnosis: L4-L5 disc herniation, R L5 radiculopathy
Objective: Antalgic gait slightly improved. Flexion 40 degrees.
Measurements: VAS 6/10 at rest, 8/10 with activity. SLR Rt: positive at 42 degrees.
MMT: Rt ankle dorsiflexion 4-/5 (improved from 3+)

Plan: Continue lumbar traction, progress McKenzie, add neural mobilization. Reviewed HEP.
""",
    },
    # ── Session 3 ──────────────────────────────────────────────────────
    {
        "date": datetime.date(2026, 3, 4),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Back pain improving. Right leg numbness still present but less intense.
History: Able to sit for 30 min without severe pain (was 10 min at eval).

Diagnosis: L4-L5 disc herniation, improving radiculopathy
Objective: Gait normalized. Flexion 50 degrees. Extension full range.
Measurements: VAS 5/10 rest, 6/10 with activity. SLR Rt: positive at 52 degrees.
MMT: Rt ankle dorsiflexion 4/5. Hip flexion 5/5.

Plan: Progress to dynamic stabilization, introduce light resistance band exercises, reduce traction frequency.
""",
    },
    # ── Session 4 ──────────────────────────────────────────────────────
    {
        "date": datetime.date(2026, 3, 11),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Good week overall. Returned to driving (short distances). Occasional right leg ache.
History: Slipped on wet floor 3 days ago — no fall, caught herself on counter. Increased pain briefly, settled.

Diagnosis: L4-L5 disc herniation
Objective: Slight increased guarding after slip incident. Flexion 45 degrees (mild regression). No new neuro deficits.
Measurements: VAS 5/10 rest, 7/10 with activity. SLR Rt: 50 degrees.

Plan: Reassess after slip incident. Continued stabilization program, added balance training. Ice for 48h post-slip.
""",
    },
    # ── Session 5 ──────────────────────────────────────────────────────
    {
        "date": datetime.date(2026, 3, 18),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Back to prior trajectory after slip setback. Right leg radiation minimal.
History: HEP compliance excellent. Returned to desk work half-days.

Diagnosis: L4-L5 disc herniation, resolving radiculopathy
Objective: Flexion 55 degrees. Extension full. No antalgic lean.
Measurements: VAS 4/10 rest, 5/10 activity. SLR Rt: negative at 60 degrees (threshold met).
MMT: All lower extremity 5/5 bilaterally.

Plan: Progress to full work return program, ergonomic counseling session. Traction discontinued.
""",
    },
    # ── Session 6 ──────────────────────────────────────────────────────
    {
        "date": datetime.date(2026, 3, 25),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Returned to full work week. Fatigue by end of day but manageable. Reports some new onset upper back tightness.
History: No new injury. Reports increased stress at work (tax season). Denies new neurological symptoms.

Diagnosis: L4-L5 disc herniation, resolving. New: Upper thoracic muscle tension
Objective: Thoracic posture: forward head, rounded shoulders. Lumbar ROM near normal. Thoracic extension restricted.
Measurements: VAS lumbar 3/10, thoracic 4/10.

Plan: Added thoracic mobilization, postural correction exercises. Continued lumbar HEP.
""",
    },
    # ── Session 7 ──────────────────────────────────────────────────────
    {
        "date": datetime.date(2026, 4, 1),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Lumbar pain well controlled. Thoracic tightness improved. Mentions fatigue has been significant past 2 weeks — attributes to work stress.
History: Reports unintentional weight loss — approximately 8 lbs over 6 weeks. Attributes to skipping meals due to stress. No appetite change otherwise. Denies fever.

Diagnosis: L4-L5 disc herniation — near resolved. Thoracic postural syndrome.
Objective: Lumbar ROM 70 degrees flexion. Thoracic improved.
Measurements: VAS lumbar 2/10. VAS thoracic 3/10.

Plan: Continue maintenance program. Flagged weight loss for physician awareness — advised to mention at next PCP visit.
""",
    },
    # ── Session 8: Red Flag escalation ────────────────────────────────
    {
        "date": datetime.date(2026, 4, 8),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: New onset mid-thoracic pain, constant aching, 6/10. Night pain waking her from sleep past 5 nights. Prior lumbar pain was positional — this is NOT positional.
History: Unexplained weight loss 10 lbs over 7 weeks now confirmed. No appetite. Fatigue worsening. History of breast cancer 8 years ago, treated with lumpectomy + radiation, considered cured. No recent oncology follow-up.

Diagnosis: Prior L4-L5 disc herniation — resolved. New: Non-mechanical thoracic pain — etiology unclear.
Objective: Tenderness on palpation T6-T8 spinous processes. No radiculopathy. Neuro exam intact.
Measurements: VAS 6/10, worse at night. No position relieves pain.

Precaution: Non-mechanical pain pattern + night pain + unexplained weight loss + prior cancer history — Red Flag indicators present. PT treatment on hold. Immediate physician referral strongly recommended.
Plan: Suspended PT. Physician referral letter generated. Patient verbally informed of clinical concern. Family member present and informed.
""",
    },
    # ── Session 9: Post-referral follow-up ────────────────────────────
    {
        "date": datetime.date(2026, 4, 22),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Follow-up after physician evaluation. Oncology workup initiated (bone scan scheduled next week). Physician confirmed PT may continue gentle mobilization pending imaging results.
History: Physician visit confirmed: elevated inflammatory markers, bone scan ordered. Patient understandably anxious. Mild thoracic pain continues 5/10.

Diagnosis: Pending oncology workup. Prior L4-L5 disc herniation resolved.
Objective: Gentle assessment only. No provocation testing. Thoracic tenderness T6-T8 unchanged.
Measurements: VAS 5/10 thoracic.

Plan: Gentle thoracic range of motion only. No spinal loading or manipulation. Emotional support provided. HEP modified to walking program only. Follow oncology workup.
""",
    },
    # ── Session 10: Final documentation ───────────────────────────────
    {
        "date": datetime.date(2026, 5, 6),
        "soap": """\
Patient: 58yo Female — Margaret Wilson
Chief complaint: Bone scan results: multiple lesions T5, T7, T9 consistent with metastatic disease. Oncology confirmed recurrent breast cancer with spinal metastases. Patient starting radiation therapy next week. Requesting PT discharge summary for oncology team.
History: Patient emotional but composed. Husband present. Reports understanding of diagnosis. Grateful for early PT referral — oncologist confirmed early detection improves treatment options.

Diagnosis: Spinal metastases (recurrent breast cancer) — oncology managing. Prior L4-L5 disc herniation resolved.
Objective: Ambulation independent. Pain 5/10 managed with medication.
Measurements: VAS 5/10 thoracic, controlled with prescribed analgesics.

LTG: Safe functional mobility during cancer treatment
STG: Maintain independence in ADLs through radiation therapy
Plan: Discharge from current PT episode. Oncology PT referral placed for spine precaution training. Comprehensive discharge summary provided to patient and oncology team. Return to PT post-radiation for functional rehabilitation.
""",
    },
]


class Command(BaseCommand):
    help = "10회 치료 이력 테스트 환자(Margaret Wilson) 적재"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="기존 Margaret 세션 삭제 후 재적재")
        parser.add_argument("--username", default="chrisnam", help="대상 계정 (기본: chrisnam)")

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found."))
            return

        if options["clear"]:
            deleted, _ = PatientTimeline.objects.filter(
                therapist=user, patient_id=PATIENT_ID
            ).delete()
            self.stdout.write(self.style.WARNING(f"기존 세션 {deleted}개 삭제됨."))

        self.stdout.write(f"페르소나: {PATIENT_NAME} ({PATIENT_ID}) — {len(SESSIONS)}회 세션 적재 시작\n")

        for i, session in enumerate(SESSIONS, 1):
            soap_text    = session["soap"].strip()
            session_date = session["date"]

            result = score_soap(soap_text)

            timeline = PatientTimeline.objects.create(
                therapist=user,
                patient_id=PATIENT_ID,
                patient_name=PATIENT_NAME,
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
                        patient_id=PATIENT_ID,
                        therapist_name=username,
                    )
                else:
                    referral_letter = generate_referral_letter(
                        alert,
                        patient_id=PATIENT_ID,
                        therapist_name=username,
                    )
                alert.referral_letter = referral_letter
                alert.save(update_fields=["referral_letter"])

            # AI 임상 컨텍스트 추출
            ctx_status = "- ctx"
            for attempt in range(3):
                try:
                    if attempt > 0:
                        time.sleep(2 ** attempt)
                    ctx = extract_clinical_context(soap_text)
                    if any(v for v in ctx.values() if v):
                        timeline.clinical_context = ctx
                        timeline.save(update_fields=["clinical_context"])
                        ctx_status = "✓ ctx"
                        break
                except Exception as e:
                    ctx_status = f"✗ ({e})"
            time.sleep(0.5)

            alarm_display = {
                "RED":    self.style.ERROR("RED   "),
                "YELLOW": self.style.WARNING("YELLOW"),
                "NONE":   self.style.SUCCESS("NONE  "),
            }.get(result["alarm"], result["alarm"])

            self.stdout.write(
                f"  Session {i:2d}  {session_date}  alarm={alarm_display}  {ctx_status}"
            )

        self.stdout.write(self.style.SUCCESS(f"\n완료: {PATIENT_NAME} {len(SESSIONS)}회 세션 적재 → {username}"))
