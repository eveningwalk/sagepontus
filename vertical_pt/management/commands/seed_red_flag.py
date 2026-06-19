"""
python manage.py seed_red_flag

data/red_flag_protocols/*.json의 indicators를 SymptomWeight 테이블에 적재.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from vertical_pt.models import SymptomWeight

_PROTOCOLS_DIR = Path(__file__).resolve().parents[3] / "data" / "red_flag_protocols"


class Command(BaseCommand):
    help = "Red Flag 프로토콜 JSON → SymptomWeight DB 적재"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="기존 데이터 삭제 후 재적재")

    def handle(self, *args, **options):
        if options["clear"]:
            count = SymptomWeight.objects.all().delete()[0]
            self.stdout.write(f"기존 {count}건 삭제")

        index_path = _PROTOCOLS_DIR / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))["protocols"]

        total = 0
        for proto_meta in index:
            path = _PROTOCOLS_DIR / proto_meta["file"]
            if not path.exists():
                self.stderr.write(f"파일 없음: {path}")
                continue

            protocol = json.loads(path.read_text(encoding="utf-8"))
            protocol_id = protocol["protocol_id"]

            for ind in protocol.get("indicators", []):
                obj, created = SymptomWeight.objects.update_or_create(
                    protocol_id=protocol_id,
                    symptom_id=ind["id"],
                    defaults={
                        "label":                ind["label"],
                        "weight":               ind["weight"],
                        "alarm_level":          ind.get("alarm_level", "YELLOW"),
                        "condition_ref":        protocol_id.replace("rfp_", ""),
                        "is_standalone_trigger": ind.get("standalone_trigger", False),
                        "cluster":              ind.get("cluster", ""),
                    },
                )
                total += 1
                mark = "✓" if created else "↺"
                self.stdout.write(f"  {mark} {protocol_id} / {ind['id']}")

        self.stdout.write(self.style.SUCCESS(f"\n완료: {total}건 적재"))
