"""
기존 PatientTimeline 세션을 최신 VPPS로 재스코어링.

사용법:
    python manage.py backfill_rescore
    python manage.py backfill_rescore --dry-run
    python manage.py backfill_rescore --username chrisnam
    python manage.py backfill_rescore --patient-id PT-MARGARET-001
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from vertical_pt.engine import score_soap, build_patient_context
from vertical_pt.engine.referral import generate_referral_letter, generate_multi_referral_letter
from vertical_pt.models import PatientTimeline, RedFlagAlert


class Command(BaseCommand):
    help = "기존 세션 VPPS 재스코어링 + RedFlagAlert 재생성"

    def add_arguments(self, parser):
        parser.add_argument("--username",   default="", help="특정 계정만 처리")
        parser.add_argument("--patient-id", default="", help="특정 환자만 처리")
        parser.add_argument("--dry-run", action="store_true", help="변경 없이 결과만 출력")

    def handle(self, *args, **options):
        qs = PatientTimeline.objects.all().order_by("id")

        if options["username"]:
            try:
                user = User.objects.get(username=options["username"])
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User '{options['username']}' not found."))
                return
            qs = qs.filter(therapist=user)

        if options["patient_id"]:
            qs = qs.filter(patient_id=options["patient_id"])

        total   = qs.count()
        changed = 0
        self.stdout.write(f"대상 세션: {total}개{'  [dry-run]' if options['dry_run'] else ''}\n")

        for timeline in qs:
            old_alarm = timeline.alarm_level
            old_score = timeline.critical_score

            result = score_soap(timeline.soap_text)
            new_alarm = result["alarm"]
            new_score = result["score"]
            new_cond  = result["condition"] or ""

            diff = (old_alarm != new_alarm) or (abs((old_score or 0) - (new_score or 0)) > 0.01)

            label = f"[{timeline.id:4d}] {timeline.patient_id} / {timeline.session_date}"
            change_str = (
                f"{self._alarm(old_alarm)} → {self._alarm(new_alarm)}"
                if diff else f"{self._alarm(old_alarm)} (unchanged)"
            )
            self.stdout.write(f"  {label}  {change_str}")

            if diff and not options["dry_run"]:
                timeline.alarm_level         = new_alarm
                timeline.critical_score      = new_score
                timeline.triggered_condition = new_cond
                timeline.extracted_symptoms  = result.get("vpps", {})
                timeline.save(update_fields=[
                    "alarm_level", "critical_score",
                    "triggered_condition", "extracted_symptoms",
                ])

                # 기존 Alert 삭제 후 재생성
                timeline.alerts.all().delete()

                if new_alarm in ("RED", "YELLOW"):
                    therapist_name    = timeline.therapist.get_full_name() or timeline.therapist.username
                    active_conditions = result.get("conditions", [])

                    alert = RedFlagAlert.objects.create(
                        timeline          = timeline,
                        condition         = new_cond,
                        alarm_level       = new_alarm,
                        matched_indicators= result["matched"],
                        score             = new_score,
                        trigger_label     = result.get("trigger", ""),
                    )

                    if len(active_conditions) > 1:
                        letter = generate_multi_referral_letter(
                            active_conditions,
                            patient_id    = timeline.patient_id,
                            therapist_name= therapist_name,
                        )
                    else:
                        letter = generate_referral_letter(
                            alert,
                            patient_id    = timeline.patient_id,
                            therapist_name= therapist_name,
                        )
                    alert.referral_letter = letter
                    alert.save(update_fields=["referral_letter"])

                changed += 1

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"\n[dry-run] 변경 예정: {sum(1 for _ in qs if True)}개 확인 완료 (실제 저장 없음)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n완료: {total}개 중 {changed}개 변경됨"))

    def _alarm(self, level):
        return {
            "RED":    self.style.ERROR("RED   "),
            "YELLOW": self.style.WARNING("YELLOW"),
            "NONE":   self.style.SUCCESS("NONE  "),
        }.get(level, level)
