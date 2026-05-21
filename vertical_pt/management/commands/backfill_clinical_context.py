"""
기존 PatientTimeline 중 clinical_context가 비어있는 세션에
extract_clinical_context()를 소급 적용.

사용법:
    python manage.py backfill_clinical_context
    python manage.py backfill_clinical_context --dry-run
    python manage.py backfill_clinical_context --username chrisnam
"""

import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from vertical_pt.engine.soap_extractor import extract_clinical_context
from vertical_pt.models import PatientTimeline


class Command(BaseCommand):
    help = "clinical_context 미적재 세션에 AI 추출 소급 적용"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", default="",
            help="특정 계정만 처리 (기본: 전체)"
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="실제 저장 없이 대상 세션 수만 출력"
        )

    def handle(self, *args, **options):
        qs = PatientTimeline.objects.all()
        if options["username"]:
            try:
                user = User.objects.get(username=options["username"])
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User '{options['username']}' not found."))
                return
            qs = qs.filter(therapist=user)

        # clinical_context가 비어있는 세션만
        targets = [t for t in qs if not t.clinical_context]
        total = len(targets)
        self.stdout.write(f"대상 세션: {total}개")

        if options["dry_run"] or total == 0:
            return

        ok = fail = 0
        for i, timeline in enumerate(targets, 1):
            label = f"[{i:3d}/{total}] {timeline.patient_id} / {timeline.session_date}"
            self.stdout.write(f"  {label} — 추출 중...", ending="\r")
            try:
                ctx = extract_clinical_context(timeline.soap_text)
                has_data = any(v for v in ctx.values() if v)
                if has_data:
                    timeline.clinical_context = ctx
                    timeline.save(update_fields=["clinical_context"])
                    self.stdout.write(f"  {label} ✓")
                    ok += 1
                else:
                    self.stdout.write(f"  {label} — 빈 응답 (저장 생략)")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  {label} ✗ {e}"))
                fail += 1

            time.sleep(0.4)  # rate limit 방지

        self.stdout.write(self.style.SUCCESS(f"\n완료: 성공 {ok} / 실패 {fail} / 전체 {total}"))
