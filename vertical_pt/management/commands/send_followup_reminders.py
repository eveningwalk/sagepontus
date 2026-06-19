"""
30일 경과 리퍼럴 follow-up 리마인더 이메일 발송.

사용법:
    python manage.py send_followup_reminders [--days 30] [--dry-run]

Cloud Scheduler / cron 예시 (매일 오전 9시):
    0 9 * * * python manage.py send_followup_reminders
"""

from django.core.management.base import BaseCommand

from vertical_pt.engine.referral_tracker import find_overdue_alerts, send_followup_reminder


class Command(BaseCommand):
    help = "30일 경과 리퍼럴 미확인 케이스에 PT 리마인더 이메일 발송"

    def add_arguments(self, parser):
        parser.add_argument("--days",    type=int, default=30, help="경과 일수 기준 (기본 30)")
        parser.add_argument("--dry-run", action="store_true",  help="실제 발송 없이 대상만 출력")

    def handle(self, *args, **options):
        days    = options["days"]
        dry_run = options["dry_run"]

        alerts = find_overdue_alerts(days=days)
        count  = alerts.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"리마인더 대상 없음 ({days}일 기준)"))
            return

        self.stdout.write(f"리마인더 대상: {count}건 ({days}일 경과, follow-up 미확인)")

        sent = skipped = 0
        for alert in alerts:
            therapist = alert.timeline.therapist
            label = f"[alert={alert.id}] {alert.timeline.patient_id} → {therapist.email or '이메일없음'}"

            if dry_run:
                self.stdout.write(f"  DRY-RUN {label}")
                continue

            if send_followup_reminder(alert):
                self.stdout.write(self.style.SUCCESS(f"  ✓ {label}"))
                sent += 1
            else:
                self.stdout.write(self.style.WARNING(f"  ✗ {label}"))
                skipped += 1

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\n완료: 발송 {sent}건 / 실패 {skipped}건"))
